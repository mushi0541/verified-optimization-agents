"""Solver-runner tool: runs the model code written by the LLM in a separate Python process.

The child process gets a minimal environment, so API keys in our environment are not visible to it.
This is isolation, not a security sandbox: only run it on a machine you control.
"""

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .contracts import SolveResult

# Appended to every script. The prompt asks the LLM to name its PuLP problem `model`.
_RESULT_FOOTER = """

try:
    import pulp as _pulp
    import re as _re
    print("STATUS:", _pulp.LpStatus[model.status])
    print("OBJECTIVE:", _pulp.value(model.objective))
    _ids = set()
    for _name in model.constraints:
        _ids.update(_re.findall(r"(?:^|_)(R\\d+)(?=_|$)", _name))
    print("REQUIREMENTS:", " ".join(sorted(_ids, key=lambda _id: int(_id[1:]))))
    if model.status == _pulp.LpStatusOptimal:
        _vars = []
        for _v in model.variables():
            _val = _pulp.value(_v)
            if _val is not None and abs(_val) > 1e-9:
                _vars.append((_v.name, float(_val)))
        _vars.sort(key=lambda _item: _item[0])
        for _name, _val in _vars[:100]:
            print("VAR:", _name, repr(_val))
        if len(_vars) > 100:
            print("VARS_OMITTED:", len(_vars) - 100)
except NameError:
    pass
"""

_STATUS_NAMES = {
    "Optimal": "optimal",
    "Infeasible": "infeasible",
    "Unbounded": "unbounded",
    "Not Solved": "not_solved",
    "Undefined": "not_solved",
}

_KEPT_ENV_VARS = ("SYSTEMROOT", "PATH", "TEMP", "TMP", "HOME", "USERPROFILE")


def extract_code(llm_text: str) -> str | None:
    """Return the longest fenced code block, which is the full script in practice."""
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", llm_text, re.DOTALL)
    return max(blocks, key=len).strip() if blocks else None


def run_model_code(code: str | None, timeout_s: int = 180) -> SolveResult:
    if not code:
        return SolveResult("no_code", None, error="The reply did not contain a Python code block.")

    start = time.perf_counter()
    with tempfile.TemporaryDirectory() as work_dir:
        script = Path(work_dir) / "model.py"
        script.write_text(code + _RESULT_FOOTER, encoding="utf-8")
        try:
            # UTF-8 mode, so code that prints symbols such as "≤" also runs on Windows.
            process = subprocess.run(
                [sys.executable, "-I", "-X", "utf8", str(script)],
                cwd=work_dir,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
                env={name: os.environ[name] for name in _KEPT_ENV_VARS if name in os.environ},
            )
        except subprocess.TimeoutExpired:
            return SolveResult("timeout", None, error=f"No result after {timeout_s} s.", runtime_s=timeout_s)

    runtime = time.perf_counter() - start
    stdout = _redact_paths(process.stdout, work_dir)
    if process.returncode != 0:
        return SolveResult("error", None, _tail(stdout), _tail(_redact_paths(process.stderr, work_dir)), runtime)

    status_text = _last_match(r"^STATUS:\s*(.+?)\s*$", stdout)
    status = _STATUS_NAMES.get(status_text, "not_solved") if status_text else "error"
    error = "" if status_text else "The script ran but did not define a PuLP problem named `model`."
    objective = _to_float(_last_match(r"^OBJECTIVE:\s*(\S+)\s*$", stdout)) if status == "optimal" else None
    variables = _parse_variables(stdout) if status == "optimal" else {}
    requirement_ids = (_last_match(r"^REQUIREMENTS:(.*)$", stdout) or "").split()
    kept = re.sub(r"^(?:VAR: |REQUIREMENTS:).*\n?", "", stdout, flags=re.MULTILINE)
    return SolveResult(status, objective, _tail(kept), error, runtime, variables, requirement_ids)


def _parse_variables(text: str) -> dict[str, float]:
    variables = {}
    for match in re.finditer(r"^VAR:\s*(\S+)\s+(\S+)$", text, re.MULTILINE):
        try:
            variables[match.group(1)] = float(match.group(2))
        except ValueError:
            pass
    return variables


def _last_match(pattern: str, text: str) -> str | None:
    matches = re.findall(pattern, text, re.MULTILINE)
    return matches[-1] if matches else None


def _to_float(text: str | None) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _redact_paths(text: str, work_dir: str) -> str:
    """Replace local folders in the solver's output with placeholders, so records and repair prompts hold no user
    name or folder: the run's temporary folder, the Python environment, the Python install, then the home folder."""
    folders = [(work_dir, "<temp>"), (sys.prefix, "<venv>"), (sys.base_prefix, "<python>"), (str(Path.home()), "<home>")]
    for folder, label in folders:
        if folder:
            text = text.replace(folder, label)
    return text


def _tail(text: str, limit: int = 2000) -> str:
    return text[-limit:]
