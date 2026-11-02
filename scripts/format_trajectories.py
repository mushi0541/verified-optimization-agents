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


FAILURE_CATEGORIES = {
    "wrong constraint": {
        "title": "Wrong Constraint Form or Bound",
        "description": "A constraint is explicitly formulated in the model code, but its mathematical expression, inequality direction, or index range is incorrect.",
        "examples": [
            "Miller-Tucker-Zemlin subtour elimination in TSP: applying u_i - u_j + N*x_ij <= N - 1 across all city pairs including start city 1, making complete tours impossible and causing model infeasibility (canonical-1457).",
            "Conditional capacity adjustment in Knapsack: subtracting a crate capacity penalty from payload rather than adding it, effectively loosening capacity (constraint-0864).",
            "BinPacking crate usage constraint: writing y[j] >= sum(x[i][j]) with binary y[j] <= 1, which accidentally restricts crates to at most one box (canonical-0310).",
            "Production vehicle processing: treating multi-stage processing times across multiple vehicles as single-vehicle assignment, leading all rewordings to agree on an inflated objective (canonical-1706).",
        ],
        "likely_cause": (
            "Parser outputs textbook formulation templates (such as general MTZ) without scoping index bounds for base nodes. "
            "In other cases, linguistic phrasing of conditional rules creates confusion between addition and subtraction, or "
            "prior training biases lead the LLM to choose classic assignment structures over sequential resource consumption."
        ),
        "future_fix": (
            "1. Domain-specific boundary checking in parser prompts, explicitly reminding the model to exclude origin nodes from MTZ subtour loops. "
            "2. Targeted repair prompts triggered by solver status 'infeasible', asking the model to check subtour indices, conflicting bounds, and capacity inequality signs. "
            "3. Multi-family paraphrasers (such as DeepSeek or alternative architectures) to break correlated misreadings across rewordings."
        ),
    },
    "missing constraint": {
        "title": "Missing Constraint",
        "description": "A requirement or physical restriction stated in the problem description is completely omitted from the formulated model.",
        "examples": [
            "JobShop scheduling: Python dict iteration bug unpacked keys as strings, skipping the non-overlap time window constraints entirely (canonical-0933).",
            "Portfolio allocation: asset minimum allocation lower bounds were not declared on LpVariable or added as constraints (canonical-1390).",
            "TSP delivery specifications: requirements R2 and R5 from prompt were identified by parser but never translated into PuLP constraints (constraint-0991).",
        ],
        "likely_cause": (
            "Formalizer overlooks parsed requirement bullets when generating code, or subtle Python coding bugs "
            "(empty loops, misplaced indentation, uninitialized dictionary sets) silently omit constraint creation."
        ),
        "future_fix": (
            "1. Enforce strict requirement linking in the verifier: every requirement tagged by the parser must have a named PuLP constraint. "
            "2. Pre-solve constraint count assertions: verify that each indexed constraint set has non-zero elements added to the model. "
            "3. Reject or down-weight any model whose requirement coverage score falls below 1.0."
        ),
    },
    "integrality error": {
        "title": "Integrality Error",
        "description": "Indivisible discrete decisions or quantities are declared as continuous variables, solving the linear relaxation rather than the integer program.",
        "examples": [
            "Knapsack item selection: 0-1 package variables declared as pulp.LpContinuous between 0 and 1, producing fractional packing (constraint-0749).",
        ],
        "likely_cause": (
            "Default formalizer prompt habits default to continuous LP variables unless explicitly instructed, "
            "or the prompt wording does not make discrete package indivisibility prominent."
        ),
        "future_fix": (
            "1. Pre-solve AST inspection checking whether variables declared continuous correspond to discrete nouns (items, trucks, crates). "
            "2. Post-solve integrality verification: inspect solver variable values; if binary decisions take fractional values, flag the solution for repair."
        ),
    },
    "code error": {
        "title": "Code Execution Error",
        "description": "The generated Python code fails to execute due to syntax errors, import mismatches, missing identifiers, or solver crashes.",
        "examples": [
            "Portfolio optimization: syntax error in PuLP summation indexing causing solver script termination on attempt 1 (canonical-1250).",
            "Nine code crashes in E3 repeat 1, all safely caught and refused by the pipeline without accepting wrong answers.",
        ],
        "likely_cause": (
            "Hallucinated PuLP methods, malformed dictionary keys, or invalid variable expressions generated under complex formulations."
        ),
        "future_fix": (
            "1. Automated self-repair round feeding solver tracebacks directly back to the formalizer (demonstrated in canonical-1250). "
            "2. Static code analysis and syntax pre-validation before sub-process execution."
        ),
    },
    "false alarm": {
        "title": "False Alarm (Spurious Escalation)",
        "description": "The system produces a mathematically correct formulation and answer, but verification gate heuristics unnecessarily escalate or abstain.",
        "examples": [
            "19 of 20 false alarms in E3 repeat 1 resulted from paraphrase disagreement when one rewording produced an alternative valid formulation or minor reading discrepancy (canonical-0652).",
            "Numbers extracted from conversational text (e.g. year, asset count) flagged as unused numbers despite the core math being sound.",
        ],
        "likely_cause": (
            "Small paraphrase sample size (k = 3) where a single diverging rewording drops agreement from 1.0 to 0.0 or 0.33, collapsing the combined score. "
            "Literal numeric matching lacking semantic awareness of conversational vs parametric numbers."
        ),
        "future_fix": (
            "1. Consensus voting with higher k (e.g. k = 5 with majority clustering) rather than strict unanimous consensus. "
            "2. Semantic filtering of extracted numbers to separate parametric values from descriptive counts or dates."
        ),
    },
    "doubtful reference": {
        "title": "Doubtful Benchmark Reference",
        "description": "The benchmark ground-truth answer does not correspond to the problem text due to infeasible problem parameters or ambiguous temporal/cost definitions.",
        "examples": [
            "Pollution control benchmark problems where stated abatement constraints require emissions reductions impossible under capacity limits, or reference values are lower than the theoretical minimum cost. "
            "Inventory problems with conflicting holding cost timing or delivery lead-time phrasing.",
        ],
        "likely_cause": (
            "Flaws in upstream synthetic dataset generation or automated problem formulation in the benchmark source."
        ),
        "future_fix": (
            "1. Independent reference audits and dual-reporting (evaluating performance both with and without doubtful classes). "
            "2. Automated cross-solver reference validation on all benchmark problems before evaluation."
        ),
    },
}


def format_category_analysis_markdown() -> str:
    """Format root causes and future work mitigations for each failure category."""
    lines = [
        "## Failure Categories: Root Causes and Future Work",
        "",
        "This section documents the primary failure categories identified across evaluation runs, ",
        "their typical manifestation in optimization formulations, root causes, and recommended engineering fixes.",
        "",
    ]
    for cat_key, info in FAILURE_CATEGORIES.items():
        lines.append(f"### Category: `{cat_key}` ({info['title']})")
        lines.append("")
        lines.append(f"**Definition:** {info['description']}")
        lines.append("")
        lines.append("**Empirical Examples:**")
        for ex in info["examples"]:
            lines.append(f"- {ex}")
        lines.append("")
        lines.append(f"**Likely Root Cause:** {info['likely_cause']}")
        lines.append("")
        lines.append(f"**Future Work Mitigation:** {info['future_fix']}")
        lines.append("")
    return "\n".join(lines)



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
    parser.add_argument("--causes", action="store_true", help="Include failure category root causes and future work")
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

    if args.causes and not args.out:
        print(format_category_analysis_markdown())

    if args.out:
        sections = [
            "# Pipeline Execution Trajectories and Failure Analysis",
            "",
            "## Summary Table",
            "",
            format_summary_table(trajectories),
            "",
            "## Case Study Trajectories",
            "",
        ]
        for t in trajectories:
            sections.append(format_single_trajectory_markdown(t))
            sections.append("---")
            sections.append("")
        if args.causes or True:
            sections.append(format_category_analysis_markdown())
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(sections), encoding="utf-8")
        print(f"Wrote {len(trajectories)} trajectories to {args.out}")


if __name__ == "__main__":
    main()
