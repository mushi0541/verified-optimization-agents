"""Compare two pipeline runs on the same problems, per class, paired (no API calls).

    python scripts/compare_runs.py --first results/<v1 run>/records.jsonl --second results/<v2 run>/records.jsonl \\
        --labels v1 v2 --out results/prompts_v2/<sample>

For the problems both runs finished, per class and overall: correct answers, problems with no feasible model, answers
accepted at the threshold, wrong answers among them, and tokens per problem. The paired test is the exact two-sided
McNemar test on correctness (scripts/analyze_e3.py), with the counts it uses (correct only in the first run, only in
the second). Written for the v2 prompts (#95), so v1 and v2 are compared on the same problems.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from optverify.calibration import load_run  # noqa: E402
from scripts.analyze_e3 import mcnemar_p  # noqa: E402


def _stats(records: list[dict], threshold: float) -> dict:
    tokens = [r["usage"]["input_tokens"] + r["usage"]["output_tokens"] for r in records]
    stats = {"problems": len(records), "correct": sum(r["correct"] for r in records),
             "no_feasible_model": None, "accepted": None, "wrong_accepted": None,  # B0 and B1 have no verifier
             "mean_tokens": sum(tokens) / len(tokens) if tokens else 0.0}
    if all(r["verifier"] for r in records):
        accepted = [r for r in records if r["verifier"]["feasible"] and r["verifier"]["score"] >= threshold]
        stats.update(no_feasible_model=sum(not r["verifier"]["feasible"] for r in records), accepted=len(accepted),
                     wrong_accepted=sum(not r["correct"] for r in accepted))
    return stats


def _count(value) -> str:
    return "--" if value is None else str(value)


def compare(first: list[dict], second: list[dict], threshold: float) -> dict:
    a = {r["problem_id"]: r for r in first if "failed" not in r}
    b = {r["problem_id"]: r for r in second if "failed" not in r}
    shared = sorted(set(a) & set(b))
    groups = {"all": shared}
    for pid in shared:
        groups.setdefault(a[pid]["problem_class"], []).append(pid)
    result = {}
    for name in sorted(groups, key=lambda g: (g == "all", g)):
        ids = groups[name]
        first_ok = [a[i]["correct"] for i in ids]
        second_ok = [b[i]["correct"] for i in ids]
        result[name] = {
            "first": _stats([a[i] for i in ids], threshold), "second": _stats([b[i] for i in ids], threshold),
            "only_first_correct": sum(x and not y for x, y in zip(first_ok, second_ok)),
            "only_second_correct": sum(y and not x for x, y in zip(first_ok, second_ok)),
            "mcnemar_p": mcnemar_p(first_ok, second_ok),
        }
    return {"shared_problems": len(shared), "only_in_first": sorted(set(a) - set(b)),
            "only_in_second": sorted(set(b) - set(a)), "groups": result}


def markdown(result: dict) -> str:
    first, second = result["labels"]
    lines = [f"# {first} against {second}, paired on {result['shared_problems']} problems", "",
             f"- {first}: `{result['records'][0]}`", f"- {second}: `{result['records'][1]}`",
             f"- Threshold for accepted answers: {result['threshold']}", "",
             f"| Group | Problems | Correct, {first} / {second} | Only {first} / only {second} correct | McNemar p "
             f"| No feasible model | Accepted | Wrong accepted | Tokens per problem |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, g in result["groups"].items():
        x, y = g["first"], g["second"]
        lines.append(f"| {name} | {x['problems']} | {x['correct']} / {y['correct']} | {g['only_first_correct']} / "
                     f"{g['only_second_correct']} | {g['mcnemar_p']:.3f} | "
                     + " | ".join(f"{_count(x[key])} / {_count(y[key])}"
                                  for key in ("no_feasible_model", "accepted", "wrong_accepted"))
                     + f" | {x['mean_tokens']:,.0f} / {y['mean_tokens']:,.0f} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--labels", nargs=2, default=["first", "second"])
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = compare(load_run(args.first), load_run(args.second), args.threshold)
    result.update(labels=args.labels, threshold=args.threshold,
                  records=[args.first.as_posix(), args.second.as_posix()])
    text = markdown(result)
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "compare.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (args.out / "compare.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
