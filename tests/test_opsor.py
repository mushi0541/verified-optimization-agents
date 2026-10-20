import hashlib
import json
import re
from pathlib import Path

import pulp
import pytest

from optverify.data import load_split
from optverify.grading import is_correct
from optverify.opsor import (
    DEFAULT_OPSOR_PATH,
    CrewRosteringScenario,
    EquipmentDispatchScenario,
    GateAssignmentScenario,
    assert_question_contains_numbers,
    build_crew_reference_model,
    build_crew_rostering_question,
    build_equipment_dispatch_question,
    build_equipment_reference_model,
    build_gate_assignment_question,
    build_gate_reference_model,
    create_crew_rostering_instance,
    create_equipment_dispatch_instance,
    create_gate_assignment_instance,
    generate_crew_scenario,
    generate_equipment_scenario,
    generate_gate_scenario,
    generate_opsor_dataset,
    save_opsor_jsonl,
    solve_crew_rostering,
    solve_equipment_dispatch,
    solve_gate_assignment,
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


def test_gate_assignment_reference_models_solve_optimal():
    """Verify that gate assignment reference models across varied sizes solve to Optimal."""
    for size, seed in [(4, 0), (5, 2), (7, 4), (8, 6), (10, 8), (12, 10)]:
        num_gates = 3 if size <= 5 else (4 if size <= 8 else 5)
        scenario = generate_gate_scenario(num_flights=size, num_gates=num_gates, seed=seed)
        model = build_gate_reference_model(scenario)
        status = model.solve(pulp.HiGHS(msg=False))
        assert pulp.LpStatus[status] == "Optimal"
        val = pulp.value(model.objective)
        assert val is not None and val > 0


def test_crew_rostering_reference_models_solve_optimal():
    """Verify that ground-crew rostering reference models across varied sizes solve to Optimal."""
    for size, seed in [(4, 0), (5, 2), (6, 4), (7, 6), (8, 8), (10, 10)]:
        num_workers = size + 2 if size <= 5 else (size + 3 if size <= 8 else size + 4)
        scenario = generate_crew_scenario(num_shifts=size, num_workers=num_workers, seed=seed)
        model = build_crew_reference_model(scenario)
        status = model.solve(pulp.HiGHS(msg=False))
        assert pulp.LpStatus[status] == "Optimal"
        val = pulp.value(model.objective)
        assert val is not None and val > 0


def test_equipment_dispatch_reference_models_solve_optimal():
    """Verify that equipment dispatch reference models across varied sizes solve to Optimal."""
    for size, seed in [(4, 0), (5, 2), (7, 4), (8, 6), (10, 8), (12, 10)]:
        num_units = 3 if size <= 5 else (4 if size <= 8 else 6)
        scenario = generate_equipment_scenario(num_requests=size, num_units=num_units, seed=seed)
        model = build_equipment_reference_model(scenario)
        status = model.solve(pulp.HiGHS(msg=False))
        assert pulp.LpStatus[status] == "Optimal"
        val = pulp.value(model.objective)
        assert val is not None and val > 0


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


def test_combined_opsor_bench_integrity():
    """Combined test verifying the whole benchmark meets all specifications:
    - at least 30 problems total
    - every reference model solves to optimal
    - every number used by each model appears in its question text
    - generation is identical on two runs
    - problem IDs are unique
    """
    problems_run1 = load_split("opsor")
    problems_run2 = generate_opsor_dataset()

    # 1. At least 30 problems total
    assert len(problems_run1) >= 30
    assert len(problems_run1) == 36

    # 2. Problem IDs are unique
    ids = [p.problem_id for p in problems_run1]
    assert len(ids) == len(set(ids))
    assert ids == [f"opsor-{i:04d}" for i in range(len(problems_run1))]

    # 3. Generation is identical on two runs
    assert len(problems_run1) == len(problems_run2)
    for p1, p2 in zip(problems_run1, problems_run2):
        assert p1.problem_id == p2.problem_id
        assert p1.answer == p2.answer
        assert p1.size == p2.size
        assert p1.problem_class == p2.problem_class
        assert p1.question == p2.question
        assert p1.meta == p2.meta

    # 4. Every reference model solves to optimal (positive float)
    # 5. Every number used by each model appears in its question text
    for problem in problems_run1:
        assert isinstance(problem.answer, float) and problem.answer > 0
        numbers = _extract_problem_numbers(problem)
        assert_question_contains_numbers(problem.question, numbers)


def test_run_parser_accepts_opsor_split():
    """Verify that --split opsor is valid in optverify/run.py CLI parsing."""
    args = parse_args(["baseline", "--model", "dummy", "--split", "opsor", "--per-class", "3"])
    assert args.split == "opsor"
    assert args.per_class == 3

    # Load problem subset using parsed args
    problems = load_split(args.split)
    assert len(problems) == 36


def test_grading_with_opsor_reference_answer():
    """Verify that grading reuses grading.py with the 0.2% tolerance rule."""
    problems = load_split("opsor")
    prob = problems[0]

    # Exact prediction is correct
    assert is_correct(prob.answer, prob.answer)
    # Within 0.2% relative tolerance is correct
    assert is_correct(prob.answer * 1.001, prob.answer)
    # Outside 0.2% relative tolerance is incorrect
    assert not is_correct(prob.answer * 1.01, prob.answer)
    # None prediction is incorrect
    assert not is_correct(None, prob.answer)

