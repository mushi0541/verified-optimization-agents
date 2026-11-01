"""Generate fixed evaluation sample files for canonical, ablation, linguistic, and constraint splits."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from optverify.data import (
    DATA_DIR,
    load_split,
    sample_ablation_subset,
    sample_canonical,
    sample_constraint_pairs,
    sample_linguistic,
    sample_per_class,
    save_sample_file,
)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "samples"


def generate_samples(output_dir: Path = DEFAULT_OUTPUT_DIR, data_dir: Path = DATA_DIR) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading canonical split...")
    canonical_problems = load_split("canonical", data_dir=data_dir)
    canonical_sample = sample_canonical(canonical_problems, per_class=10, seed=0)
    canonical_path = output_dir / "canonical_100.json"
    save_sample_file(canonical_path, [p.problem_id for p in canonical_sample])
    print(f"Saved {len(canonical_sample)} canonical problems to {canonical_path}")

    ablation_sample = sample_ablation_subset(canonical_sample, per_class=3, seed=0)
    ablation_path = output_dir / "ablation_30.json"
    save_sample_file(ablation_path, [p.problem_id for p in ablation_sample])
    print(f"Saved {len(ablation_sample)} ablation problems to {ablation_path}")

    print("Loading linguistic split...")
    linguistic_problems = load_split("linguistic", data_dir=data_dir)
    linguistic_sample = sample_linguistic(linguistic_problems, per_class=10, seed=0)
    linguistic_path = output_dir / "linguistic_30.json"
    save_sample_file(linguistic_path, [p.problem_id for p in linguistic_sample])
    print(f"Saved {len(linguistic_sample)} linguistic problems to {linguistic_path}")

    print("Loading constraint split...")
    constraint_problems = load_split("constraint", data_dir=data_dir)
    constraint_pairs = sample_constraint_pairs(constraint_problems, per_class=10, seed=0)
    constraint_path = output_dir / "constraint_pairs_30.json"
    save_sample_file(constraint_path, constraint_pairs)
    print(f"Saved {len(constraint_pairs)} constraint pairs to {constraint_path}")

    excluded_ids: set[str] = set()
    excluded_ids.update(str(p.problem_id) for p in canonical_sample)
    excluded_ids.update(str(p.problem_id) for p in ablation_sample)
    excluded_ids.update(str(p.problem_id) for p in linguistic_sample)
    for pair in constraint_pairs:
        excluded_ids.add(str(pair["original"]))
        excluded_ids.add(str(pair["augmented"]))

    dev_pool = [p for p in canonical_problems if str(p.problem_id) not in excluded_ids]
    dev_sample = sample_per_class(dev_pool, per_class=3, seed=1)
    dev_path = output_dir / "dev_30.json"
    save_sample_file(dev_path, [p.problem_id for p in dev_sample])
    print(f"Saved {len(dev_sample)} dev problems to {dev_path}")

    return {
        "canonical": canonical_path,
        "ablation": ablation_path,
        "linguistic": linguistic_path,
        "constraint": constraint_path,
        "dev": dev_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fixed evaluation sample files.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save sample JSON files (default: samples).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directory containing dataset jsonl files (default: data/optengine).",
    )
    args = parser.parse_args()
    generate_samples(output_dir=args.output_dir, data_dir=args.data_dir)


if __name__ == "__main__":
    main()
