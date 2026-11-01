"""E4 Gap 2 (H2): calibrated abstention tested leave-one-class-out, from saved records, no API calls.

    python scripts/analyze_gap2.py --records results/<pipeline repeat 1>/records.jsonl results/<repeat 2>/records.jsonl \
        --baseline results/<B1 run>/records.jsonl --subset samples/canonical_100.json --out results/gap2/canonical_200

For each pipeline repeat and each target alpha (5%, 10% and 20% by default):
- the leave-one-class-out test of `optverify.calibration` (calibrate on nine classes, test on the tenth): per-fold
  thresholds and rates, and the pooled held-out wrong-accept rate with its exact 95% interval and coverage;
- the fixed 0.8 threshold on the same records (ablation vi);
- with --subset, the same test on only the problems in that sample file. canonical_200 starts with canonical_100, so
  this shows how much the 20-per-class sample narrows the interval compared with 10 per class (supervisor feedback).
B0 is the reference: it answers whenever its first model is optimal and never abstains.

H2 is supported in a repeat when, at alpha = 10%, the pooled held-out wrong-accept rate is at most alpha and at least
50% of all problems are answered; the exact upper bound is reported next to it. Over the repeats the verdict is
"supported" only if it holds in every repeat.

The risk-coverage curve (wrong-accept rate against coverage as the threshold moves over every score) is written to
risk_coverage.csv and drawn to risk_coverage.pdf and .png, with the calibrated and fixed thresholds marked.
"""

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optverify.calibration import fixed_threshold, leave_one_class_out, scored_answers  # noqa: E402
from optverify.grading import is_correct  # noqa: E402

H2_ALPHA = 0.10
MIN_COVERAGE = 0.5


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def risk_coverage(records: list[dict]) -> list[dict]:
    """Coverage and wrong-accept rate for every threshold, from strict to lenient."""
    finished = [r for r in records if "failed" not in r]
    scored = scored_answers(finished)
    points = []
    for threshold in sorted({score for score, _ in scored}, reverse=True):
        accepted = [correct for score, correct in scored if score >= threshold]
        points.append({
            "threshold": threshold,
            "coverage": len(accepted) / len(finished),
            "wrong_accept_rate": accepted.count(False) / len(accepted),
        })
    return points


def b0_reference(baseline: list[dict], problem_ids: set[str]) -> dict:
    """B0 (the first attempt of B1 records) on the same problems; it answers whenever its model is optimal."""
    rows = [r for r in baseline if "failed" not in r and r["problem_id"] in problem_ids]
    answered = [r for r in rows if r["attempts"][0]["solve"]["status"] == "optimal"]
    wrong = sum(not is_correct(r["attempts"][0]["solve"]["objective"], r["reference"]) for r in answered)
    return {
        "problems": len(rows),
        "answered": len(answered),
        "coverage": len(answered) / len(rows) if rows else 0.0,
        "wrong_accepted": wrong,
        "wrong_accept_rate": wrong / len(answered) if answered else None,
    }


def h2_check(test: dict) -> dict:
    pooled = test["pooled"]
    rate = pooled["wrong_accept_rate"]
    return {
        "rate_ok": rate is not None and rate <= test["alpha"],
        "coverage_ok": pooled["coverage"] >= MIN_COVERAGE,
        "upper_bound_ok": pooled["exact_interval"][1] <= test["alpha"],
        "supported": rate is not None and rate <= test["alpha"] and pooled["coverage"] >= MIN_COVERAGE,
    }


def analyze_run(records: list[dict], alphas: list[float], fixed: float, subset: set[str] | None) -> dict:
    result = {
        "problems": sum("failed" not in r for r in records),
        "failed_problems": sum("failed" in r for r in records),
        "by_alpha": {},
        "fixed": fixed_threshold(records, fixed),
        "risk_coverage": risk_coverage(records),
    }
    for alpha in alphas:
        test = leave_one_class_out(records, alpha)
        entry = {"test": test, "h2": h2_check(test)}
        if subset:
            small = leave_one_class_out([r for r in records if r["problem_id"] in subset], alpha)
            entry["subset"] = {"problems": small["problems"], "pooled": small["pooled"]}
            entry["interval_width"] = {"all": _width(test["pooled"]), "subset": _width(small["pooled"])}
        result["by_alpha"][str(alpha)] = entry
    return result


def _width(pooled: dict) -> float:
    low, high = pooled["exact_interval"]
    return high - low


def mean_and_sd(values: list[float | None]) -> dict:
    present = [v for v in values if v is not None]
    return {
        "mean": statistics.mean(present) if present else None,
        "sd": statistics.stdev(present) if len(present) > 1 else None,
        "repeats_with_value": len(present),
    }


def summarize(runs: list[dict], alphas: list[float]) -> dict:
    summary = {"by_alpha": {}}
    for alpha in alphas:
        tests = [run["by_alpha"][str(alpha)]["test"] for run in runs]
        summary["by_alpha"][str(alpha)] = {
            "wrong_accept_rate": mean_and_sd([t["pooled"]["wrong_accept_rate"] for t in tests]),
            "coverage": mean_and_sd([t["pooled"]["coverage"] for t in tests]),
            "upper_bound": mean_and_sd([t["pooled"]["exact_interval"][1] for t in tests]),
        }
    summary["fixed"] = {
        "wrong_accept_rate": mean_and_sd([run["fixed"]["wrong_accept_rate"] for run in runs]),
        "coverage": mean_and_sd([run["fixed"]["coverage"] for run in runs]),
    }
    checks = [run["by_alpha"][str(H2_ALPHA)]["h2"] for run in runs] if str(H2_ALPHA) in runs[0]["by_alpha"] else []
    if not checks:
        summary["h2"] = f"not tested (alpha {H2_ALPHA} was not among the alphas)"
    elif all(c["supported"] for c in checks):
        summary["h2"] = "supported" + (" (also by the exact upper bound)" if all(c["upper_bound_ok"] for c in checks) else
                                       " (the point estimate meets alpha; the exact upper bound does not)")
    else:
        summary["h2"] = "not supported"
    return summary


def markdown(result: dict) -> str:
    runs, alphas = result["runs"], result["settings"]["alphas"]
    lines = [f"# Gap 2 (H2): {', '.join(result['records'])}", "", f"H2 (alpha = {H2_ALPHA:.0%}, at least "
             f"{MIN_COVERAGE:.0%} answered): **{result['summary']['h2']}**", "",
             "| Run | Alpha | Answered | Coverage | Wrong accepted | Wrong-accept rate [exact 95%] | All-classes threshold |",
             "|---|---|---|---|---|---|---|"]
    for i, run in enumerate(runs, start=1):
        for alpha in alphas:
            test = run["by_alpha"][str(alpha)]["test"]
            pooled = test["pooled"]
            low, high = pooled["exact_interval"]
            threshold = "answer nothing" if test["threshold"] is None else f"{test['threshold']:.3f}"
            lines.append(f"| {i} | {alpha:.0%} | {pooled['answered']} / {test['problems']} | {_pct(pooled['coverage'])} | "
                         f"{pooled['wrong_accepted']} | {_pct(pooled['wrong_accept_rate'])} [{low:.1%}, {high:.1%}] | {threshold} |")
        fixed = run["fixed"]
        lines.append(f"| {i} | fixed {fixed['threshold']} | {fixed['answered']} / {run['problems']} | {_pct(fixed['coverage'])} | "
                     f"{fixed['wrong_accepted']} | {_pct(fixed['wrong_accept_rate'])} | {fixed['threshold']} |")
    if any("interval_width" in run["by_alpha"][str(a)] for run in runs for a in alphas):
        lines += ["", "Width of the pooled exact interval, all problems against the subset:", ""]
        for i, run in enumerate(runs, start=1):
            for alpha in alphas:
                entry = run["by_alpha"][str(alpha)]
                if "interval_width" in entry:
                    w = entry["interval_width"]
                    lines.append(f"- Run {i}, alpha {alpha:.0%}: {w['all']:.3f} ({run['problems']} problems) against "
                                 f"{w['subset']:.3f} ({entry['subset']['problems']} problems)")
    if "b0" in result:
        b0 = result["b0"]
        lines += ["", f"B0 on the same {b0['problems']} problems: answers {b0['answered']} ({_pct(b0['coverage'])}), "
                      f"wrong-accept rate {_pct(b0['wrong_accept_rate'])} ({b0['wrong_accepted']} wrong)."]
    return "\n".join(lines) + "\n"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def write_curve(result: dict, out: Path) -> None:
    with (out / "risk_coverage.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["run", "threshold", "coverage", "wrong_accept_rate"])
        for i, run in enumerate(result["runs"], start=1):
            for point in run["risk_coverage"]:
                writer.writerow([i, point["threshold"], point["coverage"], point["wrong_accept_rate"]])

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(4.8, 3.4))
    for i, run in enumerate(result["runs"], start=1):
        points = run["risk_coverage"]
        axis.plot([p["coverage"] for p in points], [p["wrong_accept_rate"] for p in points], marker=".", label=f"Pipeline, run {i}")
        fixed = run["fixed"]
        if fixed["wrong_accept_rate"] is not None:
            axis.scatter([fixed["coverage"]], [fixed["wrong_accept_rate"]], marker="s", color="black", zorder=3,
                         label="Fixed threshold 0.8" if i == 1 else None)
        pooled = run["by_alpha"].get(str(H2_ALPHA), {}).get("test", {}).get("pooled")
        if pooled and pooled["wrong_accept_rate"] is not None:
            axis.scatter([pooled["coverage"]], [pooled["wrong_accept_rate"]], marker="*", s=90, color="tab:red", zorder=3,
                         label=f"Calibrated, alpha {H2_ALPHA:.0%} (held out)" if i == 1 else None)
    if "b0" in result and result["b0"]["wrong_accept_rate"] is not None:
        axis.scatter([result["b0"]["coverage"]], [result["b0"]["wrong_accept_rate"]], marker="^", color="tab:gray", label="B0")
    axis.axhline(H2_ALPHA, linestyle="--", color="tab:red", linewidth=0.8)
    axis.axvline(MIN_COVERAGE, linestyle=":", color="gray", linewidth=0.8)
    axis.set_xlabel("Coverage (share of problems answered)")
    axis.set_ylabel("Wrong-accept rate")
    axis.set_xlim(0, 1)
    axis.set_ylim(bottom=0)
    axis.legend(fontsize=7)
    figure.tight_layout()
    for suffix in ("pdf", "png"):
        figure.savefig(out / f"risk_coverage.{suffix}", dpi=200)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--records", type=Path, nargs="+", required=True, help="records.jsonl of each pipeline repeat")
    parser.add_argument("--alphas", type=float, nargs="+", default=[0.05, 0.10, 0.20], help="target wrong-accept rates")
    parser.add_argument("--fixed-threshold", type=float, default=0.8, help="fixed threshold to compare with (ablation vi)")
    parser.add_argument("--subset", type=Path, help="sample file of a smaller sample, e.g. samples/canonical_100.json")
    parser.add_argument("--baseline", type=Path, help="records.jsonl of a B1 run on the same problems (B0 = its first attempts)")
    parser.add_argument("--out", type=Path, help="folder for gap2.json, gap2.md and the risk-coverage curve")
    args = parser.parse_args()

    all_records = [load(path) for path in args.records]
    subset = set(json.loads(args.subset.read_text(encoding="utf-8"))) if args.subset else None
    runs = [analyze_run(records, args.alphas, args.fixed_threshold, subset) for records in all_records]
    result = {
        "records": [path.as_posix() for path in args.records],
        "settings": {"alphas": args.alphas, "fixed_threshold": args.fixed_threshold,
                     "subset": args.subset.as_posix() if args.subset else None, "h2_alpha": H2_ALPHA, "min_coverage": MIN_COVERAGE},
        "runs": runs,
        "summary": summarize(runs, args.alphas),
    }
    if args.baseline:
        problem_ids = {r["problem_id"] for records in all_records for r in records if "failed" not in r}
        result["b0"] = b0_reference(load(args.baseline), problem_ids)
    text = markdown(result)
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "gap2.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (args.out / "gap2.md").write_text(text, encoding="utf-8")
        write_curve(result, args.out)


if __name__ == "__main__":
    main()
