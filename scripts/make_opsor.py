"""Generate the OpsOR-Bench dataset file data/opsor/opsor_bench.jsonl."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from optverify.opsor.registry import DEFAULT_OPSOR_PATH, generate_opsor_dataset, save_opsor_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OpsOR-Bench problem dataset.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OPSOR_PATH,
        help="Path to output JSONL file (default: data/opsor/opsor_bench.jsonl).",
    )
    args = parser.parse_args()

    print("Generating OpsOR-Bench dataset...")
    problems = generate_opsor_dataset()
    saved_path = save_opsor_jsonl(problems, output_path=args.output)
    print(f"Saved {len(problems)} OpsOR problems to {saved_path}")


if __name__ == "__main__":
    main()
