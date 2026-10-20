"""Registry and coordination for OpsOR-Bench problem generation."""

from __future__ import annotations

import json
from pathlib import Path

from optverify.contracts import Problem
from .base import OpsORInstance
from .gate_assignment import create_gate_assignment_instance

OPSOR_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "opsor"
DEFAULT_OPSOR_PATH = OPSOR_DATA_DIR / "opsor_bench.jsonl"

# Family instance generator dispatch
FAMILY_GENERATORS = {
    "GateAssignment": create_gate_assignment_instance,
}

# Gate assignment size and seed configurations: 4 Easy, 4 Medium, 4 Hard = 12 problems
GATE_ASSIGNMENT_SPECS = [
    # Easy tier (4-5 flights)
    {"size": 4, "seed": 0},
    {"size": 4, "seed": 1},
    {"size": 5, "seed": 2},
    {"size": 5, "seed": 3},
    # Medium tier (7-8 flights)
    {"size": 7, "seed": 4},
    {"size": 7, "seed": 5},
    {"size": 8, "seed": 6},
    {"size": 8, "seed": 7},
    # Hard tier (10-12 flights)
    {"size": 10, "seed": 8},
    {"size": 10, "seed": 9},
    {"size": 12, "seed": 10},
    {"size": 12, "seed": 11},
]


def generate_opsor_dataset(families: list[str] | None = None) -> list[Problem]:
    """Generate all registered OpsOR-Bench problem instances as standard Problem records."""
    target_families = families or ["GateAssignment"]
    problems: list[Problem] = []
    current_index = 0

    if "GateAssignment" in target_families:
        generator = FAMILY_GENERATORS["GateAssignment"]
        for spec in GATE_ASSIGNMENT_SPECS:
            instance: OpsORInstance = generator(size=spec["size"], seed=spec["seed"])
            problem_id = f"opsor-{current_index:04d}"
            problems.append(instance.to_problem(problem_id))
            current_index += 1

    return problems


def save_opsor_jsonl(problems: list[Problem], output_path: Path | str = DEFAULT_OPSOR_PATH) -> Path:
    """Save OpsOR problems to JSONL format matching C^3-Bench schema."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8", newline="\n") as file:
        for problem in problems:
            row = {
                "question": problem.question,
                "answer": problem.answer,
                "problem_class": problem.problem_class,
                "size": problem.size,
                "split": problem.split,
                **problem.meta,
            }
            file.write(json.dumps(row, sort_keys=True) + "\n")

    return target
