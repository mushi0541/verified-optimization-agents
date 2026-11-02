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
50% of all problems are answered. Failed problems (from each run's summary.json) count as problems that were not
answered. The one-sided 95% exact upper bound, the same bound the calibration uses, is reported next to it; the
interval in the table is the two-sided 95% exact interval. Over the repeats the verdict is "supported" only if it holds
in every repeat.

The risk-coverage curve (wrong-accept rate against coverage as the threshold moves over every score) is written to
risk_coverage.csv and drawn to risk_coverage.pdf and .png, with the calibrated and fixed thresholds marked.

Two extra analyses, reported next to H2 and never in place of it:
- --alpha-scan: the same leave-one-class-out test for every alpha from 5% to 30% in steps of 1%, and the smallest
  alpha that meets H2's rule (point rate at most alpha, at least 50% answered) and the smallest one whose one-sided
  exact bound is also at most alpha. This shows which error rate the data can support (alpha_scan.csv and .png).
- --shift: the shift test (#36). Each repeat's threshold, calibrated on all of its classes, is applied unchanged to a
  run on another benchmark (OpsOR-Bench), and the wrong-accept rate and coverage are reported per family.
- --exclude-classes: the same analysis without some problem classes, for the sensitivity analysis the reference
  check (#40) asks for when a class's references are wrong. It is always reported next to the full result.
- Combined calibration data: one repeat can be several runs joined with "+", for example the canonical,
  constraint-pair, linguistic and OpsOR runs of one repeat. Classes with the same name are held out together, so the
  test still never calibrates on the class it tests.
"""

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optverify.calibration import (  # noqa: E402
    fixed_threshold,
    leave_one_class_out,
    load_run,
    only_sample,
    scored_answers,
    upper_bound,
)
from optverify.grading import is_correct  # noqa: E402

H2_ALPHA = 0.10
MIN_COVERAGE = 0.5


def alpha_key(alpha: float) -> str:
    """The key of an alpha in the results, e.g. 0.1 -> "0.1"."""
    return f"{alpha:g}"


SCAN_ALPHAS = [round(0.05 + 0.01 * i, 2) for i in range(26)]  # 5% to 30%


def load_repeat(spec: str) -> list[dict]:
    """The records of one repeat: one records.jsonl, or several joined with "+" (combined calibration data)."""
    records = [record for part in spec.split("+") for record in load_run(Path(part))]
    ids = [r["problem_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"{spec}: a problem appears in more than one of the joined runs")
    return records


def alpha_scan(records: list[dict], alphas: list[float] = SCAN_ALPHAS) -> dict:
    """The leave-one-class-out test at every alpha, and the smallest alpha the data supports."""
    points = []
    for alpha in alphas:
        test = leave_one_class_out(records, alpha)
        check = h2_check(test)
        points.append({"alpha": alpha, "coverage": test["pooled"]["coverage"],
                       "wrong_accept_rate": test["pooled"]["wrong_accept_rate"], **check})
    return {
        "points": points,
        "smallest_alpha_meeting_h2_rule": next((p["alpha"] for p in points if p["supported"]), None),
        "smallest_alpha_meeting_the_bound_too": next((p["alpha"] for p in points if p["supported"] and p["upper_bound_ok"]), None),
    }


def shift_test(records: list[dict], shift_records: list[dict], alphas: list[float], fixed: float) -> dict:
    """Apply the thresholds calibrated on every class of `records` to another benchmark's records, per family."""
    families = sorted({r["problem_class"] for r in shift_records})
    result = {"problems": len(shift_records), "families": families, "by_alpha": {}}
    settings = [(alpha_key(alpha), leave_one_class_out(records, alpha)["threshold"]) for alpha in alphas] + [("fixed", fixed)]
    for key, threshold in settings:
        rows = {}
        for family in families + ["all"]:
            members = [r for r in shift_records if family == "all" or r["problem_class"] == family]
            accepted = [] if threshold is None else [ok for score, ok in scored_answers(members) if score >= threshold]
            rows[family] = {"problems": len(members), "answered": len(accepted), "wrong_accepted": accepted.count(False),
                            "coverage": len(accepted) / len(members) if members else 0.0,
                            "wrong_accept_rate": accepted.count(False) / len(accepted) if accepted else None}
        result["by_alpha"][key] = {"threshold": threshold, "families": rows}
    return result


def h2_alpha(alphas: list[float]) -> float | None:
    """The alpha among the given ones that H2 is tested at, compared as numbers, not as text."""
    return next((alpha for alpha in alphas if math.isclose(alpha, H2_ALPHA)), None)


def risk_coverage(records: list[dict]) -> list[dict]:
    """Coverage (over every problem, failed ones included) and wrong-accept rate for every threshold, strict to lenient."""
    scored = scored_answers([r for r in records if "failed" not in r])
    points = []
    for threshold in sorted({score for score, _ in scored}, reverse=True):
        accepted = [correct for score, correct in scored if score >= threshold]
        points.append({
            "threshold": threshold,
            "coverage": len(accepted) / len(records),
            "wrong_accept_rate": accepted.count(False) / len(accepted),
        })
    return points


def b0_reference(baseline: list[dict], problem_ids: set[str]) -> dict:
    """B0 (the first attempt of B1 records) on the same problems; it answers whenever its model is optimal. A failed
    problem counts as not answered."""
    rows = [r for r in baseline if r["problem_id"] in problem_ids]
    answered = [r for r in rows if "failed" not in r and r["attempts"][0]["solve"]["status"] == "optimal"]
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
    bound = upper_bound(pooled["wrong_accepted"], pooled["answered"]) if pooled["answered"] else None
    return {
        "rate_ok": rate is not None and rate <= test["alpha"],
        "coverage_ok": pooled["coverage"] >= MIN_COVERAGE,
        "one_sided_upper_bound": bound,
        "upper_bound_ok": bound is not None and bound <= test["alpha"],
        "supported": rate is not None and rate <= test["alpha"] and pooled["coverage"] >= MIN_COVERAGE,
    }


def analyze_run(records: list[dict], alphas: list[float], fixed: float, subset: set[str] | None, scan: bool = False) -> dict:
    if subset:
        found = subset & {r["problem_id"] for r in records}
        if found != subset:
            raise SystemExit(f"the records hold {len(found)} of the {len(subset)} --subset problems; use the subset's own runs")
    result = {
        "problems": len(records),
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
        result["by_alpha"][alpha_key(alpha)] = entry
    if scan:
        result["alpha_scan"] = alpha_scan(records)
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
        entries = [run["by_alpha"][alpha_key(alpha)] for run in runs]
        summary["by_alpha"][alpha_key(alpha)] = {
            "wrong_accept_rate": mean_and_sd([e["test"]["pooled"]["wrong_accept_rate"] for e in entries]),
            "coverage": mean_and_sd([e["test"]["pooled"]["coverage"] for e in entries]),
            "one_sided_upper_bound": mean_and_sd([e["h2"]["one_sided_upper_bound"] for e in entries]),
        }
    summary["fixed"] = {
        "wrong_accept_rate": mean_and_sd([run["fixed"]["wrong_accept_rate"] for run in runs]),
        "coverage": mean_and_sd([run["fixed"]["coverage"] for run in runs]),
    }
    tested = h2_alpha(alphas)
    checks = [run["by_alpha"][alpha_key(tested)]["h2"] for run in runs] if tested is not None else []
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
    excluded = result["settings"].get("excluded_classes")
    sample = result["settings"].get("sample")
    lines = [f"# Gap 2 (H2): {', '.join(result['records'])}", "",
             *([f"**Only the problems of `{sample}`** (`--sample`), in every repeat.", ""] if sample else []),
             *([f"**Sensitivity analysis without {', '.join(excluded)}.** Not the H2 result itself; report it next to the full one.", ""]
               if excluded else []), f"H2 (alpha = {H2_ALPHA:.0%}, at least "
             f"{MIN_COVERAGE:.0%} answered): **{result['summary']['h2']}**", "",
             "| Run | Alpha | Answered | Coverage | Wrong accepted | Wrong-accept rate [exact 95%] | All-classes threshold |",
             "|---|---|---|---|---|---|---|"]
    for i, run in enumerate(runs, start=1):
        for alpha in alphas:
            test = run["by_alpha"][alpha_key(alpha)]["test"]
            pooled = test["pooled"]
            low, high = pooled["exact_interval"]
            threshold = "answer nothing" if test["threshold"] is None else f"{test['threshold']:.3f}"
            lines.append(f"| {i} | {alpha:.0%} | {pooled['answered']} / {test['problems']} | {_pct(pooled['coverage'])} | "
                         f"{pooled['wrong_accepted']} | {_pct(pooled['wrong_accept_rate'])} [{low:.1%}, {high:.1%}] | {threshold} |")
        fixed = run["fixed"]
        lines.append(f"| {i} | fixed {fixed['threshold']} | {fixed['answered']} / {run['problems']} | {_pct(fixed['coverage'])} | "
                     f"{fixed['wrong_accepted']} | {_pct(fixed['wrong_accept_rate'])} | {fixed['threshold']} |")
    if any("interval_width" in run["by_alpha"][alpha_key(a)] for run in runs for a in alphas):
        lines += ["", "Width of the pooled exact interval, all problems against the subset:", ""]
        for i, run in enumerate(runs, start=1):
            for alpha in alphas:
                entry = run["by_alpha"][alpha_key(alpha)]
                if "interval_width" in entry:
                    w = entry["interval_width"]
                    lines.append(f"- Run {i}, alpha {alpha:.0%}: {w['all']:.3f} ({run['problems']} problems) against "
                                 f"{w['subset']:.3f} ({entry['subset']['problems']} problems)")
    if any("alpha_scan" in run for run in runs):
        lines += ["", "Alpha scan (an extra analysis, not H2 itself): the smallest alpha the data supports.", "",
                  "| Run | Smallest alpha meeting H2's rule | ... and its one-sided bound | Coverage there |", "|---|---|---|---|"]
        for i, run in enumerate(runs, start=1):
            scan = run.get("alpha_scan")
            if scan:
                rule, bound = scan["smallest_alpha_meeting_h2_rule"], scan["smallest_alpha_meeting_the_bound_too"]
                coverage = next((p["coverage"] for p in scan["points"] if p["alpha"] == rule), None)
                lines.append(f"| {i} | {_pct(rule) if rule is not None else 'none up to 30%'} | "
                             f"{_pct(bound) if bound is not None else 'none up to 30%'} | {_pct(coverage)} |")
    for i, shift in enumerate(result.get("shift", []), start=1):
        classes = f"every class of this run except {', '.join(excluded)}" if excluded else "every class of this run"
        lines += ["", f"Shift test, run {i}: thresholds calibrated on {classes}, applied to "
                      f"{result['settings']['shift']} ({shift['problems']} problems).", "",
                  "| Setting | Threshold | " + " | ".join(shift["families"]) + " | All |",
                  "|---|---|" + "---|" * (len(shift["families"]) + 1)]
        for key, entry in shift["by_alpha"].items():
            label = f"alpha {float(key):.0%}" if key != "fixed" else "fixed"
            threshold = "answer nothing" if entry["threshold"] is None else f"{entry['threshold']:.3f}"
            cells = [f"{c['answered']}/{c['problems']} answered, {_pct(c['wrong_accept_rate'])} wrong"
                     for c in (entry["families"][f] for f in shift["families"] + ["all"])]
            lines.append(f"| {label} | {threshold} | " + " | ".join(cells) + " |")
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
                         label=f"Fixed threshold {fixed['threshold']:g}" if i == 1 else None)
        tested = h2_alpha(result["settings"]["alphas"])
        pooled = run["by_alpha"][alpha_key(tested)]["test"]["pooled"] if tested is not None else None
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


def write_scan(result: dict, out: Path) -> None:
    runs = [(i, run["alpha_scan"]) for i, run in enumerate(result["runs"], start=1) if "alpha_scan" in run]
    if not runs:
        return
    with (out / "alpha_scan.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["run", "alpha", "coverage", "wrong_accept_rate", "one_sided_upper_bound", "meets_h2_rule"])
        for i, scan in runs:
            for p in scan["points"]:
                writer.writerow([i, p["alpha"], p["coverage"], p["wrong_accept_rate"], p["one_sided_upper_bound"], p["supported"]])

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(4.8, 3.4))
    for i, scan in runs:
        alphas = [p["alpha"] for p in scan["points"]]
        axis.plot(alphas, [p["coverage"] for p in scan["points"]], marker=".", label=f"Coverage, run {i}")
        axis.plot(alphas, [p["wrong_accept_rate"] if p["wrong_accept_rate"] is not None else float("nan") for p in scan["points"]],
                  linestyle="--", label=f"Held-out wrong-accept rate, run {i}")
    axis.plot([0, 0.3], [0, 0.3], color="gray", linewidth=0.8, label="rate = alpha")
    axis.axhline(MIN_COVERAGE, linestyle=":", color="gray", linewidth=0.8)
    axis.set_xlabel("Target alpha")
    axis.set_ylabel("Share")
    axis.set_xlim(0.05, 0.30)
    axis.set_ylim(0, 1)
    axis.legend(fontsize=6)
    figure.tight_layout()
    for suffix in ("pdf", "png"):
        figure.savefig(out / f"alpha_scan.{suffix}", dpi=200)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--records", nargs="+", required=True,
                        help='records.jsonl of each pipeline repeat; join several runs of one repeat with "+"')
    parser.add_argument("--alphas", type=float, nargs="+", default=[0.05, 0.10, 0.20], help="target wrong-accept rates")
    parser.add_argument("--fixed-threshold", type=float, default=0.8, help="fixed threshold to compare with (ablation vi)")
    parser.add_argument("--subset", type=Path, help="sample file of a smaller sample, e.g. samples/canonical_100.json")
    parser.add_argument("--baseline", type=Path, help="records.jsonl of a B1 run on the same problems (B0 = its first attempts)")
    parser.add_argument("--out", type=Path, help="folder for gap2.json, gap2.md and the risk-coverage curve")
    parser.add_argument("--alpha-scan", action="store_true", help="also scan alpha from 5%% to 30%% (an extra analysis)")
    parser.add_argument("--exclude-classes", nargs="+", default=[], help="sensitivity analysis without these classes")
    parser.add_argument("--shift", help="records.jsonl of a run on another benchmark (OpsOR-Bench) for the shift test")
    parser.add_argument("--sample", type=Path, help="analyze only the problems of this sample file, in every repeat")
    args = parser.parse_args()

    all_records = [load_repeat(spec) for spec in args.records]  # failed problems included, as unanswered
    if args.sample:
        all_records = [only_sample(records, args.sample) for records in all_records]
    if args.exclude_classes:
        all_records = [[r for r in records if r["problem_class"] not in args.exclude_classes] for records in all_records]
    subset = set(json.loads(args.subset.read_text(encoding="utf-8"))) if args.subset else None
    runs = [analyze_run(records, args.alphas, args.fixed_threshold, subset, args.alpha_scan) for records in all_records]
    result = {
        "records": [spec.replace("\\", "/") for spec in args.records],
        "settings": {"alphas": args.alphas, "fixed_threshold": args.fixed_threshold,
                     "subset": args.subset.as_posix() if args.subset else None, "h2_alpha": H2_ALPHA, "min_coverage": MIN_COVERAGE,
                     "excluded_classes": args.exclude_classes, "sample": args.sample.as_posix() if args.sample else None,
                     "shift": args.shift.replace("\\", "/") if args.shift else None},
        "runs": runs,
        "summary": summarize(runs, args.alphas),
    }
    if args.shift:
        shift_records = load_run(Path(args.shift))
        result["shift"] = [shift_test(records, shift_records, args.alphas, args.fixed_threshold) for records in all_records]
    if args.baseline:
        problem_ids = {r["problem_id"] for records in all_records for r in records}
        baseline = load_run(args.baseline)
        result["b0"] = b0_reference(only_sample(baseline, args.sample) if args.sample else baseline, problem_ids)
    text = markdown(result)
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "gap2.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (args.out / "gap2.md").write_text(text, encoding="utf-8")
        write_curve(result, args.out)
        write_scan(result, args.out)


if __name__ == "__main__":
    main()
