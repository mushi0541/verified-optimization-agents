"""E4 Gap 1 (H1): do the label-free signals separate correct from wrong answers? From saved records, no API calls.

    python scripts/analyze_gap1.py --records results/<pipeline repeat 1>/records.jsonl results/<repeat 2>/records.jsonl \
        --baseline results/<B1 run>/records.jsonl --out results/gap1/canonical_200

For each pipeline run (one repeat), the AUROC for separating correct from wrong final answers of:
- feasibility alone (1 for a feasible model, 0 otherwise);
- each signal alone (number coverage, requirement coverage, paraphrase agreement), with feasibility still required;
- the combined score (the mean of all available signals), and the combined score without each signal (ablations
  i to iii, the same score `scripts/rescore.py --signals` gives).
A wrong answer includes a model with no optimum; a feasible model always scores above an infeasible one. Intervals
are bootstrap 95% intervals over problems, resampled in pairs so differences keep their pairing. Problems that failed
(no answer was produced, listed in the run's summary.json) are not in the AUROCs, which compare the system's own
answers, but they count as unanswered in the coverage at the threshold.

H1 is supported for a run when the combined score's AUROC is at least 0.10 above feasibility alone and the interval
of that gain lies above 0, and removing any one signal lowers the AUROC (the interval of each drop lies above 0).
Over the repeats the verdict is "supported" only if it holds in every repeat, "partly" if the gain holds but not
every drop, and "not supported" otherwise. A run with only correct or only wrong answers has no AUROC, so the verdict
is then "not testable".

Also reported at the decision threshold (fixed, or from a calibration file made for these runs): coverage, precision (selective
accuracy) and recall of accepted answers, and, with --baseline, B0 on the same problems (it answers whenever its
first model is optimal, the SIR setting of the base paper). Results are split by group when the problems have one:
original against augmented for the constraint pairs, and easy, moderate and hard wording for the linguistic split,
each group with its own bootstrap intervals.
"""

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optverify.calibration import check_system, load_run, record_system, threshold_from_file  # noqa: E402
from optverify.data import load_split  # noqa: E402
from optverify.grading import is_correct  # noqa: E402
from optverify.rescore import rescore  # noqa: E402
from optverify.verifier import SIGNALS  # noqa: E402
from scripts.analyze_e3 import percentile_interval  # noqa: E402  (one interval rule for every analysis)

TARGET_GAIN = 0.10
GROUP_KEYS = ("constraint_type", "linguistic_complexity")


def score_sets() -> dict[str, tuple[str, ...]]:
    """Name -> enabled signals for every score compared."""
    scores = {"feasibility": ()}
    scores.update({name: (name,) for name in SIGNALS})
    scores["combined"] = SIGNALS
    scores.update({f"combined_without_{name}": tuple(s for s in SIGNALS if s != name) for name in SIGNALS})
    return scores


def auroc(scores: list[float], labels: list[bool]) -> float | None:
    """P(score of a correct answer > score of a wrong one), ties counted half; None without both kinds."""
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    start = 0
    while start < len(order):  # average ranks over ties
        end = start
        while end + 1 < len(order) and scores[order[end + 1]] == scores[order[start]]:
            end += 1
        for position in range(start, end + 1):
            ranks[order[position]] = (start + end) / 2 + 1
        start = end + 1
    rank_sum = sum(rank for rank, label in zip(ranks, labels) if label)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def outcomes(records: list[dict]) -> list[dict]:
    """Per finished problem (failed ones produced no answer): whether the final answer is correct, and every score."""
    rows = []
    for record in records:
        if "failed" in record:
            continue
        row = {"problem_id": record["problem_id"], "problem_class": record["problem_class"]}
        for name, signals in score_sets().items():
            outcome = rescore(record, signals)
            row[name] = outcome["score"]
            row["correct"], row["feasible"] = outcome["correct"], outcome["feasible"]
        rows.append(row)
    return rows


def aurocs(rows: list[dict]) -> dict[str, float | None]:
    labels = [row["correct"] for row in rows]
    return {name: auroc([row[name] for row in rows], labels) for name in score_sets()}


def bootstrap(rows: list[dict], draws: int, rng: random.Random) -> dict[str, list[float] | None]:
    """95% intervals of each AUROC, of the gain over feasibility and of each drop, resampling problems in pairs."""
    names = list(score_sets())
    samples = {name: [] for name in names}
    samples.update({"gain": []}, **{f"drop_{s}": [] for s in SIGNALS})
    for _ in range(draws):
        values = aurocs([rows[rng.randrange(len(rows))] for _ in rows])
        if any(values[name] is None for name in names):
            continue  # a resample with only correct or only wrong answers has no AUROC
        for name in names:
            samples[name].append(values[name])
        samples["gain"].append(values["combined"] - values["feasibility"])
        for signal in SIGNALS:
            samples[f"drop_{signal}"].append(values["combined"] - values[f"combined_without_{signal}"])
    return {name: percentile_interval(values) for name, values in samples.items()}


def at_threshold(rows: list[dict], threshold: float, problems: int | None = None) -> dict:
    """Coverage, precision (selective accuracy) and recall of the answers the combined score accepts. `problems` is
    every problem of the run, failed ones included (they are never answered); by default the finished ones."""
    problems = len(rows) if problems is None else problems
    accepted = [row for row in rows if row["feasible"] and row["combined"] >= threshold]
    correct_accepted = sum(row["correct"] for row in accepted)
    correct_total = sum(row["correct"] for row in rows)
    return {
        "threshold": None if threshold == float("inf") else threshold,
        "problems": problems,
        "accepted": len(accepted),
        "coverage": len(accepted) / problems if problems else 0.0,
        "precision": correct_accepted / len(accepted) if accepted else None,
        "recall": correct_accepted / correct_total if correct_total else None,
        "wrong_accepted": len(accepted) - correct_accepted,
    }


def b0_reference(baseline: list[dict], problem_ids: set[str]) -> dict:
    """B0 (the first attempt of B1 records) on the same problems: it answers whenever its model is optimal. A failed
    problem counts as not answered."""
    rows = [r for r in baseline if r["problem_id"] in problem_ids]
    answered = [r for r in rows if "failed" not in r and r["attempts"][0]["solve"]["status"] == "optimal"]
    correct = sum(is_correct(r["attempts"][0]["solve"]["objective"], r["reference"]) for r in answered)
    return {
        "problems": len(rows),
        "accepted": len(answered),
        "coverage": len(answered) / len(rows) if rows else 0.0,
        "precision": correct / len(answered) if answered else None,
        "accuracy": correct / len(rows) if rows else None,
        "wrong_accepted": len(answered) - correct,
    }


def verdict(values: dict, intervals: dict) -> dict:
    gain = None if values["combined"] is None or values["feasibility"] is None else values["combined"] - values["feasibility"]
    gain_ok = gain is not None and gain >= TARGET_GAIN and bool(intervals["gain"]) and intervals["gain"][0] > 0
    drops_ok = {s: bool(intervals[f"drop_{s}"]) and intervals[f"drop_{s}"][0] > 0 for s in SIGNALS}
    return {"testable": gain is not None, "gain": gain, "gain_ok": gain_ok, "drops_ok": drops_ok,
            "supported": gain_ok and all(drops_ok.values())}


def analyze_run(records: list[dict], threshold: float, draws: int, seed: int, groups: dict[str, str]) -> dict:
    """One repeat; `records` come from load_run, so failed problems are in them as unanswered."""
    rows = outcomes(records)
    values = aurocs(rows)
    rng = random.Random(seed)
    intervals = bootstrap(rows, draws, rng)
    result = {
        "problems": len(rows),
        "failed_problems": len(records) - len(rows),
        "correct": sum(row["correct"] for row in rows),
        "auroc": values,
        "intervals": intervals,
        "verdict": verdict(values, intervals),
        "at_threshold": at_threshold(rows, threshold, problems=len(records)),
    }
    by_group: dict[str, list[dict]] = {}
    for row in rows:
        if row["problem_id"] in groups:
            by_group.setdefault(groups[row["problem_id"]], []).append(row)
    if by_group:
        group_sizes = {name: sum(groups.get(r["problem_id"]) == name for r in records) for name in by_group}
        result["groups"] = {
            name: {"problems": len(members), "failed_problems": group_sizes[name] - len(members),
                   "correct": sum(r["correct"] for r in members), "auroc": aurocs(members),
                   "intervals": bootstrap(members, draws, rng),
                   "at_threshold": at_threshold(members, threshold, problems=group_sizes[name])}
            for name, members in sorted(by_group.items())
        }
    return result


def problem_groups(problem_ids: set[str]) -> dict[str, str]:
    """problem id -> group (constraint type or wording level) for the splits that have one."""
    groups = {}
    for split in sorted({pid.partition("-")[0] for pid in problem_ids}):
        if split not in ("constraint", "linguistic"):
            continue
        for problem in load_split(split):
            if problem.problem_id in problem_ids:
                groups[problem.problem_id] = next(str(problem.meta[k]) for k in GROUP_KEYS if k in problem.meta)
    return groups


def mean_and_sd(values: list[float | None]) -> dict:
    present = [v for v in values if v is not None]
    return {
        "mean": statistics.mean(present) if present else None,
        "sd": statistics.stdev(present) if len(present) > 1 else None,
        "repeats_with_value": len(present),
    }


def summarize(runs: list[dict]) -> dict:
    summary = {
        "auroc": {name: mean_and_sd([run["auroc"][name] for run in runs]) for name in score_sets()},
        "gain": mean_and_sd([run["verdict"]["gain"] for run in runs]),
        "precision": mean_and_sd([run["at_threshold"]["precision"] for run in runs]),
        "recall": mean_and_sd([run["at_threshold"]["recall"] for run in runs]),
        "coverage": mean_and_sd([run["at_threshold"]["coverage"] for run in runs]),
    }
    if not all(run["verdict"]["testable"] for run in runs):
        summary["h1"] = "not testable (a run has only correct or only wrong answers, so it has no AUROC)"
    elif all(run["verdict"]["supported"] for run in runs):
        summary["h1"] = "supported"
    elif all(run["verdict"]["gain_ok"] for run in runs):
        summary["h1"] = "partly supported (the gain holds, but not every signal is needed)"
    else:
        summary["h1"] = "not supported"
    return summary


def markdown(result: dict) -> str:
    runs, summary = result["runs"], result["summary"]
    lines = [f"# Gap 1 (H1): {', '.join(result['records'])}", "", f"H1: **{summary['h1']}**", ""]
    header = "| Score | " + " | ".join(f"Run {i + 1}" for i in range(len(runs))) + " | Mean (sd) |"
    lines += [header, "|---|" + "---|" * (len(runs) + 1)]
    for name in score_sets():
        cells = []
        for run in runs:
            value, interval = run["auroc"][name], run["intervals"].get(name)
            cells.append("n/a" if value is None else f"{value:.3f}" + (f" [{interval[0]:.2f}, {interval[1]:.2f}]" if interval else ""))
        stats = summary["auroc"][name]
        mean = "n/a" if stats["mean"] is None else f"{stats['mean']:.3f}" + (f" ({stats['sd']:.3f})" if stats["sd"] is not None else "")
        lines.append(f"| {name} | " + " | ".join(cells) + f" | {mean} |")
    lines += ["", "| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |",
              "|---|---|---|---|---|---|---|---|"]
    for i, run in enumerate(runs, start=1):
        gain, interval, t = run["verdict"]["gain"], run["intervals"]["gain"], run["at_threshold"]
        drops = ", ".join(f"{s}: {'yes' if ok else 'no'}" for s, ok in run["verdict"]["drops_ok"].items())
        lines.append(
            f"| {i} | {run['problems']} | {run['correct']} | "
            + ("n/a" if gain is None else f"{gain:+.3f}" + (f" [{interval[0]:+.2f}, {interval[1]:+.2f}]" if interval else ""))
            + f" | {drops} | {t['accepted']} | {_pct(t['precision'])} | {_pct(t['recall'])} |"
        )
    if any("groups" in run for run in runs):
        lines += ["", "By group (bootstrap 95% intervals within each group):", "",
                  "| Run | Group | Problems | Correct | Feasibility | Combined [95%] | Gain [95%] | Coverage | Precision |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for i, run in enumerate(runs, start=1):
            for name, group in run.get("groups", {}).items():
                values, intervals, t = group["auroc"], group["intervals"], group["at_threshold"]
                gain = None if values["combined"] is None or values["feasibility"] is None else values["combined"] - values["feasibility"]
                lines.append(
                    f"| {i} | {name} | {t['problems']} | {group['correct']} | {_auroc_cell(values['feasibility'], None)} | "
                    f"{_auroc_cell(values['combined'], intervals['combined'])} | "
                    + ("n/a" if gain is None else f"{gain:+.3f}" + (f" [{intervals['gain'][0]:+.2f}, {intervals['gain'][1]:+.2f}]"
                                                                     if intervals["gain"] else ""))
                    + f" | {_pct(t['coverage'])} | {_pct(t['precision'])} |"
                )
    if "b0" in result:
        b0 = result["b0"]
        if b0["problems"]:
            lines += ["", f"B0 on the same {b0['problems']} problems: answers {b0['accepted']} ({_pct(b0['coverage'])}), "
                          f"precision {_pct(b0['precision'])}, {b0['wrong_accepted']} wrong answers accepted."]
        else:
            lines += ["", "B0: the baseline records share no problems with these runs."]
    return "\n".join(lines) + "\n"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _auroc_cell(value: float | None, interval: list[float] | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}" + (f" [{interval[0]:.2f}, {interval[1]:.2f}]" if interval else "")


def calibrated_threshold(calibration: dict, record_paths: list[Path], all_records: list[list[dict]]) -> float:
    """The threshold of a calibration file, after checking it was made for these runs: the same system and parser
    switch, and every signal on (the combined score here always uses all of them)."""
    for path, records in zip(record_paths, all_records):
        summary = path.parent / "summary.json"
        config = json.loads(summary.read_text(encoding="utf-8"))["config"] if summary.exists() else {}
        try:
            check_system(calibration, record_system(records), SIGNALS, not config.get("no_parser", False))
        except ValueError as error:
            raise SystemExit(f"--calibration does not fit {path}: {error}") from error
    return threshold_from_file(calibration)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--records", type=Path, nargs="+", required=True, help="records.jsonl of each pipeline repeat")
    parser.add_argument("--baseline", type=Path, help="records.jsonl of a B1 run on the same problems (B0 = its first attempts)")
    parser.add_argument("--threshold", type=float, default=0.8, help="decision threshold for precision and recall")
    parser.add_argument("--calibration", type=Path, help="use the threshold of a calibration file instead")
    parser.add_argument("--draws", type=int, default=2000, help="bootstrap resamples")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, help="folder for gap1.json and gap1.md")
    args = parser.parse_args()

    all_records = [load_run(path) for path in args.records]  # failed problems included, as unanswered
    threshold = args.threshold
    if args.calibration:
        calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
        threshold = calibrated_threshold(calibration, args.records, all_records)
    problem_ids = {r["problem_id"] for records in all_records for r in records}
    groups = problem_groups(problem_ids)
    runs = [analyze_run(records, threshold, args.draws, args.seed + i, groups) for i, records in enumerate(all_records)]
    result = {
        "records": [path.as_posix() for path in args.records],
        "settings": {"threshold": None if threshold == float("inf") else threshold, "draws": args.draws, "seed": args.seed,
                     "target_gain": TARGET_GAIN},
        "runs": runs,
        "summary": summarize(runs),
    }
    if args.baseline:
        result["b0"] = b0_reference(load_run(args.baseline), problem_ids)
    text = markdown(result)
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "gap1.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (args.out / "gap1.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
