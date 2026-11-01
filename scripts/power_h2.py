"""How many accepted calibration answers certify a wrong-accept rate of alpha (Gap 2 power analysis, devlog entry 13).

    python scripts/power_h2.py [--alpha 0.10] [--rates 0.05 0.06 0.07 0.08]

For each true wrong-accept rate, the smallest number of accepted answers n whose one-sided exact 95% upper bound
(optverify.calibration.upper_bound, the bound the calibration uses) is at most alpha, with round(rate * n) wrong.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optverify.calibration import upper_bound  # noqa: E402


def needed(rate: float, alpha: float) -> int:
    n = 1
    while upper_bound(round(rate * n), n) > alpha:
        n += 1
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--rates", type=float, nargs="+", default=[0.05, 0.06, 0.07, 0.08])
    args = parser.parse_args()
    print("| Wrong-accept rate among accepted | Accepted answers needed |")
    print("|---|---|")
    for rate in args.rates:
        print(f"| {rate:.0%} | {needed(rate, args.alpha)} |")


if __name__ == "__main__":
    main()
