"""Loads the OPT-Engine (C^3-Bench) test data downloaded by scripts/download_data.py."""

import json
import random
import re
from pathlib import Path

from .contracts import Problem

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "optengine"

SPLIT_FILES = {
    "canonical": "canonical.jsonl",
    "linguistic": "linguistic_complexity.jsonl",
    "constraint": "constraint_augmentation.jsonl",
    "objective": "objective_perturbation.jsonl",
}

_STANDARD_FIELDS = {"question", "answer", "problem_class", "size", "experimental_type"}


def load_split(split: str, data_dir: Path = DATA_DIR) -> list[Problem]:
    path = data_dir / SPLIT_FILES[split]
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing. Run: python scripts/download_data.py")

    problems = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file):
            row = json.loads(line)
            problems.append(
                Problem(
                    problem_id=f"{split}-{line_number:04d}",
                    question=row["question"],
                    answer=_to_float(row["answer"]),
                    problem_class=row["problem_class"],
                    size=int(row["size"]),
                    split=split,
                    meta={key: value for key, value in row.items() if key not in _STANDARD_FIELDS},
                )
            )
    return problems


def sample_per_class(problems: list[Problem], per_class: int, seed: int = 0) -> list[Problem]:
    """Pick the same number of problems from every class with a fixed seed, so runs can be repeated."""
    rng = random.Random(seed)
    by_class: dict[str, list[Problem]] = {}
    for problem in problems:
        by_class.setdefault(problem.problem_class, []).append(problem)

    chosen = []
    for problem_class in sorted(by_class):
        members = by_class[problem_class]
        chosen += rng.sample(members, min(per_class, len(members)))
    return chosen


def sample_canonical(problems: list[Problem], per_class: int = 10, seed: int = 0) -> list[Problem]:
    """Sample canonical problems evenly across classes with a fixed seed."""
    return sample_per_class(problems, per_class=per_class, seed=seed)


def sample_linguistic(problems: list[Problem], per_class: int = 10, seed: int = 0) -> list[Problem]:
    """Sample linguistic complexity problems evenly across classes with a fixed seed."""
    return sample_per_class(problems, per_class=per_class, seed=seed)


def sample_ablation_subset(canonical_sample: list[Problem], per_class: int = 3, seed: int = 0) -> list[Problem]:
    """Sample an ablation subset directly from the canonical evaluation sample with a fixed seed."""
    return sample_per_class(canonical_sample, per_class=per_class, seed=seed)


def extract_knapsack_capacity(question: str) -> int | None:
    """Extract vehicle or container capacity from a Knapsack question text."""
    match = re.search(
        r"(?:maximum capacity of|gross weight.*?is|capacity is|carry at most|payload.*?of|weight limit.*?is|allowance of|limit of|capacity:)\s*(\d+)",
        question,
        re.IGNORECASE,
    )
    if match:
        return int(match.group(1))
    numbers = [int(token) for token in re.findall(r"\b\d+\b", question)]
    return numbers[-1] if numbers else None


def knapsack_item_key(problem: Problem) -> tuple[tuple[tuple[int, int], ...], int | None]:
    """Base key for Knapsack: sorted (weight, profit) items and container capacity."""
    items = []
    for line in problem.question.split("\n"):
        stripped = line.strip()
        if stripped.startswith("*") or stripped.startswith("-"):
            nums = [int(token) for token in re.findall(r"\d+", stripped)]
            if len(nums) >= 2:
                items.append((nums[-2], nums[-1]))
    capacity = extract_knapsack_capacity(problem.question)
    return tuple(sorted(items)), capacity


def tsp_distance_set(problem: Problem) -> set[float]:
    """Set of rounded edge distances extracted from a TSP question text."""
    distances = []
    for line in problem.question.split("\n"):
        if "to" in line and ":" in line:
            after_colon = line.split(":", 1)[1]
            match = re.search(r"(\d+(?:\.\d+)?)", after_colon)
            if match:
                distances.append(round(float(match.group(1)), 2))
    return set(distances)


def match_knapsack_pairs(problems: list[Problem]) -> list[dict]:
    """Pair Knapsack original and augmented problems sharing identical items and capacity."""
    orig = [p for p in problems if p.problem_class == "Knapsack" and p.meta.get("constraint_type") == "original"]
    aug = [p for p in problems if p.problem_class == "Knapsack" and p.meta.get("constraint_type") == "augmented"]

    aug_by_key: dict[tuple, list[Problem]] = {}
    for problem in aug:
        key = knapsack_item_key(problem)
        aug_by_key.setdefault(key, []).append(problem)

    pairs = []
    for problem in sorted(orig, key=lambda p: p.problem_id):
        key = knapsack_item_key(problem)
        matches = aug_by_key.get(key, [])
        if len(matches) == 1:
            pairs.append({
                "original": problem.problem_id,
                "augmented": matches[0].problem_id,
                "problem_class": "Knapsack",
                "pairing": "matched_data",
            })
    return pairs


def match_tsp_pairs(problems: list[Problem]) -> list[dict]:
    """Pair TSP original and augmented problems sharing identical distance matrices minus one forbidden edge."""
    orig = [p for p in problems if p.problem_class == "TSP" and p.meta.get("constraint_type") == "original"]
    aug = [p for p in problems if p.problem_class == "TSP" and p.meta.get("constraint_type") == "augmented"]
    aug_dists = [(p, tsp_distance_set(p)) for p in aug]

    pairs = []
    for problem in sorted(orig, key=lambda p: p.problem_id):
        orig_set = tsp_distance_set(problem)
        matches = [
            a for a, a_set in aug_dists
            if a.size == problem.size and a_set.issubset(orig_set) and len(orig_set - a_set) == 1
        ]
        if len(matches) == 1:
            pairs.append({
                "original": problem.problem_id,
                "augmented": matches[0].problem_id,
                "problem_class": "TSP",
                "pairing": "matched_data",
            })
    return pairs


def match_inventory_pairs(problems: list[Problem], seed: int = 0) -> list[dict]:
    """Pair Inventory original and augmented problems by problem class and size without reuse.

    In C^3-Bench, only one Inventory problem has identical base parameters between original and
    augmented splits. The remaining augmented problems were generated with distinct parameter draws
    for each size tier. Therefore, we deterministically pair problems matching on (problem_class, size).
    """
    orig = [p for p in problems if p.problem_class == "Inventory" and p.meta.get("constraint_type") == "original"]
    aug = [p for p in problems if p.problem_class == "Inventory" and p.meta.get("constraint_type") == "augmented"]

    aug_by_size: dict[int, list[Problem]] = {}
    for problem in sorted(aug, key=lambda p: p.problem_id):
        aug_by_size.setdefault(problem.size, []).append(problem)

    rng = random.Random(seed)
    for size in aug_by_size:
        rng.shuffle(aug_by_size[size])

    pairs = []
    for problem in sorted(orig, key=lambda p: p.problem_id):
        matched = aug_by_size[problem.size].pop(0)
        pairs.append({
            "original": problem.problem_id,
            "augmented": matched.problem_id,
            "problem_class": "Inventory",
            "pairing": "class_and_size",
        })
    return pairs


def sample_constraint_pairs(problems: list[Problem], per_class: int = 10, seed: int = 0) -> list[dict]:
    """Sample matched constraint-augmentation pairs across Inventory, Knapsack, and TSP."""
    knap_pairs = match_knapsack_pairs(problems)
    tsp_pairs = match_tsp_pairs(problems)
    inv_pairs = match_inventory_pairs(problems, seed=seed)

    rng = random.Random(seed)
    chosen_inv = rng.sample(sorted(inv_pairs, key=lambda p: p["original"]), min(per_class, len(inv_pairs)))
    chosen_knap = rng.sample(sorted(knap_pairs, key=lambda p: p["original"]), min(per_class, len(knap_pairs)))
    chosen_tsp = rng.sample(sorted(tsp_pairs, key=lambda p: p["original"]), min(per_class, len(tsp_pairs)))

    sampled = chosen_inv + chosen_knap + chosen_tsp
    for pair_id, pair in enumerate(sampled):
        pair["pair_id"] = pair_id
    return sampled


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
