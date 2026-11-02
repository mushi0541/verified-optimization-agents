"""Format and inspect pipeline execution trajectories (#41).

Parses JSONL trace files produced by `optverify.run pipeline --trace` and renders
step-by-step trajectories, verification signal breakdowns, and summary tables.

Usage:
    python scripts/format_trajectories.py --traces logs/sample/*.jsonl --summary
    python scripts/format_trajectories.py --traces logs/sample/*.jsonl --cases canonical-1155 canonical-1250 canonical-1601 canonical-0890 --out docs/failures/trajectories.md
"""

import argparse
import glob
import json
import re
import sys
from pathlib import Path


def parse_trace_file(path: Path) -> dict:
    """Parse one JSONL trace log into a structured trajectory dictionary."""
    steps = []
    total_tokens = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
    total_latency_s = 0.0
    solver_attempts = []
    repair_steps = []
    paraphrase_runs = {}
    verifier_report = {}
    decision_report = {}
    explainer_text = ""
    prompt_text = ""
    parsed_spec = ""
    formalizer_code = ""

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            step = json.loads(line)
            role = step.get("role", "")
            tokens = step.get("tokens") or {}
            latency = float(step.get("latency_s", 0.0))

            for key in ("input_tokens", "output_tokens", "calls"):
                total_tokens[key] += int(tokens.get(key, 0))
            total_latency_s += latency

            out = step.get("output")
            inp = step.get("input")

            if role == "parser":
                prompt_text = inp if isinstance(inp, str) else ""
                parsed_spec = out if isinstance(out, str) else ""
            elif role == "formalizer":
                formalizer_code = out if isinstance(out, str) else ""
            elif role == "repair":
                repair_steps.append({
                    "input": inp if isinstance(inp, str) else "",
                    "output": out if isinstance(out, str) else "",
                    "tokens": tokens,
                    "latency_s": latency,
                })
            elif role == "solver":
                solver_attempts.append(out if isinstance(out, dict) else {"status": "unknown"})
            elif role.startswith("paraphrase_"):
                idx = role.split("_")[-1]
                if idx not in paraphrase_runs:
                    paraphrase_runs[idx] = {"text": "", "code": "", "solve": None}
                if isinstance(out, dict) and "status" in out:
                    paraphrase_runs[idx]["solve"] = out
                elif isinstance(out, str) and ("```python" in out or "import pulp" in out):
                    paraphrase_runs[idx]["code"] = out
                elif isinstance(out, str):
                    paraphrase_runs[idx]["text"] = out
            elif role == "verifier":
                verifier_report = out if isinstance(out, dict) else {}
            elif role == "decision":
                decision_report = out if isinstance(out, dict) else {}
            elif role == "explainer":
                explainer_text = out if isinstance(out, str) else ""

            steps.append(step)

    last_solver = solver_attempts[-1] if solver_attempts else {"status": "no_code", "objective": None}

    return {
        "problem_id": path.stem,
        "path": str(path),
        "steps_count": len(steps),
        "total_latency_s": round(total_latency_s, 2),
        "total_tokens": total_tokens,
        "prompt_text": prompt_text,
        "parsed_spec": parsed_spec,
        "formalizer_code": formalizer_code,
        "repair_steps": repair_steps,
        "solver_attempts": solver_attempts,
        "final_solver_status": last_solver.get("status"),
        "final_objective": last_solver.get("objective"),
        "paraphrases": paraphrase_runs,
        "verifier": verifier_report,
        "decision": decision_report,
        "explainer": explainer_text,
    }


def format_summary_table(trajectories: list[dict]) -> str:
    """Format a summary table across multiple parsed trajectories."""
    lines = [
        "| Problem ID | Steps | Attempts | Final Status | Objective | Agreement | Score | Action | Latency | Tokens |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in sorted(trajectories, key=lambda t: t["problem_id"]):
        pid = item["problem_id"]
        steps = item["steps_count"]
        attempts = len(item["solver_attempts"])
        status = item["final_solver_status"] or "unknown"
        obj = item["final_objective"]
        obj_str = f"{obj:.4f}" if isinstance(obj, float) else str(obj)
        v = item["verifier"]
        agreement = v.get("paraphrase_agreement")
        agr_str = f"{agreement:.2f}" if isinstance(agreement, (int, float)) else "none"
        score = v.get("score")
        score_str = f"{score:.3f}" if isinstance(score, (int, float)) else "none"
        action = item["decision"].get("action", "none")
        lat = f"{item['total_latency_s']:.1f}s"
        tok = item["total_tokens"]["input_tokens"] + item["total_tokens"]["output_tokens"]
        lines.append(f"| {pid} | {steps} | {attempts} | {status} | {obj_str} | {agr_str} | {score_str} | {action} | {lat} | {tok:,} |")
    return "\n".join(lines)


def clean_code_block(code: str) -> str:
    """Strip markdown code fence wrapper if present."""
    code = code.strip()
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    elif code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()
    return code


def format_single_trajectory_markdown(traj: dict) -> str:
    """Render a single trajectory as detailed GitHub-flavored markdown."""
    lines = []
    pid = traj["problem_id"]
    dec = traj["decision"].get("action", "none").upper()
    v = traj["verifier"]
    score = v.get("score")
    score_display = f"{score:.3f}" if isinstance(score, (int, float)) else "None"

    lines.append(f"### Problem: `{pid}` (Decision: `{dec}`, Score: `{score_display}`)")
    lines.append("")
    lines.append(f"- **Trace Log:** `{traj['path']}`")
    lines.append(f"- **Execution Latency:** {traj['total_latency_s']}s")
    tokens = traj["total_tokens"]
    lines.append(f"- **Token Usage:** {tokens['input_tokens']:,} input, {tokens['output_tokens']:,} output ({tokens['calls']} LLM calls)")
    lines.append("")

    # Prompt
    if traj["prompt_text"]:
        lines.append("#### 1. Input Problem Statement")
        lines.append("")
        lines.append("```text")
        lines.append(traj["prompt_text"].strip())
        lines.append("```")
        lines.append("")

    # Parser
    if traj["parsed_spec"]:
        lines.append("#### 2. Parser Specification")
        lines.append("")
        clean_spec = traj["parsed_spec"].strip()
        if not clean_spec.startswith("```"):
            lines.append("```json")
            lines.append(clean_spec)
            lines.append("```")
        else:
            lines.append(clean_spec)
        lines.append("")

    # Formalizer & Initial Solver
    if traj["formalizer_code"]:
        lines.append("#### 3. Formalizer Initial Code & First Solver Attempt")
        lines.append("")
        lines.append("```python")
        lines.append(clean_code_block(traj["formalizer_code"]))
        lines.append("```")
        lines.append("")
        if traj["solver_attempts"]:
            first_solve = traj["solver_attempts"][0]
            lines.append(f"- **Solver Status:** `{first_solve.get('status')}`")
            lines.append(f"- **Objective Value:** `{first_solve.get('objective')}`")
            if first_solve.get("error"):
                lines.append(f"- **Error Output:** `{first_solve.get('error')}`")
            lines.append("")

    # Repairs
    if traj["repair_steps"]:
        lines.append(f"#### 4. Self Repair ({len(traj['repair_steps'])} round)")
        for idx, rstep in enumerate(traj["repair_steps"], start=1):
            lines.append(f"##### Repair Attempt {idx}")
            lines.append("")
            lines.append("```python")
            lines.append(clean_code_block(rstep["output"]))
            lines.append("```")
            lines.append("")
            solve_after = traj["solver_attempts"][idx] if idx < len(traj["solver_attempts"]) else None
            if solve_after:
                lines.append(f"- **Solver Status After Repair:** `{solve_after.get('status')}`")
                lines.append(f"- **Objective Value After Repair:** `{solve_after.get('objective')}`")
                if solve_after.get("error"):
                    lines.append(f"- **Error Output:** `{solve_after.get('error')}`")
                lines.append("")

    # Paraphrases
    if traj["paraphrases"]:
        section_num = 5 if traj["repair_steps"] else 4
        lines.append(f"#### {section_num}. Paraphrase Rewordings & Consensus Checks")
        lines.append("")
        for p_idx, p_data in sorted(traj["paraphrases"].items()):
            solve = p_data.get("solve") or {}
            p_status = solve.get("status", "unknown")
            p_obj = solve.get("objective")
            lines.append(f"- **Rewording {p_idx}:** status `{p_status}`, objective `{p_obj}`")
            if p_data.get("text"):
                preview = p_data["text"].strip().replace("\n", " ")[:140]
                lines.append(f"  - *Prompt variant:* \"{preview}...\"")
        lines.append("")

    # Verifier
    if v:
        section_num = 6 if traj["repair_steps"] else 5
        lines.append(f"#### {section_num}. Verification Signals")
        lines.append("")
        lines.append("| Signal | Value | Passing / Detail |")
        lines.append("|---|---|---|")
        lines.append(f"| Solver Feasibility | `{v.get('feasible')}` | Status `{traj['final_solver_status']}` |")
        num_cov = v.get("number_coverage")
        num_str = f"{num_cov:.2%}" if isinstance(num_cov, float) else str(num_cov)
        missing_nums = ", ".join(v.get("missing_numbers", [])) or "None"
        lines.append(f"| Number Coverage | `{num_str}` | Missing: {missing_nums} |")
        req_cov = v.get("requirement_coverage")
        req_str = f"{req_cov:.2%}" if isinstance(req_cov, float) else str(req_cov)
        missing_reqs = ", ".join(v.get("missing_requirements", [])) or "None"
        lines.append(f"| Requirement Coverage | `{req_str}` | Missing: {missing_reqs} |")
        agr = v.get("paraphrase_agreement")
        agr_str = f"{agr:.2%}" if isinstance(agr, float) else str(agr)
        objs = str(v.get("paraphrase_objectives", []))
        lines.append(f"| Paraphrase Agreement | `{agr_str}` | Rewording values: {objs} |")
        lines.append(f"| Combined Verification Score | `{score_display}` | Calibrated threshold: `0.800` |")
        lines.append("")

    # Decision & Explainer
    section_num = 7 if traj["repair_steps"] else 6
    lines.append(f"#### {section_num}. Decision Gate & Explainer")
    lines.append("")
    d = traj["decision"]
    lines.append(f"- **Action:** `{d.get('action')}`")
    lines.append(f"- **Returned Answer:** `{d.get('answer')}`")
    reasons = d.get("reasons", [])
    if reasons:
        lines.append("- **Gate Reasons:**")
        for reason in reasons:
            lines.append(f"  - {reason}")
    else:
        lines.append("- **Gate Reasons:** All verification checks passed.")
    lines.append("")
    if traj["explainer"]:
        lines.append("**User Explanation:**")
        lines.append(f"> {traj['explainer'].strip()}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Format and inspect pipeline execution trajectories (#41).")
    parser.add_argument("--traces", nargs="+", required=True, help="Trace file paths or globs")
    parser.add_argument("--cases", nargs="*", help="Specific problem IDs to filter (e.g. canonical-1155)")
    parser.add_argument("--summary", action="store_true", help="Print trajectory summary table")
    parser.add_argument("--out", type=Path, help="Write markdown output to destination file")
    args = parser.parse_args()

    files = []
    for pattern in args.traces:
        matched = glob.glob(pattern)
        if matched:
            files.extend(matched)
        else:
            p = Path(pattern)
            if p.exists():
                files.append(str(p))

    files = sorted(set(files))
    if not files:
        sys.exit("Error: no trace files found matching provided paths.")

    trajectories = [parse_trace_file(Path(f)) for f in files]

    if args.cases:
        target_ids = set(args.cases)
        trajectories = [t for t in trajectories if t["problem_id"] in target_ids]

    if args.summary:
        print(format_summary_table(trajectories))

    if args.out:
        sections = ["# Pipeline Execution Trajectories", "", format_summary_table(trajectories), ""]
        for t in trajectories:
            sections.append(format_single_trajectory_markdown(t))
            sections.append("---")
            sections.append("")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(sections), encoding="utf-8")
        print(f"Wrote {len(trajectories)} trajectories to {args.out}")


if __name__ == "__main__":
    main()
