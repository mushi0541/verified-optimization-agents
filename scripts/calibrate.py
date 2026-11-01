"""Gap 2: calibrate the decision threshold to a target wrong-accept rate from saved pipeline records.

    python scripts/calibrate.py --records results/pipeline_.../records.jsonl --alpha 0.10 --out results/calibration/<name>.json

The output holds the leave-one-class-out test (per-fold thresholds and the pooled held-out wrong-accept rate with
its exact 95% interval), the same numbers for the fixed threshold (ablation vi), and one threshold calibrated on
every class for the application (`run.py --calibration`, `web.py --calibration`) and for shift tests.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optverify.calibration import fixed_threshold, leave_one_class_out, record_system  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--records", type=Path, required=True,
        help="records.jsonl of one pipeline or b2 run; B2 is calibrated on its own records, with its agreement rate as the score",
    )
    parser.add_argument("--alpha", type=float, default=0.10, help="target wrong-accept rate")
    parser.add_argument("--fixed-threshold", type=float, default=0.8, help="fixed threshold to compare with")
    parser.add_argument("--out", type=Path, required=True, help="output JSON file")
    args = parser.parse_args()

    records = [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = {
        "records": args.records.as_posix(),
        "system": record_system(records),  # run.py and web.py refuse the file for another system
        **leave_one_class_out(records, args.alpha),
        "fixed": fixed_threshold(records, args.fixed_threshold),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    pooled = result["pooled"]
    rate = "none answered" if pooled["wrong_accept_rate"] is None else f"{pooled['wrong_accept_rate']:.1%}"
    low, high = pooled["exact_interval"]
    print(f"alpha {args.alpha:.0%}: held-out wrong-accept rate {rate} [{low:.1%}, {high:.1%}], "
          f"coverage {pooled['coverage']:.1%}; all-classes threshold {result['threshold']}")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
