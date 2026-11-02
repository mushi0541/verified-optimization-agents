"""Exploratory (#36): other rules for picking the threshold, under the same leave-one-class-out test (no API calls).

    python scripts/threshold_rules.py --records results/<run>/records.jsonl [--exclude-classes Pollution]
        --out results/gap2/threshold_rules/<name>

Each rule picks a threshold from the nine calibration classes; the held-out class is answered with it, and the
results are pooled over the ten folds, as in scripts/analyze_gap2.py. The rules:
- R0, pooled bound: the H2 rule itself (calibrate_threshold, a one-sided 95% bound at most alpha);
- R1, nested strictest: hold out each calibration class in turn and take the strictest of those thresholds, so the
  threshold has already survived a class shift (none when an inner fold has none);
- R2, worst class: the most lenient threshold at which every calibration class with 5 or more accepted answers has an
  observed wrong-accept rate at most alpha;
- R3, pooled rate: the most lenient threshold whose pooled observed rate is at most alpha, with no bound.
This is an exploratory comparison, not a replacement for H2: a rule chosen because it does well here would be tuned
on these runs.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from optverify.calibration import MIN_ACCEPTED, calibrate_threshold, load_run, scored_answers, upper_bound  # noqa: E402

ALPHAS = (0.08, 0.10, 0.12)
MIN_PER_CLASS = 5


def _thresholds(records: list[dict]) -> list[float]:
    return sorted({score for score, _ in scored_answers(records) if score > 0}, reverse=True)


def pooled_bound(calibration: list[dict], alpha: float) -> float | None:
    return calibrate_threshold(scored_answers(calibration), alpha)


def nested_strictest(calibration: list[dict], alpha: float) -> float | None:
    found = []
    for inner in sorted({r["problem_class"] for r in calibration}):
        threshold = calibrate_threshold(scored_answers([r for r in calibration if r["problem_class"] != inner]), alpha)
        if threshold is None:
            return None
        found.append(threshold)
    return max(found) if found else None


def worst_class(calibration: list[dict], alpha: float) -> float | None:
    by_class: dict[str, list[dict]] = {}
    for record in calibration:
        by_class.setdefault(record["problem_class"], []).append(record)
    chosen = None
    for threshold in _thresholds(calibration):
        for members in by_class.values():
            accepted = [ok for score, ok in scored_answers(members) if score >= threshold]
            if len(accepted) >= MIN_PER_CLASS and accepted.count(False) / len(accepted) > alpha:
                return chosen
        chosen = threshold
    return chosen


def pooled_rate(calibration: list[dict], alpha: float) -> float | None:
    scored = scored_answers(calibration)
    chosen = None
    for threshold in _thresholds(calibration):
        accepted = [ok for score, ok in scored if score >= threshold]
        if len(accepted) < MIN_ACCEPTED:
            continue
        if accepted.count(False) / len(accepted) > alpha:
            break
        chosen = threshold
    return chosen


RULES = {"R0 pooled bound": pooled_bound, "R1 nested strictest": nested_strictest, "R2 worst class": worst_class,
         "R3 pooled rate": pooled_rate}


def compare(records: list[dict], alphas=ALPHAS) -> list[dict]:
    finished = [r for r in records if "failed" not in r]
    rows = []
    for name, rule in RULES.items():
        for alpha in alphas:
            answered = wrong = 0
            for held_out in sorted({r["problem_class"] for r in records}):
                threshold = rule([r for r in finished if r["problem_class"] != held_out], alpha)
                test = [r for r in records if r["problem_class"] == held_out]
                accepted = [ok for score, ok in scored_answers(test) if threshold is not None and score >= threshold]
                answered += len(accepted)
                wrong += accepted.count(False)
            rows.append({"rule": name, "alpha": alpha, "problems": len(records), "answered": answered, "wrong": wrong,
                         "coverage": answered / len(records), "wrong_accept_rate": wrong / answered if answered else None,
                         "one_sided_bound": upper_bound(wrong, answered) if answered else None})
    return rows


def markdown(result: dict) -> str:
    pct = lambda v: "n/a" if v is None else f"{v:.1%}"  # noqa: E731
    excluded = result["excluded_classes"]
    lines = [f"# Threshold rules under leave-one-class-out: {result['records']}", "",
             "Exploratory, not the H2 result." + (f" Without {', '.join(excluded)}." if excluded else ""), "",
             "| Rule | Alpha | Answered | Coverage | Wrong | Wrong-accept rate | One-sided bound |",
             "|---|---|---|---|---|---|---|"]
    for row in result["rows"]:
        lines.append(f"| {row['rule']} | {row['alpha']:.0%} | {row['answered']}/{row['problems']} | "
                     f"{pct(row['coverage'])} | {row['wrong']} | {pct(row['wrong_accept_rate'])} | "
                     f"{pct(row['one_sided_bound'])} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--exclude-classes", nargs="+", default=[])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    records = [r for r in load_run(args.records) if r["problem_class"] not in args.exclude_classes]
    result = {"records": args.records.as_posix(), "excluded_classes": args.exclude_classes, "rows": compare(records)}
    text = markdown(result)
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "threshold_rules.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (args.out / "threshold_rules.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
