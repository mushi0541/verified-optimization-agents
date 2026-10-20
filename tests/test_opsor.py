import hashlib
import re
from pathlib import Path

from optverify.data import load_split
from optverify.opsor import (
    DEFAULT_OPSOR_PATH,
    assert_question_contains_numbers,
    generate_opsor_dataset,
    save_opsor_jsonl,
)
from optverify.run import parse_args


def _extract_problem_numbers(problem) -> list[float | int]:
    """Extract all numerical constants used by a problem's reference model."""
    params = problem.meta["params"]
    if problem.problem_class == "GateAssignment":
        numbers = [params["buffer_minutes"]]
        for gate in params["gates"]:
            numbers.append(gate["walking_distance"])
        for flight in params["flights"]:
            numbers.extend([flight["arrival_minute"], flight["departure_minute"], flight["passengers"]])
        return numbers
    elif problem.problem_class == "CrewRostering":
        numbers = [params["max_consecutive"]]
        for shift in params["shifts"]:
            numbers.append(shift["required_crew"])
        for worker in params["workers"]:
            numbers.extend([worker["shift_cost"], worker["max_shifts"]])
        return numbers
    elif problem.problem_class == "EquipmentDispatch":
        numbers = []
        for unit in params["units"]:
            numbers.extend([unit["fixed_cost"], unit["max_hours"]])
        for req in params["requests"]:
            numbers.append(req["required_hours"])
        for cost in params["transit_costs"].values():
            numbers.append(cost)
        return numbers
    raise ValueError(f"Unknown problem class: {problem.problem_class}")


def test_question_text_contains_every_model_number():
    """Verify that question text explicitly contains all numbers used by the reference model for all problems."""
    problems = generate_opsor_dataset()
    for problem in problems:
        numbers = _extract_problem_numbers(problem)
        assert_question_contains_numbers(problem.question, numbers)


def test_generation_determinism_across_reruns(tmp_path):
    """Verify that generation is strictly deterministic down to matching SHA-256 hashes."""
    problems_first = generate_opsor_dataset()
    problems_second = generate_opsor_dataset()

    assert len(problems_first) == len(problems_second)
    for p1, p2 in zip(problems_first, problems_second):
        assert p1.problem_id == p2.problem_id
        assert p1.answer == p2.answer
        assert p1.size == p2.size
        assert p1.problem_class == p2.problem_class
        assert p1.question == p2.question

    temp_target = save_opsor_jsonl(problems_first, output_path=tmp_path / "opsor_bench.jsonl")
    hash_temp = hashlib.sha256(temp_target.read_bytes()).hexdigest()
    hash_existing = hashlib.sha256(DEFAULT_OPSOR_PATH.read_bytes()).hexdigest()
    assert hash_temp == hash_existing


def test_load_split_opsor_returns_problem_records():
    """Verify that load_split('opsor') returns valid standard Problem records."""
    problems = load_split("opsor")
    assert len(problems) == 36

    classes = [p.problem_class for p in problems]
    assert classes.count("GateAssignment") == 12
    assert classes.count("CrewRostering") == 12
    assert classes.count("EquipmentDispatch") == 12

    for problem in problems:
        assert re.match(r"^opsor-\d{4}$", problem.problem_id)
        assert problem.problem_class in {"GateAssignment", "CrewRostering", "EquipmentDispatch"}
        assert problem.split == "opsor"
        assert isinstance(problem.answer, float) and problem.answer > 0


def test_run_parser_accepts_opsor_split():
    """Verify that --split opsor is valid in optverify/run.py CLI parsing."""
    args = parse_args(["baseline", "--model", "dummy", "--split", "opsor", "--per-class", "3"])
    assert args.split == "opsor"
    assert args.per_class == 3

    # Load problem subset using parsed args
    problems = load_split(args.split)
    assert len(problems) == 36

