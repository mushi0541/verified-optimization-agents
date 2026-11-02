"""#56: compare two pipeline runs that differ only in the paraphrase model. From saved records, no API calls.

    python scripts/compare_paraphrasers.py --same results/<run>/records.jsonl --other results/<run>/records.jsonl \
        --out results/paraphraser/dev_93

Each reworded question is solved by the main model in both runs, so only the source of the rewording changes. The
main model's own answer also differs between runs (it is sampled again), so the paraphrase signals are compared on
the problems where both runs gave the same final answer. There, a wrong answer that one run's rewordings all agree
on is a misreading that rewording did not catch; one that the other run's rewordings break is caught by changing the
paraphrase model. Also reported per run: the paraphrase-agreement AUROC, and the false alarms (correct answers
below the threshold) and tokens per problem.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from optverify.calibration import load_run  # noqa: E402
from optverify.grading import same_optimum  # noqa: E402
from scripts.analyze_gap1 import aurocs, outcomes  # noqa: E402


def run_summary(records: list[dict], threshold: float) -> dict:
    finished = [r for r in records if "failed" not in r]
    rows = outcomes(records)
    correct = [r for r in finished if r["correct"]]
    tokens = [r["usage"]["input_tokens"] + r["usage"]["output_tokens"] for r in finished]
    return {"problems": len(records), "finished": len(finished), "correct": len(correct),
            "paraphrase_auroc": aurocs(rows)["paraphrase"], "combined_auroc": aurocs(rows)["combined"],
            "false_alarms": sum(r["verifier"]["score"] < threshold for r in correct),
            "mean_tokens": sum(tokens) / len(tokens) if tokens else 0.0}


def full_agreement(record: dict) -> bool:
    return record["verifier"].get("paraphrase_agreement") == 1


def shared_answers(same: list[dict], other: list[dict]) -> dict:
    """Problems where both runs gave the same feasible final answer, and how each run's rewordings judged it."""
    by_id = {r["problem_id"]: r for r in other if "failed" not in r}
    shared = []
    for a in same:
        b = by_id.get(a["problem_id"])
        if "failed" in a or b is None or not (a["verifier"]["feasible"] and b["verifier"]["feasible"]):
            continue
        if same_optimum(a["predicted"], b["predicted"]):
            shared.append((a, b))
    wrong = [(a, b) for a, b in shared if not a["correct"]]
    right = [(a, b) for a, b in shared if a["correct"]]
    cases = [{"problem_id": a["problem_id"], "problem_class": a["problem_class"],
              "agreement_same": a["verifier"]["paraphrase_agreement"],
              "agreement_other": b["verifier"]["paraphrase_agreement"]} for a, b in wrong]
    return {"shared": len(shared), "wrong": len(wrong),
            "wrong_full_agreement_same": sum(full_agreement(a) for a, _ in wrong),
            "wrong_full_agreement_other": sum(full_agreement(b) for _, b in wrong),
            "caught_only_by_other": [c["problem_id"] for (a, b), c in zip(wrong, cases) if full_agreement(a) and not full_agreement(b)],
            "caught_only_by_same": [c["problem_id"] for (a, b), c in zip(wrong, cases) if full_agreement(b) and not full_agreement(a)],
            "correct": len(right),
            "correct_full_agreement_same": sum(full_agreement(a) for a, _ in right),
            "correct_full_agreement_other": sum(full_agreement(b) for _, b in right),
            "wrong_cases": cases}


def markdown(result: dict) -> str:
    same, other, shared = result["same"], result["other"], result["shared"]
    lines = [f"# Paraphrase model comparison (#56)", "",
             f"- Same model as the formalizer: `{result['records']['same']}`",
             f"- Other paraphrase model: `{result['records']['other']}`", "",
             "| Paraphraser | Correct | Paraphrase AUROC | Combined AUROC | False alarms | Tokens per problem |",
             "|---|---|---|---|---|---|"]
    for name, run in (("same model", same), ("other model", other)):
        lines.append(f"| {name} | {run['correct']}/{run['problems']} | {run['paraphrase_auroc']:.3f} | "
                     f"{run['combined_auroc']:.3f} | {run['false_alarms']} | {run['mean_tokens']:.0f} |")
    lines += ["", f"On the {shared['shared']} problems where both runs gave the same feasible answer "
                  f"({shared['wrong']} wrong, {shared['correct']} correct):", "",
              f"- Wrong answers all rewordings agree on: {shared['wrong_full_agreement_same']} with the same model, "
              f"{shared['wrong_full_agreement_other']} with the other model.",
              f"- Caught only by the other model: {', '.join(shared['caught_only_by_other']) or 'none'}.",
              f"- Caught only by the same model: {', '.join(shared['caught_only_by_same']) or 'none'}.",
              f"- Correct answers all rewordings agree on: {shared['correct_full_agreement_same']} with the same "
              f"model, {shared['correct_full_agreement_other']} with the other model.", "",
              "| Problem | Class | Agreement, same model | Agreement, other model |", "|---|---|---|---|"]
    lines += [f"| {c['problem_id']} | {c['problem_class']} | {c['agreement_same']:.3f} | {c['agreement_other']:.3f} |"
              for c in shared["wrong_cases"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--same", type=Path, required=True, help="records.jsonl with the main model as paraphraser")
    parser.add_argument("--other", type=Path, required=True, help="records.jsonl with another paraphrase model")
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--out", type=Path, help="folder for paraphraser.json and paraphraser.md")
    args = parser.parse_args()
    same, other = load_run(args.same), load_run(args.other)
    result = {"records": {"same": args.same.as_posix(), "other": args.other.as_posix()}, "threshold": args.threshold,
              "same": run_summary(same, args.threshold), "other": run_summary(other, args.threshold),
              "shared": shared_answers(same, other)}
    text = markdown(result)
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "paraphraser.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (args.out / "paraphraser.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
