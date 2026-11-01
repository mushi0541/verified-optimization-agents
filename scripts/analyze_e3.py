"""E3 (Gap 3): the pipeline against the single agent B2 at equal token budgets, from saved records only.

For k = 1, 2, 3 paraphrase runs:
- the pipeline at k is read from k = 3 records by dropping the later paraphrase runs (their tokens are in
  usage_by_step["paraphrase_<j>"]) and rescoring with the first k reworded-run optima;
- the budget level is the pipeline's mean tokens per problem at k, and B2 at that level keeps its first samples
  whose tokens are closest to it (the same rule as in the B2 run).

Reported per system and level: accuracy (with exact 95% interval), wrong-accept rate at equal coverage (50%)
with tied scores broken at random and averaged over 1,000 draws, tokens and calls per problem, and the B2 budget
ratio (it must be within 10% of the pipeline). Paired comparisons: McNemar test on accuracy and bootstrap 95%
intervals of the differences (pipeline minus B2). H3 is supported only if the whole interval of the wrong-accept
difference at k = 3 lies below zero. B0 and B1 are added as reference points when baseline records are given.

Example:
    python scripts/analyze_e3.py --pipeline results/pipeline_.../records.jsonl --b2 results/b2_.../records.jsonl \\
        --baseline results/baseline_..._r1_.../records.jsonl --out results/e3
"""

import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optverify.grading import is_correct  # noqa: E402
from optverify.systems import majority_vote, samples_within_budget  # noqa: E402
from optverify.verifier import combined_score, paraphrase_agreement  # noqa: E402

LEVELS = (1, 2, 3)
BUDGET_TOLERANCE = 0.10


def main() -> None:
    parser = argparse.ArgumentParser(description="E3: pipeline against B2 at equal token budgets (no API calls).")
    parser.add_argument("--pipeline", nargs="+", required=True, help="records.jsonl of pipeline runs with k = 3")
    parser.add_argument("--b2", nargs="+", required=True, help="records.jsonl of B2 runs")
    parser.add_argument("--baseline", nargs="+", help="records.jsonl of B1 runs (B0 is read from the first attempts)")
    parser.add_argument("--coverage", type=float, default=0.5, help="share of all problems answered for the risk comparison")
    parser.add_argument("--draws", type=int, default=1000, help="random tie-breaking draws")
    parser.add_argument("--bootstrap", type=int, default=1000, help="bootstrap resamples")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", help="folder for e3.json and accuracy_cost.csv")
    args = parser.parse_args()

    baseline = load_records(args.baseline) if args.baseline else None
    result = analyze(
        load_records(args.pipeline), load_records(args.b2), baseline, args.coverage, args.draws, args.bootstrap, args.seed
    )
    print(json.dumps(result, indent=2))
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "e3.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        write_curve(result, out_dir / "accuracy_cost.csv")


# ---------- loading and per-level views ----------


def load_records(paths: list[str]) -> dict[str, dict]:
    """Records by problem id; several files (one per member's run) are merged."""
    records = {}
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if "failed" in record:
                continue
            if record["problem_id"] in records:
                raise ValueError(f"{record['problem_id']} appears twice in {paths}")
            records[record["problem_id"]] = record
    return records


def pipeline_at(record: dict, k: int) -> dict:
    """The pipeline's outcome with only its first k paraphrase runs."""
    report = record["verifier"]
    objective = record["attempts"][-1]["solve"]["objective"] if report["feasible"] else None
    others = report["paraphrase_objectives"]
    if report["feasible"] and len(others) < k:
        raise ValueError(f"{record['problem_id']} has {len(others)} paraphrase runs, fewer than k = {k}")
    agreement = paraphrase_agreement(objective, others[:k]) if report["feasible"] else None
    dropped = [f"paraphrase_{j}" for j in range(k + 1, len(others) + 1)]
    return {
        "answer": objective,
        "score": combined_score(
            report["feasible"], report["number_coverage"], agreement, report.get("requirement_coverage")
        ),
        "correct": is_correct(objective, record["reference"]),
        **_usage_without(record, dropped),
    }


def b2_at(record: dict, budget: float) -> dict:
    """B2's outcome with its first samples whose tokens are closest to budget."""
    steps = _steps(record)
    sample_steps = [steps[f"sample_{i}"] for i in range(1, len(record["samples"]) + 1)]
    used = samples_within_budget([step["input_tokens"] + step["output_tokens"] for step in sample_steps], budget)
    answer, agreement = majority_vote([attempts[-1]["solve"]["objective"] for attempts in record["samples"][:used]])
    return {
        "answer": answer,
        "score": agreement,
        "correct": is_correct(answer, record["reference"]),
        "tokens": sum(step["input_tokens"] + step["output_tokens"] for step in sample_steps[:used]),
        "calls": sum(step["calls"] for step in sample_steps[:used]),
        "samples": used,
    }


def baseline_points(record: dict) -> dict[str, dict]:
    """B0 (first attempt, no repair) and B1 (after repairs) from one B1 record."""
    steps = record.get("usage_by_step") or {}
    first = record["attempts"][0]["solve"]["objective"]
    final = record["attempts"][-1]["solve"]["objective"]
    total = record["usage"]
    if "formalize" in steps:
        b0_tokens, b0_calls = steps["formalize"]["input_tokens"] + steps["formalize"]["output_tokens"], steps["formalize"]["calls"]
    elif len(record["attempts"]) == 1:  # records saved before Phase 2: only a single attempt can be read
        b0_tokens, b0_calls = total["input_tokens"] + total["output_tokens"], total["calls"]
    else:
        b0_tokens = b0_calls = None
    return {
        "B0": {"answer": first, "correct": is_correct(first, record["reference"]), "tokens": b0_tokens, "calls": b0_calls},
        "B1": {
            "answer": final,
            "correct": is_correct(final, record["reference"]),
            "tokens": total["input_tokens"] + total["output_tokens"],
            "calls": total["calls"],
        },
    }


def _steps(record: dict) -> dict:
    steps = record.get("usage_by_step")
    if not steps:
        raise ValueError(f"{record['problem_id']} has no usage_by_step; E3 needs records saved in Phase 2")
    return steps


def _usage_without(record: dict, dropped_steps: list[str]) -> dict:
    total = record["usage"]
    tokens, calls = total["input_tokens"] + total["output_tokens"], total["calls"]
    steps = _steps(record) if dropped_steps else {}
    for name in dropped_steps:
        tokens -= steps[name]["input_tokens"] + steps[name]["output_tokens"]
        calls -= steps[name]["calls"]
    return {"tokens": tokens, "calls": calls}


# ---------- statistics ----------


def wrong_accept_at_coverage(outcomes: list[dict], coverage: float, draws: int, rng: random.Random | None) -> dict:
    """Wrong-accept rate when the top `coverage` share of all problems by score is answered.

    Only problems with an answer can be accepted. Problems tied at the cut-off score are picked at random; the
    rate is averaged over `draws` draws from rng. With rng None the exact mean over all tie-breaks is returned
    (the value the draws estimate), which keeps the bootstrap fast.
    """
    target = int(coverage * len(outcomes) + 0.5)
    candidates = sorted((o for o in outcomes if o["answer"] is not None), key=lambda o: -o["score"])
    accepted = min(target, len(candidates))
    if accepted == 0:
        return {"wrong_accept_rate": None, "coverage": 0.0}
    cut = candidates[accepted - 1]["score"]
    above = [o for o in candidates if o["score"] > cut]
    tied_wrong = [not o["correct"] for o in candidates if o["score"] == cut]
    wrong_above = sum(not o["correct"] for o in above)
    picks = accepted - len(above)
    if rng is None:
        wrong = wrong_above + picks * sum(tied_wrong) / len(tied_wrong)
    else:
        wrong = sum(wrong_above + sum(rng.sample(tied_wrong, picks)) for _ in range(draws)) / draws
    return {"wrong_accept_rate": wrong / accepted, "coverage": accepted / len(outcomes)}


def mcnemar_p(first_correct: list[bool], second_correct: list[bool]) -> float:
    """Exact two-sided McNemar test on paired correct / wrong outcomes."""
    only_first = sum(a and not b for a, b in zip(first_correct, second_correct))
    only_second = sum(b and not a for a, b in zip(first_correct, second_correct))
    discordant = only_first + only_second
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, i) for i in range(min(only_first, only_second) + 1)) / 2**discordant
    return min(1.0, 2 * tail)


def clopper_pearson(successes: int, trials: int, level: float = 0.95) -> list[float]:
    """Exact binomial interval."""
    if trials == 0:
        return [0.0, 1.0]
    alpha = 1 - level
    lower = 0.0 if successes == 0 else _bisect(lambda p: _binomial_tail_at_least(successes, trials, p) - alpha / 2)
    upper = 1.0 if successes == trials else _bisect(lambda p: alpha / 2 - _binomial_cdf(successes, trials, p))
    return [lower, upper]


def percentile_interval(values: list[float], level: float = 0.95) -> list[float] | None:
    values = sorted(value for value in values if value is not None)
    if not values:
        return None
    low = values[int(math.floor((1 - level) / 2 * (len(values) - 1)))]
    high = values[int(math.ceil((1 + level) / 2 * (len(values) - 1)))]
    return [low, high]


def _binomial_cdf(successes: int, trials: int, p: float) -> float:
    return sum(_binomial_pmf(i, trials, p) for i in range(successes + 1))


def _binomial_tail_at_least(successes: int, trials: int, p: float) -> float:
    return sum(_binomial_pmf(i, trials, p) for i in range(successes, trials + 1))


def _binomial_pmf(i: int, trials: int, p: float) -> float:
    if p <= 0.0:
        return 1.0 if i == 0 else 0.0
    if p >= 1.0:
        return 1.0 if i == trials else 0.0
    log_comb = math.lgamma(trials + 1) - math.lgamma(i + 1) - math.lgamma(trials - i + 1)
    return math.exp(log_comb + i * math.log(p) + (trials - i) * math.log(1 - p))


def _bisect(increasing, low: float = 0.0, high: float = 1.0) -> float:
    """Root of a function that increases in p."""
    for _ in range(60):
        middle = (low + high) / 2
        if increasing(middle) < 0:
            low = middle
        else:
            high = middle
    return (low + high) / 2


# ---------- the analysis ----------


def analyze(
    pipeline: dict[str, dict],
    b2: dict[str, dict],
    baseline: dict[str, dict] | None = None,
    coverage: float = 0.5,
    draws: int = 1000,
    bootstrap: int = 1000,
    seed: int = 0,
) -> dict:
    ids = sorted(set(pipeline) & set(b2))
    if not ids:
        raise ValueError("the pipeline and B2 records share no problems")
    result = {
        "problems": len(ids),
        "only_in_pipeline": sorted(set(pipeline) - set(b2)),
        "only_in_b2": sorted(set(b2) - set(pipeline)),
        "settings": {"coverage": coverage, "draws": draws, "bootstrap": bootstrap, "seed": seed},
        "levels": [],
    }

    for k in LEVELS:
        pipe = [pipeline_at(pipeline[i], k) for i in ids]
        budget = _mean(o["tokens"] for o in pipe)
        single = [b2_at(b2[i], budget) for i in ids]
        level = {
            "k": k,
            "budget_tokens": budget,
            "pipeline": _summary(pipe, coverage, draws, random.Random(f"{seed}-pipeline-{k}")),
            "b2": _summary(single, coverage, draws, random.Random(f"{seed}-b2-{k}")),
        }
        ratio = level["b2"]["mean_tokens"] / budget if budget else None
        level["b2"]["budget_ratio"] = ratio
        level["b2"]["within_budget_tolerance"] = ratio is not None and abs(ratio - 1) <= BUDGET_TOLERANCE
        level["b2"]["mean_samples"] = _mean(o["samples"] for o in single)
        level["paired"] = _paired(pipe, single, coverage, bootstrap, random.Random(f"{seed}-bootstrap-{k}"))
        result["levels"].append(level)

    top = result["levels"][-1]["paired"]["wrong_accept_difference_ci"]
    result["h3"] = {
        "k": LEVELS[-1],
        "wrong_accept_difference_ci": top,
        "supported": top is not None and top[1] < 0,
    }
    if baseline:
        result["reference_points"] = _reference_points(baseline)
    return result


def _summary(outcomes: list[dict], coverage: float, draws: int, rng: random.Random) -> dict:
    correct = sum(o["correct"] for o in outcomes)
    risk = wrong_accept_at_coverage(outcomes, coverage, draws, rng)
    return {
        "accuracy": correct / len(outcomes),
        "accuracy_ci": clopper_pearson(correct, len(outcomes)),
        "wrong_accept_rate": risk["wrong_accept_rate"],
        "coverage": risk["coverage"],
        "mean_tokens": _mean(o["tokens"] for o in outcomes),
        "mean_calls": _mean(o["calls"] for o in outcomes),
    }


def _paired(pipe: list[dict], single: list[dict], coverage: float, bootstrap: int, rng: random.Random) -> dict:
    """Pipeline minus B2, resampling problems with replacement and keeping the pairs together."""
    accuracy_differences, risk_differences = [], []
    for _ in range(bootstrap):
        picks = [rng.randrange(len(pipe)) for _ in pipe]
        pipe_sample, single_sample = [pipe[i] for i in picks], [single[i] for i in picks]
        accuracy_differences.append(_mean(o["correct"] for o in pipe_sample) - _mean(o["correct"] for o in single_sample))
        pipe_risk = wrong_accept_at_coverage(pipe_sample, coverage, 0, None)["wrong_accept_rate"]
        single_risk = wrong_accept_at_coverage(single_sample, coverage, 0, None)["wrong_accept_rate"]
        risk_differences.append(None if pipe_risk is None or single_risk is None else pipe_risk - single_risk)
    return {
        "mcnemar_p": mcnemar_p([o["correct"] for o in pipe], [o["correct"] for o in single]),
        "accuracy_difference_ci": percentile_interval(accuracy_differences),
        "wrong_accept_difference_ci": percentile_interval(risk_differences),
    }


def _reference_points(baseline: dict[str, dict]) -> dict:
    points = {"B0": [], "B1": []}
    for record in baseline.values():
        for name, outcome in baseline_points(record).items():
            points[name].append(outcome)
    summary = {}
    for name, outcomes in points.items():
        answered = [o for o in outcomes if o["answer"] is not None]
        correct = sum(o["correct"] for o in outcomes)
        tokens = [o["tokens"] for o in outcomes]
        summary[name] = {
            "problems": len(outcomes),
            "accuracy": correct / len(outcomes),
            "accuracy_ci": clopper_pearson(correct, len(outcomes)),
            "coverage": len(answered) / len(outcomes),  # never abstains: answers whenever the model is optimal
            "wrong_accept_rate": _mean(not o["correct"] for o in answered) if answered else None,
            "mean_tokens": _mean(tokens) if None not in tokens else None,
            "mean_calls": _mean(o["calls"] for o in outcomes) if None not in tokens else None,
        }
    return summary


def write_curve(result: dict, path: Path) -> None:
    """Accuracy-cost points (mean tokens per problem against accuracy) for plotting."""
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["system", "k", "mean_tokens", "mean_calls", "accuracy", "wrong_accept_rate_at_coverage"])
        for name, point in result.get("reference_points", {}).items():
            writer.writerow([name, "", point["mean_tokens"], point["mean_calls"], point["accuracy"], ""])
        for level in result["levels"]:
            for name in ("pipeline", "b2"):
                point = level[name]
                writer.writerow(
                    [name, level["k"], point["mean_tokens"], point["mean_calls"], point["accuracy"], point["wrong_accept_rate"]]
                )


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


if __name__ == "__main__":
    main()
