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

Repeats (course E1 and E2): pass each run with its own --repeat. Runs are grouped by the model in their records, and
each model gets one block labelled "reproduced (<model>, our runs)", so our gpt-oss-120b runs and the DeepSeek-V3.2
reproduction sit side by side; a block of B0-only runs (no repair round) leaves the B1 and repair cells empty. Each
number is the mean and sample standard deviation (n - 1) over the block's repeats, which needs 2 or more repeats.
The last column is the SIR accuracy reported in the paper: one number, with no standard deviation. The tables also
give silent failures and the problems fixed and broken by the repair round. --out-dir writes e1_e2.json, e1_e2.md
and e1_e2.csv.

Examples:
    python scripts/compare_baselines.py --baseline results/baseline_..._r1_.../records.jsonl --paper paper_sir.json --markdown
    python scripts/compare_baselines.py --repeat results/<run 1>/records.jsonl --repeat results/<run 2>/records.jsonl \\
        --repeat results/<run 3>/records.jsonl --paper docs/paper_sir.json --out-dir results/e1_e2
"""

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optverify.grading import RELATIVE_TOLERANCE, is_correct  # noqa: E402
from scripts.analyze_e3 import baseline_points, clopper_pearson, load_records, mcnemar_p  # noqa: E402

PAPER_TOLERANCE = 0.001  # the tolerance stated in the base paper's text
SYSTEMS = ("B0", "B1")
REPRODUCED = "reproduced ({model}, our runs)"
REPORTED = "reported in OPT-Engine (DeepSeek-V3.2, Table 2)"
DEVIATION_NOTE = (
    "Mean ± sample standard deviation (n - 1) over the repeats; the deviation needs 2 or more repeats. "
    "The paper's value is one reported number, with no standard deviation, and uses its 0.1% rule."
)
SYSTEM_METRICS = ("accuracy", "accuracy_strict", "solved_rate", "silent_failures", "mean_tokens", "mean_calls")
REPAIR_METRICS = ("fixed", "broken")
# Columns of the repeat tables: (system or "repair", metric, label).
TABLE_COLUMNS = [
    ("B0", "accuracy", "B0 accuracy, 0.2% rule"),
    ("B0", "accuracy_strict", "B0 accuracy, 0.1% rule"),
    ("B1", "accuracy", "B1 accuracy, 0.2% rule"),
    ("B1", "accuracy_strict", "B1 accuracy, 0.1% rule"),
    ("B0", "silent_failures", "B0 silent failures"),
    ("B1", "silent_failures", "B1 silent failures"),
    ("repair", "fixed", "Fixed by repair"),
    ("repair", "broken", "Broken by repair"),
]
COUNT_COLUMNS = {label for _, metric, label in TABLE_COLUMNS if metric in ("silent_failures", "fixed", "broken")}


def main() -> None:
    parser = argparse.ArgumentParser(description="B0 and B1 per class, and the base-paper comparison (no API calls).")
    runs = parser.add_mutually_exclusive_group(required=True)
    runs.add_argument("--baseline", nargs="+", help="records.jsonl of one B1 run (baseline with --repairs 1)")
    runs.add_argument(
        "--repeat", nargs="+", action="append", help="records.jsonl of one repeat (B1, or B0 only); give once per repeat; grouped by model"
    )
    parser.add_argument("--paper", help="JSON file with the base paper's SIR accuracy per class")
    parser.add_argument("--out", help="file to write the JSON result to")
    parser.add_argument("--out-dir", help="with --repeat: folder for e1_e2.json, e1_e2.md and e1_e2.csv")
    parser.add_argument("--markdown", action="store_true", help="print a per-class table instead of JSON")
    args = parser.parse_args()

    paper = json.loads(Path(args.paper).read_text(encoding="utf-8")) if args.paper else None
    if args.repeat:
        try:
            result = compare_models([load_records(paths) for paths in args.repeat], paper)
        except ValueError as error:
            parser.error(str(error))
        if args.out_dir:
            write_repeat_tables(result, Path(args.out_dir))
        print(repeats_markdown_table(result) if args.markdown else json.dumps(result, indent=2))
        return
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


def compare_models(repeats: list[dict[str, dict]], paper: dict | None = None) -> dict:
    """Group the repeats by the model that produced them, then compare_repeats() for each model.

    Each model gets its own block, labelled "reproduced (<model>, our runs)". A block may hold B0-only runs (no
    repair round), as for the DeepSeek-V3.2 reproduction of the base paper; its B1 and repair cells stay empty.
    """
    by_model: dict[str, list] = {}
    for records in repeats:
        models = {record["model"] for record in records.values()}
        if len(models) != 1:
            raise ValueError(f"one repeat mixes models: {sorted(models)}")
        by_model.setdefault(models.pop(), []).append(records)
    return {
        "labels": {"reproduced": REPRODUCED, "reported": REPORTED},
        "deviation": DEVIATION_NOTE,
        "models": [{"model": model, **compare_repeats(group, paper)} for model, group in by_model.items()],
    }


def compare_repeats(repeats: list[dict[str, dict]], paper: dict | None = None) -> dict:
    """compare() for each repeat of the same run, then the mean and standard deviation of each number."""
    if not repeats:
        raise ValueError("no repeats")
    for records in repeats[1:]:
        if set(records) != set(repeats[0]):
            differing = sorted(set(records) ^ set(repeats[0]))
            raise ValueError(f"the repeats do not cover the same problems; for example {', '.join(differing[:5])}")
    systems = {record["system"] for records in repeats for record in records.values()}
    if len(systems) != 1:
        raise ValueError(f"the repeats mix settings: {sorted(systems)}")
    with_repair = systems.pop() != "baseline_r0"
    runs = [compare(records, paper) for records in repeats]
    model = next(iter(repeats[0].values()))["model"]
    result = {
        "label": REPRODUCED.format(model=model),
        "repeats": len(runs),
        "with_repair": with_repair,
        "tolerances": runs[0]["tolerances"],
        "overall": _aggregate([run["overall"] for run in runs], with_repair),
        "classes": {},
    }
    for name in runs[0]["classes"]:
        summary = _aggregate([run["classes"][name] for run in runs], with_repair)
        paper_sir = runs[0]["classes"][name].get("paper_sir")
        if paper_sir:
            summary["reported"] = {"accuracy": paper_sir["accuracy"], "source": paper_sir["source"]}
            # Both at the paper's 0.1% rule.
            summary["b0_strict_minus_reported"] = summary["B0"]["accuracy_strict"]["mean"] - paper_sir["accuracy"]
        result["classes"][name] = summary
    result["runs"] = runs  # every repeat in full, so each mean can be traced back to its runs
    return result


def _aggregate(summaries: list[dict], with_repair: bool = True) -> dict:
    missing = {"mean": None, "sd": None}
    aggregated = {"problems": summaries[0]["problems"]}
    for name in SYSTEMS:
        if name == "B1" and not with_repair:  # a B0-only run has no B1
            aggregated[name] = {metric: missing for metric in SYSTEM_METRICS}
            continue
        aggregated[name] = {metric: mean_and_sd([s[name][metric] for s in summaries]) for metric in SYSTEM_METRICS}
    aggregated["repair"] = {
        metric: mean_and_sd([s["repair"][metric] for s in summaries]) if with_repair else missing
        for metric in REPAIR_METRICS
    }
    return aggregated


def mean_and_sd(values: list) -> dict:
    """Mean and sample standard deviation (n - 1) over repeats. The deviation needs 2 or more repeats, and a missing
    value (an unknown cost) leaves both missing."""
    if not values or None in values:
        return {"mean": None, "sd": None}
    return {"mean": statistics.mean(values), "sd": statistics.stdev(values) if len(values) >= 2 else None}


def repeat_rows(block: dict) -> list[dict]:
    """One row per class and one for all classes, shared by the Markdown and CSV tables."""
    rows = []
    for name, summary in list(block["classes"].items()) + [("All classes", block["overall"])]:
        row = {"class": name, "problems": summary["problems"]}
        for system, metric, label in TABLE_COLUMNS:
            row[label] = summary["repair"][metric] if system == "repair" else summary[system][metric]
        reported = summary.get("reported")
        row[f"SIR accuracy, {REPORTED}"] = reported["accuracy"] if reported else None
        rows.append(row)
    return rows


def repeats_markdown_table(result: dict) -> str:
    lines = [DEVIATION_NOTE]
    for block in result["models"]:
        rows = repeat_rows(block)
        columns = list(rows[0])[2:]
        title = f"### {block['label']}: {block['repeats']} repeat(s)"
        lines += [
            "",
            title if block["with_repair"] else title + ", B0 only (no repair round)",
            "",
            "| Class | n | " + " | ".join(columns) + " |",
            "|---|---|" + "---|" * len(columns),
        ]
        for row in rows:
            cells = [str(row["class"]), str(row["problems"])]
            for column in columns:
                value = row[column]
                cells.append(_mean_sd_text(value, column in COUNT_COLUMNS) if isinstance(value, dict) else _percent(value))
            lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_repeat_tables(result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "e1_e2.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out_dir / "e1_e2.md").write_text(repeats_markdown_table(result) + "\n", encoding="utf-8")
    with (out_dir / "e1_e2.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        for number, block in enumerate(result["models"]):
            rows = repeat_rows(block)
            columns = list(rows[0])[2:]
            if number == 0:
                header = ["model", "repeats", "class", "problems"]
                for column in columns:
                    header += [f"{column} (mean)", f"{column} (sd)"] if isinstance(rows[0][column], dict) else [column]
                writer.writerow(header)
            for row in rows:
                cells = [block["model"], block["repeats"], row["class"], row["problems"]]
                for column in columns:
                    value = row[column]
                    cells += [value["mean"], value["sd"]] if isinstance(value, dict) else [value]
                writer.writerow(["" if cell is None else cell for cell in cells])


def _mean_sd_text(value: dict, as_count: bool = False) -> str:
    if value["mean"] is None:
        return ""
    show = (lambda v: f"{v:.1f}") if as_count else (lambda v: f"{v:.1%}")
    return show(value["mean"]) if value["sd"] is None else f"{show(value['mean'])} ± {show(value['sd'])}"


def _percent(value: float | None) -> str:
    return "" if value is None else f"{value:.1%}"


def _rate(system: dict, key: str) -> str:
    low, high = system[f"{key}_ci"]
    return f"{system[key]:.1%} [{low:.1%}, {high:.1%}]"


if __name__ == "__main__":
    main()
