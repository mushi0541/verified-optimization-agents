"""Download the OPT-Engine (C^3-Bench) test data, pinned to one commit so everyone uses the same files.

The upstream repository has no licence file, so the data is downloaded instead of being stored in this repo.
Source: https://github.com/Cardinal-Operations/OPTEngine (Chen et al., ICML 2026)
"""

import urllib.request
from pathlib import Path

COMMIT = "d84a4b49187071debf16f50ba03a193776213edd"
BASE_URL = f"https://raw.githubusercontent.com/Cardinal-Operations/OPTEngine/{COMMIT}/test_data"
FILES = [
    "canonical/canonical.jsonl",
    "perturbations/linguistic_complexity.jsonl",
    "perturbations/constraint_augmentation.jsonl",
    "perturbations/objective_perturbation.jsonl",
]
TARGET_DIR = Path(__file__).resolve().parent.parent / "data" / "optengine"


def main() -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    for remote_path in FILES:
        target = TARGET_DIR / Path(remote_path).name
        urllib.request.urlretrieve(f"{BASE_URL}/{remote_path}", target)
        line_count = sum(1 for _ in target.open(encoding="utf-8"))
        print(f"{target.name}: {line_count} problems")


if __name__ == "__main__":
    main()
