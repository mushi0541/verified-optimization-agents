"""Agent roles: parser, formalizer (with solver-feedback repair), paraphraser and explainer.

Each role takes plain inputs, calls the LLM at most a few times, and adds its token use to the shared counter.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from . import prompts
from .contracts import Attempt, Decision, TokenUsage, VerifierReport
from .llm import LLM
from .solver_tool import extract_code, run_model_code

if TYPE_CHECKING:
    from .trace import TraceWriter

# The parser lists every number of the problem, so on large instances (network flow with 100 arcs, TSP with 100 edges)
# its JSON did not fit in the default 4,096 output tokens and was cut off: 9 of 24 dev-split calls failed this way.
PARSE_MAX_TOKENS = 12000


def parse_problem(
    question: str,
    llm: LLM,
    usage: TokenUsage,
    trace: TraceWriter | None = None,
) -> dict | None:
    """The parser's JSON spec, or None. A reply that is not valid JSON is asked for once more (2 of 9 dev calls)."""
    prompt = prompts.PARSE.format(question=question)
    for _ in range(2):
        reply = llm.complete(prompt, max_tokens=PARSE_MAX_TOKENS)
        usage.add(reply.usage)
        if trace is not None:
            trace.record("parser", prompt, reply.text, reply.usage, reply.latency_s)
        spec = _first_json_object(reply.text)
        if spec is not None:
            return spec
    return None


def number_requirements(spec: dict | None) -> tuple[dict | None, list[str]]:
    """The parser output with its requirements keyed by ID ("R1", "R2", ...), as the formalizer sees it, and the IDs.

    Without a requirement list (the parser failed or returned another shape) the spec is kept and there are no IDs.
    """
    if not spec or not isinstance(spec.get("requirements"), list) or not spec["requirements"]:
        return spec, []
    numbered = {f"R{i}": text for i, text in enumerate(spec["requirements"], start=1)}
    return {**spec, "requirements": numbered}, list(numbered)


def formalize_and_solve(
    first_prompt: str,
    question: str,
    llm: LLM,
    usage: TokenUsage,
    max_repairs: int,
    *,
    role: str,
    solver_role: str,
    repair_usage: TokenUsage | None = None,
    repair_note: str = "",
    trace: TraceWriter | None = None,
) -> list[Attempt]:
    """Write model code, run it, and repair it from solver/runtime errors only (never from the reference answer).

    Repair calls are counted in repair_usage when it is given, otherwise in usage. repair_note is added to the
    repair instruction (the pipeline uses it to keep the constraint names)."""
    attempts = []
    prompt = first_prompt
    for round_number in range(max_repairs + 1):
        reply = llm.complete(prompt)
        (usage if round_number == 0 or repair_usage is None else repair_usage).add(reply.usage)
        step_role = role if round_number == 0 else "repair"
        if trace is not None:
            trace.record(step_role, prompt, reply.text, reply.usage, reply.latency_s)
        code = extract_code(reply.text)
        result = run_model_code(code)
        attempts.append(Attempt(code=code or "", solve=result))
        if trace is not None:
            trace.record(
                solver_role,
                code or "",
                {"status": result.status, "objective": result.objective, "error": result.error},
                tokens=None,
                latency_s=result.runtime_s,
            )
        if result.status == "optimal":
            break
        problem_text = result.error or f"The solver finished with status '{result.status}'."
        prompt = prompts.REPAIR.format(
            question=question, code=code or "(no code returned)", error=problem_text, note=repair_note
        )
    return attempts


def paraphrase(
    question: str,
    llm: LLM,
    usage: TokenUsage,
    *,
    role: str,
    trace: TraceWriter | None = None,
) -> str:
    prompt = prompts.PARAPHRASE.format(question=question)
    reply = llm.complete(prompt)
    usage.add(reply.usage)
    if trace is not None:
        trace.record(role, prompt, reply.text, reply.usage, reply.latency_s)
    return reply.text.strip()


def explain(
    decision: Decision,
    report: VerifierReport,
    variables: dict[str, float] | None = None,
) -> str:
    """Plain-language note for the operations user. Deterministic, so it costs no tokens."""
    if decision.action == "answer":
        opening = f"Recommended plan found. Optimal objective value: {decision.answer:g}."
    elif decision.action == "escalate":
        opening = "A plan was found, but the checks did not pass. Please have an analyst review it before use."
    else:
        opening = "The system could not build a working model, so it is not giving an answer."
    checks = f"Checks: number coverage {report.number_coverage:.0%}"
    if report.requirement_coverage is not None:
        checks += f", requirement coverage {report.requirement_coverage:.0%}"
    if report.paraphrase_agreement is not None:
        checks += f", reworded-question agreement {report.paraphrase_agreement:.0%}"
    summary = " ".join([opening, checks + ".", *decision.reasons])
    if decision.action != "answer" or not variables:
        return summary
    lines = [summary]
    for name, value in sorted(variables.items()):
        lines.append(f"{name}: {value:g}")
    return "\n".join(lines)


def _first_json_object(text: str) -> dict | None:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
