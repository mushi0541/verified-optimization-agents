"""The wrong-accept floor of a score: the share of wrong answers at the highest score, per class (no API calls).

    python scripts/score_floor.py --records results/<run>/records.jsonl [...] [--sample samples/canonical_200.json]
        --out results/gap2/score_floor

No threshold can accept fewer wrong answers than the strictest one, which accepts only the answers at the top score.
If a class has a wrong-accept rate above alpha at the top score, a calibration that holds that class out cannot meet
alpha on it, whatever rule picks the threshold. This report gives, for each run, the answers at the top score, how
many are wrong, per class, and the pooled rate with and without Pollution (whose references do not follow from the
text, #79).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from optverify.calibration import load_run, only_sample, scored_answers  # noqa: E402

DOUBTFUL = "Pollution"


def floor(records: list[dict]) -> dict:
    finished = [r for r in records if "failed" not in r]
    top = max(score for score, _ in scored_answers(finished))
    by_class: dict[str, dict] = {}
    for record in finished:
        cell = by_class.setdefault(record["problem_class"], {"answers": 0, "wrong": 0})
        if scored_answers([record]) and scored_answers([record])[0][0] >= top:
            cell["answers"] += 1
            cell["wrong"] += not record["correct"]

    def pooled(classes):
        answers = sum(by_class[c]["answers"] for c in classes)
        wrong = sum(by_class[c]["wrong"] for c in classes)
        return {"answers": answers, "wrong": wrong, "rate": wrong / answers if answers else None}

    classes = sorted(by_class)
    return {"top_score": top, "by_class": {c: by_class[c] for c in classes}, "all": pooled(classes),
            "without_pollution": pooled([c for c in classes if c != DOUBTFUL])}


def _pct(value):
    return "n/a" if value is None else f"{value:.1%}"


def markdown(result: dict) -> str:
    lines = ["# The wrong-accept floor at the top score", "",
             "Answers at the highest score of each run; no threshold accepts fewer wrong answers than this.", ""]
    if result["sample"]:
        lines += [f"**Only the problems of `{result['sample']}`** (`--sample`).", ""]
    classes = sorted({c for run in result["runs"] for c in run["by_class"]})
    lines += ["| Run | Top score | " + " | ".join(classes) + " | All | Without Pollution |",
              "|---|---|" + "---|" * (len(classes) + 2)]
    for path, run in zip(result["records"], result["runs"]):
        cells = []
        for c in classes:
            cell = run["by_class"].get(c, {"answers": 0, "wrong": 0})
            cells.append(f"{cell['wrong']}/{cell['answers']}")
        lines.append(f"| `{Path(path).parent.name}` | {run['top_score']:.3f} | " + " | ".join(cells)
                     + f" | {run['all']['wrong']}/{run['all']['answers']} ({_pct(run['all']['rate'])})"
                     + f" | {run['without_pollution']['wrong']}/{run['without_pollution']['answers']}"
                     + f" ({_pct(run['without_pollution']['rate'])}) |")
    lines += ["", "Cells are wrong / answers at the top score."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--records", type=Path, nargs="+", required=True)
    parser.add_argument("--sample", type=Path, help="only the problems of this sample file, in every run")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    runs = []
    for path in args.records:
        records = load_run(path)
        runs.append(floor(only_sample(records, args.sample) if args.sample else records))
    result = {"records": [p.as_posix() for p in args.records], "sample": args.sample.as_posix() if args.sample else None,
              "runs": runs}
    text = markdown(result)
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "score_floor.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (args.out / "score_floor.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
