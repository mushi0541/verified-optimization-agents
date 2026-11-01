"""Failure analysis (#41): a label file from pipeline records, then frequency tables from the finished labels.

    python scripts/failure_analysis.py draft --records results/<run>/records.jsonl ... --out results/failures/labels.csv
    python scripts/failure_analysis.py table --labels results/failures/labels.csv --records ... --out results/failures

`draft` writes one row for every wrong answer and every false alarm, with evidence that needs no judgement:
- the outcome: wrong accept (answered and wrong), correct refusal (wrong and escalated or abstained) or false alarm
  (correct but escalated or abstained);
- the last solver status, the relative gap to the reference, and its direction: "looser" when the wrong optimum is
  better than the reference in the code's own sense (a constraint is missing or too weak, or integrality was
  dropped), "tighter" when it is worse;
- whether the code's objective sense matches the parsed one, and whether the class is one whose reference answers
  are being hand-checked (#40).

Rows that need no judgement get their label at once: code errors (no code, or code that crashed) and false alarms
(labelled by the signal that raised them). The other wrong answers, including infeasible models (a symptom whose cause
still has to be read), are labelled by a person in the `label` column, with a short reason in `note`. A blank label
means pending: `table` counts pending rows apart, and with --complete it refuses them. It always refuses an unknown
label, a repeated row, and a label file that does not match the records.
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path, PureWindowsPath

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Labels for a wrong model, from #41, plus "wrong constraint" (a constraint that is there but has the wrong form or
# bound, proposed on #41). An infeasible model gets the label of its cause, read by hand.
WRONG_LABELS = (
    "missing constraint",
    "wrong constraint",
    "wrong data value",
    "wrong objective sense",
    "integrality error",
    "code error",
    "doubtful reference",
    "other",
)
PENDING = ""  # a blank label: not labelled yet (for example waiting for the reference hand-check, #40)
# Labels for a false alarm: the signal that stopped a correct answer.
FALSE_ALARM_LABELS = ("paraphrase disagreement", "requirement not linked", "number not used")
DOUBTFUL_REFERENCE_CLASSES = {"Inventory", "Pollution"}  # hand-checked in #40
OUTCOMES = ("wrong accept", "correct refusal", "false alarm")
COLUMNS = (
    "sample", "problem_id", "problem_class", "outcome", "decision", "reference", "predicted", "final_status",
    "attempts", "relative_gap", "direction", "code_sense", "parsed_sense", "doubtful_reference_class", "reasons",
    "label", "note",
)


def read_records(path: Path) -> tuple[str, list[dict]]:
    """The sample name (from the run's summary.json) and the finished records of one run."""
    summary = json.loads((path.parent / "summary.json").read_text(encoding="utf-8"))
    sample = PureWindowsPath(summary["config"]["sample_file"]).stem  # a Windows path (samples\x.json) also works on POSIX
    with path.open(encoding="utf-8") as file:
        records = [json.loads(line) for line in file if line.strip()]
    return sample, [record for record in records if "failed" not in record]


def outcome(record: dict) -> str | None:
    """The outcome of a record, or None for a correct answer that was given (a success)."""
    answered = (record.get("decision") or {}).get("action") == "answer"
    if record["correct"]:
        return None if answered else "false alarm"
    return "wrong accept" if answered else "correct refusal"


def code_sense(code: str) -> str:
    """minimize or maximize, from the last PuLP sense in the code; empty when the code names none."""
    senses = re.findall(r"Lp(Maximize|Minimize)", code or "")
    return senses[-1].lower() if senses else ""


def draft_row(sample: str, record: dict) -> dict:
    last = record["attempts"][-1] if record["attempts"] else {"code": "", "solve": {"status": "no_code"}}
    status = last["solve"]["status"]
    reference, predicted = record["reference"], record["predicted"]
    sense = code_sense(last.get("code", ""))
    gap, direction = "", ""
    if predicted is not None and reference not in (None, 0):
        gap = round((predicted - reference) / abs(reference), 4)
        if sense and predicted != reference:
            better = predicted > reference if sense == "maximize" else predicted < reference
            direction = "looser" if better else "tighter"
    kind = outcome(record)
    decision = record.get("decision") or {}
    label = ""
    if kind == "false alarm":
        label = false_alarm_label(record.get("verifier") or {})
    elif status in ("no_code", "error"):
        label = "code error"
    return {
        "sample": sample,
        "problem_id": record["problem_id"],
        "problem_class": record["problem_class"],
        "outcome": kind,
        "decision": decision.get("action", ""),
        "reference": reference,
        "predicted": predicted,
        "final_status": status,
        "attempts": len(record["attempts"]),
        "relative_gap": gap,
        "direction": direction,
        "code_sense": sense,
        "parsed_sense": (record.get("spec") or {}).get("objective_sense", ""),
        "doubtful_reference_class": "yes" if record["problem_class"] in DOUBTFUL_REFERENCE_CLASSES else "no",
        "reasons": " | ".join(decision.get("reasons", [])),
        "label": label,
        "note": "" if status in ("optimal", "no_code", "error") or kind == "false alarm" else f"{status} model; cause to label",
    }


def false_alarm_label(report: dict) -> str:
    """The signal that cost a correct answer its score: paraphrase disagreement first, as it weighs the most."""
    if report.get("paraphrase_agreement") is not None and report["paraphrase_agreement"] < 1:
        return "paraphrase disagreement"
    if report.get("missing_requirements"):
        return "requirement not linked"
    return "number not used"


def draft(record_paths: list[Path], out: Path) -> list[dict]:
    rows = []
    for path in record_paths:
        sample, records = read_records(path)
        rows += [draft_row(sample, record) for record in records if outcome(record)]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def check_labels(rows: list[dict], complete: bool = False) -> None:
    """Every label must be known; a repeated row would be counted twice. With complete, no row may be pending."""
    seen = set()
    for row in rows:
        key = (row["sample"], row["problem_id"])
        if key in seen:
            raise SystemExit(f"{row['sample']} {row['problem_id']} appears twice in the label file")
        seen.add(key)
        allowed = FALSE_ALARM_LABELS if row["outcome"] == "false alarm" else WRONG_LABELS
        if row["label"] == PENDING and not complete:
            continue
        if row["label"] not in allowed:
            raise SystemExit(f"{row['sample']} {row['problem_id']}: label {row['label']!r} is not one of {allowed}")


def table(label_file: Path, record_paths: list[Path], out_dir: Path, complete: bool = False) -> dict:
    with label_file.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    check_labels(rows, complete)
    totals = Counter()
    expected = set()
    for path in record_paths:
        sample, records = read_records(path)
        totals[sample] += len(records)
        expected |= {(sample, record["problem_id"]) for record in records if outcome(record)}
    samples = sorted(totals)
    labelled = {(row["sample"], row["problem_id"]) for row in rows}
    if labelled != expected:
        raise SystemExit(f"the label file does not match the records: {len(labelled ^ expected)} rows differ")

    outcomes = {
        sample: {kind: sum(row["sample"] == sample and row["outcome"] == kind for row in rows) for kind in OUTCOMES}
        for sample in samples
    }
    for sample in samples:
        outcomes[sample] = {"problems": totals[sample], **outcomes[sample]}
    wrong = [row for row in rows if row["outcome"] != "false alarm"]
    by_label = {
        label: {
            "wrong accept": sum(row["label"] == label and row["outcome"] == "wrong accept" for row in wrong),
            "correct refusal": sum(row["label"] == label and row["outcome"] == "correct refusal" for row in wrong),
        }
        for label in WRONG_LABELS
    }
    false_alarms = Counter(row["label"] for row in rows if row["outcome"] == "false alarm")
    pending = [row for row in rows if row["label"] == PENDING]
    by_label["pending"] = {
        "wrong accept": sum(row["outcome"] == "wrong accept" for row in pending),
        "correct refusal": sum(row["outcome"] == "correct refusal" for row in pending),
    }
    result = {
        "outcomes": outcomes,
        "pending_rows": len(pending),
        "wrong_by_label": by_label,
        "false_alarms_by_signal": {label: false_alarms[label] for label in FALSE_ALARM_LABELS},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "failures.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (out_dir / "failures.md").write_text(markdown(result, len(wrong)), encoding="utf-8")
    return result


def markdown(result: dict, wrong_total: int) -> str:
    lines = ["# Failure analysis", "", "## Outcomes per sample", "",
             "| Sample | Problems | Wrong accept | Correct refusal | False alarm |", "|---|---|---|---|---|"]
    for sample, counts in result["outcomes"].items():
        lines.append(f"| {sample} | {counts['problems']} | " + " | ".join(str(counts[kind]) for kind in OUTCOMES) + " |")
    if result["pending_rows"]:
        lines += ["", f"**Not final:** {result['pending_rows']} rows are still pending (blank label), shown as 'pending'."]
    lines += ["", f"## Wrong answers by category ({wrong_total} in all)", "",
              "| Category | Wrong accept | Correct refusal | Total | Share |", "|---|---|---|---|---|"]
    for label, counts in sorted(result["wrong_by_label"].items(), key=lambda item: -sum(item[1].values())):
        total = sum(counts.values())
        if total:
            share = f"{100 * total / wrong_total:.1f}%"
            lines.append(f"| {label} | {counts['wrong accept']} | {counts['correct refusal']} | {total} | {share} |")
    lines += ["", "## False alarms by signal", "", "| Signal | Count |", "|---|---|"]
    lines += [f"| {label} | {count} |" for label, count in result["false_alarms_by_signal"].items()]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Failure analysis (#41) from pipeline records (no API calls).")
    commands = parser.add_subparsers(dest="command", required=True)
    draft_parser = commands.add_parser("draft", help="write the label file with evidence and the automatic labels")
    draft_parser.add_argument("--records", type=Path, nargs="+", required=True)
    draft_parser.add_argument("--out", type=Path, required=True)
    table_parser = commands.add_parser("table", help="frequency tables from a finished label file")
    table_parser.add_argument("--labels", type=Path, required=True)
    table_parser.add_argument("--records", type=Path, nargs="+", required=True)
    table_parser.add_argument("--out", type=Path, required=True)
    table_parser.add_argument("--complete", action="store_true", help="refuse pending (blank) labels: the final table")
    args = parser.parse_args()
    if args.command == "draft":
        rows = draft(args.records, args.out)
        open_rows = sum(not row["label"] for row in rows)
        print(f"{len(rows)} rows written to {args.out}; {open_rows} still need a label")
    else:
        print(json.dumps(table(args.labels, args.records, args.out, args.complete), indent=2))


if __name__ == "__main__":
    main()
