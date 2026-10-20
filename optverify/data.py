"""Loads the OPT-Engine (C^3-Bench) test data downloaded by scripts/download_data.py."""

import json
import random
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


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
