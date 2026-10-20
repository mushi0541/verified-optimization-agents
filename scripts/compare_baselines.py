"""B0 and B1 per problem class, and the comparison with the base paper's SIR results, from saved records only.

B0 is read from the first attempt of each B1 record and B1 from its last attempt (report Section 2.10).
For each class and overall it reports:
- accuracy at the 0.2% tolerance of the base paper's evaluation code and at the 0.1% tolerance stated in the
  paper text, each with an exact 95% interval;
- solved rate (optimal solver status) and silent failures (optimal status but a wrong objective);
- mean tokens and calls per problem;
- for B1: problems fixed and broken by the repair round, and an exact McNemar test of B0 against B1.

With --paper, the base paper's SIR accuracy per class (entered by hand from the paper) is shown next to B0 at the
paper's 0.1% rule. The file maps our class names to a value and its source, for example:
    {"Knapsack": {"sir_accuracy": 0.95, "source": "Table 3, DeepSeek-V3.2, mean over levels"}}

Example:
    python scripts/compare_baselines.py --baseline results/baseline_..._r1_.../records.jsonl --paper paper_sir.json --markdown
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optverify.grading import RELATIVE_TOLERANCE, is_correct  # noqa: E402
from scripts.analyze_e3 import baseline_points, clopper_pearson, load_records, mcnemar_p  # noqa: E402

PAPER_TOLERANCE = 0.001  # the tolerance stated in the base paper's text
SYSTEMS = ("B0", "B1")


def main() -> None:
    parser = argparse.ArgumentParser(description="B0 and B1 per class, and the base-paper comparison (no API calls).")
    parser.add_argument("--baseline", nargs="+", required=True, help="records.jsonl of B1 runs (baseline with --repairs 1)")
    parser.add_argument("--paper", help="JSON file with the base paper's SIR accuracy per class")
    parser.add_argument("--out", help="file to write the JSON result to")
    parser.add_argument("--markdown", action="store_true", help="print a per-class table instead of JSON")
    args = parser.parse_args()

    paper = json.loads(Path(args.paper).read_text(encoding="utf-8")) if args.paper else None
    result = compare(load_records(args.baseline), paper)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(markdown_table(result) if args.markdown else json.dumps(result, indent=2))


def outcomes(record: dict) -> dict[str, dict]:
    """B0 and B1 of one record, graded at both tolerances."""
    points = baseline_points(record)
    statuses = {"B0": record["attempts"][0]["solve"]["status"], "B1": record["attempts"][-1]["solve"]["status"]}
    graded = {}
    for name in SYSTEMS:
        answer = points[name]["answer"]
        graded[name] = {
            "correct": is_correct(answer, record["reference"], RELATIVE_TOLERANCE),
            "correct_strict": is_correct(answer, record["reference"], PAPER_TOLERANCE),
            "solved": statuses[name] == "optimal",
            "tokens": points[name]["tokens"],
            "calls": points[name]["calls"],
        }
    return graded


def summarize_group(group: list[dict[str, dict]]) -> dict:
    summary = {"problems": len(group)}
    for name in SYSTEMS:
        rows = [row[name] for row in group]
        correct, strict = sum(r["correct"] for r in rows), sum(r["correct_strict"] for r in rows)
        known_cost = None not in [r["tokens"] for r in rows]
        summary[name] = {
            "accuracy": correct / len(rows),
            "accuracy_ci": clopper_pearson(correct, len(rows)),
            "accuracy_strict": strict / len(rows),
            "accuracy_strict_ci": clopper_pearson(strict, len(rows)),
            "solved_rate": sum(r["solved"] for r in rows) / len(rows),
            "silent_failures": sum(r["solved"] and not r["correct"] for r in rows),
            "mean_tokens": sum(r["tokens"] for r in rows) / len(rows) if known_cost else None,
            "mean_calls": sum(r["calls"] for r in rows) / len(rows) if known_cost else None,
        }
    first, final = [row["B0"]["correct"] for row in group], [row["B1"]["correct"] for row in group]
    summary["repair"] = {
        "fixed": sum(not a and b for a, b in zip(first, final)),
        "broken": sum(a and not b for a, b in zip(first, final)),
        "mcnemar_p": mcnemar_p(first, final),
    }
    return summary


def compare(records: dict[str, dict], paper: dict | None = None) -> dict:
    if not records:
        raise ValueError("no baseline records")
    by_class: dict[str, list] = {}
    for record in records.values():
        by_class.setdefault(record["problem_class"], []).append(outcomes(record))

    if paper:
        unknown = sorted(set(paper) - set(by_class))
        if unknown:
            raise ValueError(f"paper classes not in the records: {unknown} (use the names {sorted(by_class)})")

    result = {
        "tolerances": {"accuracy": RELATIVE_TOLERANCE, "accuracy_strict": PAPER_TOLERANCE},
        "overall": summarize_group([row for group in by_class.values() for row in group]),
        "classes": {},
    }
    for name in sorted(by_class):
        summary = summarize_group(by_class[name])
        if paper and name in paper:
            reported = paper[name]["sir_accuracy"]
            summary["paper_sir"] = {
                "accuracy": reported,
                "source": paper[name].get("source", ""),
                "b0_minus_paper": summary["B0"]["accuracy_strict"] - reported,  # both at the paper's 0.1% rule
            }
        result["classes"][name] = summary
    return result


def markdown_table(result: dict) -> str:
    lines = [
        "| Class | n | B0 acc (0.2%) | B0 acc (0.1%) | B1 acc (0.2%) | Fixed / broken by repair | Silent failures B0 / B1 | Paper SIR |",
        "|---|---|---|---|---|---|---|---|",
    ]
    rows = list(result["classes"].items()) + [("All classes", result["overall"])]
    for name, summary in rows:
        paper = summary.get("paper_sir")
        paper_text = f"{paper['accuracy']:.1%}" if paper else ""
        lines.append(
            f"| {name} | {summary['problems']} | {_rate(summary['B0'], 'accuracy')} | {_rate(summary['B0'], 'accuracy_strict')} "
            f"| {_rate(summary['B1'], 'accuracy')} | {summary['repair']['fixed']} / {summary['repair']['broken']} "
            f"| {summary['B0']['silent_failures']} / {summary['B1']['silent_failures']} "
            f"| {paper_text} |"
        )
    return "\n".join(lines)


def _rate(system: dict, key: str) -> str:
    low, high = system[f"{key}_ci"]
    return f"{system[key]:.1%} [{low:.1%}, {high:.1%}]"


if __name__ == "__main__":
    main()
