"""Generate fixed evaluation sample files for canonical, ablation, linguistic, and constraint splits.

The Phase 2 test samples (canonical_200, canonical_587, ablation_50, linguistic_60, constraint_pairs_60) each contain the
smaller Phase 1 sample (canonical_100, ablation_30, linguistic_30, constraint_pairs_30) plus new problems,
so results on the smaller samples stay valid. The dev sample shares no problem with any test sample.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from optverify.data import (
    DATA_DIR,
    extend_constraint_pairs,
    extend_per_class,
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

    def save(name: str, items: list) -> Path:
        path = output_dir / name
        save_sample_file(path, [p if isinstance(p, dict) else p.problem_id for p in items])
        print(f"Saved {len(items)} items to {path}")
        return path

    print("Loading canonical split...")
    canonical_problems = load_split("canonical", data_dir=data_dir)
    canonical_100 = sample_canonical(canonical_problems, per_class=10, seed=0)
    canonical_200 = extend_per_class(canonical_problems, canonical_100, per_class=10, seed=0)
    ablation_30 = sample_ablation_subset(canonical_100, per_class=3, seed=0)
    ablation_50 = extend_per_class(canonical_100, ablation_30, per_class=2, seed=0)

    print("Loading linguistic split...")
    linguistic_problems = load_split("linguistic", data_dir=data_dir)
    linguistic_30 = sample_linguistic(linguistic_problems, per_class=10, seed=0)
    linguistic_60 = extend_per_class(linguistic_problems, linguistic_30, per_class=10, seed=0)

    print("Loading constraint split...")
    constraint_problems = load_split("constraint", data_dir=data_dir)
    constraint_pairs_30 = sample_constraint_pairs(constraint_problems, per_class=10, seed=0)
    constraint_pairs_60 = extend_constraint_pairs(constraint_problems, constraint_pairs_30, per_class=10, seed=0)

    paths = {
        "canonical": save("canonical_100.json", canonical_100),
        "canonical_200": save("canonical_200.json", canonical_200),
        "ablation": save("ablation_30.json", ablation_30),
        "ablation_50": save("ablation_50.json", ablation_50),
        "linguistic": save("linguistic_30.json", linguistic_30),
        "linguistic_60": save("linguistic_60.json", linguistic_60),
        "constraint": save("constraint_pairs_30.json", constraint_pairs_30),
        "constraint_60": save("constraint_pairs_60.json", constraint_pairs_60),
    }

    # The larger samples contain the smaller ones, so excluding them excludes every test problem.
    excluded_ids = {p.problem_id for p in canonical_200 + linguistic_60}
    excluded_ids |= {pair[key] for pair in constraint_pairs_60 for key in ("original", "augmented")}
    dev_pool = [p for p in canonical_problems if p.problem_id not in excluded_ids]
    dev_30 = sample_per_class(dev_pool, per_class=3, seed=1)
    paths["dev"] = save("dev_30.json", dev_30)

    # The H2 power analysis on E3 repeat 1 (devlog entry 13): certifying alpha = 10% needs several hundred accepted
    # calibration answers, so canonical_587 adds up to 40 problems per class to canonical_200 (60 per class; NetworkFlow has only 50 in
    # the benchmark and 3 are in dev_30, so it gets 47). It never takes a development problem. The development split
    # grows to dev_93 the same way (dev_30 plus 7 per class; no NetworkFlow problem is left), outside every test
    # sample, so signal changes can be designed on more than 30 problems. Every file above stays as it was.
    dev_ids = {p.problem_id for p in dev_30}
    canonical_587 = extend_per_class([p for p in canonical_problems if p.problem_id not in dev_ids], canonical_200,
                                     per_class=40, seed=0)
    paths["canonical_587"] = save("canonical_587.json", canonical_587)
    test_ids = excluded_ids | {p.problem_id for p in canonical_587}
    dev_93 = extend_per_class([p for p in dev_pool if p.problem_id not in test_ids], dev_30, per_class=7, seed=1)
    paths["dev_93"] = save("dev_93.json", dev_93)
    # Development problems for the v2 prompts (#95): 30 TSP and 30 Inventory problems in no sample above, test or
    # development, so the prompt change is designed without touching the test set.
    used_ids = test_ids | {p.problem_id for p in dev_93}
    v2_pool = [p for p in canonical_problems if p.problem_id not in used_ids and p.problem_class in ("Inventory", "TSP")]
    paths["dev_tsp_inventory_60"] = save("dev_tsp_inventory_60.json", sample_per_class(v2_pool, per_class=30, seed=2))
    return paths



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
