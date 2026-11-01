"""Ablations from saved pipeline records, with no LLM calls (Gap 1 switches, k, repairs, threshold).

    python scripts/rescore.py --records results/pipeline_.../records.jsonl --signals number,paraphrase --k 2 --alpha 0.10

Each record is rescored with only the enabled signals (i to iii), its first k paraphrase runs (v) and, with
--no-repair, its first attempt (vii, r = 0), and the tokens of the dropped steps are taken off. The decision then
uses a fixed threshold, a calibration file, or a leave-one-class-out calibration to --alpha on the rescored
records (vi). Ablation iv (no parser) and r = 2 need their own runs: `run.py pipeline --no-parser` or `--repairs 2`.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optverify.calibration import fixed_threshold, leave_one_class_out, load_run, threshold_from_file  # noqa: E402
from optverify.rescore import rescore  # noqa: E402
from optverify.run import parse_signals  # noqa: E402
from optverify.verifier import SIGNALS  # noqa: E402


def rescore_records(records: list[dict], signals=SIGNALS, k=None, repairs=True) -> list[dict]:
    """Rescored outcomes in the record shape the calibration functions read; failed problems are kept as failed."""
    rescored = []
    for record in records:
        if "failed" in record:
            rescored.append(record)
            continue
        outcome = rescore(record, signals, k, repairs)
        rescored.append({**outcome, "verifier": {"feasible": outcome["feasible"], "score": outcome["score"]}})
    return rescored


def summarize(rescored: list[dict], args: argparse.Namespace) -> dict:
    finished = [r for r in rescored if "failed" not in r]
    if args.alpha is not None:
        decision = leave_one_class_out(rescored, args.alpha)
    elif args.calibration:
        decision = fixed_threshold(rescored, threshold_from_file(json.loads(args.calibration.read_text(encoding="utf-8"))))
    else:
        decision = fixed_threshold(rescored, args.threshold)
    return {
        "records": [path.as_posix() for path in args.records],
        "settings": {"signals": list(args.signals), "k": args.k, "repairs": not args.no_repair},
        "problems": len(finished),
        "failed_problems": len(rescored) - len(finished),
        "accuracy": sum(r["correct"] for r in finished) / len(finished) if finished else 0.0,
        "mean_tokens": sum(r["tokens"] for r in finished) / len(finished) if finished else 0.0,
        "mean_calls": sum(r["calls"] for r in finished) / len(finished) if finished else 0.0,
        "decision": decision,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--records", type=Path, nargs="+", required=True, help="records.jsonl of pipeline runs")
    parser.add_argument("--signals", type=parse_signals, default=SIGNALS, help="as in run.py, e.g. number,paraphrase or none")
    parser.add_argument("--k", type=int, help="paraphrase runs to keep (default: all in the records)")
    parser.add_argument("--no-repair", action="store_true", help="use the first attempt only (r = 0)")
    decision = parser.add_mutually_exclusive_group()
    decision.add_argument("--threshold", type=float, default=0.8, help="fixed threshold (default 0.8)")
    decision.add_argument("--calibration", type=Path, help="apply the threshold of a calibration file")
    decision.add_argument("--alpha", type=float, help="leave-one-class-out calibration to this wrong-accept rate")
    parser.add_argument("--out", type=Path, help="output JSON file")
    args = parser.parse_args()

    records = []
    for path in args.records:
        records += load_run(path)  # failed problems included, as unanswered
    result = summarize(rescore_records(records, args.signals, args.k, not args.no_repair), args)
    text = json.dumps(result, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
