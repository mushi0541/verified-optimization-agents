"""Exploratory: does the verifier score and B2's vote agreement catch different mistakes? (saved records only)

H3 was not supported (devlog 15): at an equal token budget, the pipeline's wrong-accept rate is not lower than B2's.
This asks a question that was not pre-registered, so its result is a lead for a new test, not a finding:
if part of the budget goes to the pipeline and the rest to B2 samples, is the combination better than either?

Systems, on the problems both runs share:
- "pipeline k=3": the pipeline as run (its mean tokens per problem is the budget);
- "B2": B2 held to the same budget (as in scripts/analyze_e3.py);
- "pipeline k=j + B2": the pipeline with its first j paraphrase runs, plus B2's first samples for the rest of the
  budget. The answer is the pipeline's; the score is the mean of the pipeline's score and the share of those B2
  samples that reach the same optimum. The pipeline abstains (no answer) when it has no feasible model;
- "ceiling": the full pipeline plus all of B2's samples, at about twice the budget, to show how much the two signals
  can add at most.

For each system: accuracy, AUROC of the score for correctness (answered problems), and the wrong-accept rate when the
top 50, 70, 80 and 90% of problems by score are answered. Each combination is paired with B2 and with the pipeline
(bootstrap 95% intervals of the difference in wrong-accept rate, combination minus the other).

    python scripts/explore_combination.py --pipeline results/pipeline_.../records.jsonl \\
        --b2 results/b2_.../records.jsonl --out results/exploratory/combination
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from optverify.grading import same_optimum  # noqa: E402
from optverify.systems import samples_within_budget  # noqa: E402
from scripts.analyze_e3 import _steps, b2_at, load_records, percentile_interval, pipeline_at  # noqa: E402
from scripts.analyze_e3 import wrong_accept_at_coverage  # noqa: E402
from scripts.analyze_gap1 import auroc  # noqa: E402

COVERAGES = (0.5, 0.7, 0.8, 0.9)


def b2_samples(record: dict, budget: float | None) -> tuple[list[float | None], int]:
    """The optima of B2's first samples whose tokens are closest to budget (all samples when budget is None)."""
    steps = _steps(record)
    sample_tokens = [steps[f"sample_{i}"]["input_tokens"] + steps[f"sample_{i}"]["output_tokens"]
                     for i in range(1, len(record["samples"]) + 1)]
    used = len(sample_tokens) if budget is None else samples_within_budget(sample_tokens, budget)
    return [attempts[-1]["solve"]["objective"] for attempts in record["samples"][:used]], sum(sample_tokens[:used])


def combined(pipeline_record: dict, b2_record: dict, k: int, b2_budget: float | None) -> dict:
    """The pipeline's answer, scored by its own score and by how many B2 samples agree with it."""
    pipe = pipeline_at(pipeline_record, k)
    optima, tokens = b2_samples(b2_record, b2_budget)
    agreement = sum(same_optimum(pipe["answer"], o) for o in optima) / len(optima) if pipe["answer"] is not None else 0.0
    return {"answer": pipe["answer"], "score": (pipe["score"] + agreement) / 2, "correct": pipe["correct"],
            "tokens": pipe["tokens"] + tokens}


def summary(outcomes: list[dict]) -> dict:
    answered = [o for o in outcomes if o["answer"] is not None]
    return {
        "accuracy": sum(o["correct"] for o in outcomes) / len(outcomes),
        "auroc": auroc([o["score"] for o in answered], [o["correct"] for o in answered]),
        "mean_tokens": sum(o["tokens"] for o in outcomes) / len(outcomes),
        "wrong_accept_rate": {f"{c:g}": wrong_accept_at_coverage(outcomes, c, 0, None)["wrong_accept_rate"]
                              for c in COVERAGES},
    }


def paired_risk(first: list[dict], second: list[dict], bootstrap: int, rng: random.Random) -> dict:
    """First minus second wrong-accept rate at each coverage, resampling problems with the pairs kept together."""
    differences = {c: [] for c in COVERAGES}
    for _ in range(bootstrap):
        picks = [rng.randrange(len(first)) for _ in first]
        for c in COVERAGES:
            a = wrong_accept_at_coverage([first[i] for i in picks], c, 0, None)["wrong_accept_rate"]
            b = wrong_accept_at_coverage([second[i] for i in picks], c, 0, None)["wrong_accept_rate"]
            differences[c].append(None if a is None or b is None else a - b)
    return {f"{c:g}": percentile_interval(values) for c, values in differences.items()}


def explore(pipeline: dict[str, dict], b2: dict[str, dict], skip_classes: tuple[str, ...] = (),
            bootstrap: int = 1000, seed: int = 0) -> dict:
    ids = sorted(i for i in set(pipeline) & set(b2) if pipeline[i]["problem_class"] not in skip_classes)
    full = [pipeline_at(pipeline[i], 3) for i in ids]
    budget = sum(o["tokens"] for o in full) / len(full)
    systems = {"pipeline k=3": full, "B2": [b2_at(b2[i], budget) for i in ids]}
    for k in (1, 2):
        rest = budget - sum(pipeline_at(pipeline[i], k)["tokens"] for i in ids) / len(ids)
        systems[f"pipeline k={k} + B2"] = [combined(pipeline[i], b2[i], k, rest) for i in ids]
    systems["ceiling: pipeline k=3 + all of B2"] = [combined(pipeline[i], b2[i], 3, None) for i in ids]
    result = {"problems": len(ids), "skipped_classes": list(skip_classes), "budget_tokens": budget,
              "systems": {name: summary(outcomes) for name, outcomes in systems.items()}, "paired": {}}
    for name in [n for n in systems if "+" in n]:
        for other in ("B2", "pipeline k=3"):
            rng = random.Random(f"{seed}-{name}-{other}")
            result["paired"][f"{name} minus {other}"] = paired_risk(systems[name], systems[other], bootstrap, rng)
    return result


def markdown(result: dict) -> str:
    def rate(value):
        return "--" if value is None else f"{100 * value:.1f}%"

    lines = [f"# Exploratory: the pipeline combined with B2 ({result['problems']} problems"
             + (f", without {', '.join(result['skipped_classes'])})" if result["skipped_classes"] else ")"), "",
             f"Budget: {result['budget_tokens']:,.0f} tokens per problem (the pipeline at k = 3). Not pre-registered.", "",
             "| System | Tokens | Accuracy | AUROC | " + " | ".join(f"WAR at {100 * c:g}%" for c in COVERAGES) + " |",
             "|---|---|---|---|" + "---|" * len(COVERAGES)]
    for name, s in result["systems"].items():
        lines.append(f"| {name} | {s['mean_tokens']:,.0f} | {100 * s['accuracy']:.1f}% | "
                     + ("--" if s["auroc"] is None else f"{s['auroc']:.3f}") + " | "
                     + " | ".join(rate(s["wrong_accept_rate"][f"{c:g}"]) for c in COVERAGES) + " |")
    lines += ["", "Paired 95% intervals of the wrong-accept difference (points):", "",
              "| Comparison | " + " | ".join(f"at {100 * c:g}%" for c in COVERAGES) + " |",
              "|---|" + "---|" * len(COVERAGES)]
    for name, cis in result["paired"].items():
        lines.append(f"| {name} | " + " | ".join(
            "--" if ci is None else f"[{100 * ci[0]:+.1f}, {100 * ci[1]:+.1f}]" for ci in cis.values()) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pipeline", nargs="+", required=True)
    parser.add_argument("--b2", nargs="+", required=True)
    parser.add_argument("--skip-class", nargs="*", default=[])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = explore(load_records(args.pipeline), load_records(args.b2), tuple(args.skip_class))
    result["records"] = {"pipeline": args.pipeline, "b2": args.b2}
    text = markdown(result)
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "combination.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (args.out / "combination.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
