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
    GateAssignmentScenario,
    assert_question_contains_numbers,
    build_gate_assignment_question,
    build_gate_reference_model,
    create_gate_assignment_instance,
    generate_gate_scenario,
    generate_opsor_dataset,
    save_opsor_jsonl,
    solve_gate_assignment,
)
from optverify.run import parse_args


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


def test_question_text_contains_every_model_number():
    """Verify that question text explicitly contains all numbers used by the reference model."""
    problems = generate_opsor_dataset()
    for problem in problems:
        params = problem.meta["params"]
        # Reconstruct scenario numbers
        numbers = [params["buffer_minutes"]]
        for gate in params["gates"]:
            numbers.append(gate["walking_distance"])
        for flight in params["flights"]:
            numbers.extend([flight["arrival_minute"], flight["departure_minute"], flight["passengers"]])

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
        assert p1.question == p2.question

    temp_target = save_opsor_jsonl(problems_first, output_path=tmp_path / "opsor_bench.jsonl")
    hash_temp = hashlib.sha256(temp_target.read_bytes()).hexdigest()
    hash_existing = hashlib.sha256(DEFAULT_OPSOR_PATH.read_bytes()).hexdigest()
    assert hash_temp == hash_existing


def test_load_split_opsor_returns_problem_records():
    """Verify that load_split('opsor') returns valid standard Problem records."""
    problems = load_split("opsor")
    assert len(problems) == 12

    for problem in problems:
        assert re.match(r"^opsor-\d{4}$", problem.problem_id)
        assert problem.problem_class == "GateAssignment"
        assert problem.split == "opsor"
        assert isinstance(problem.answer, float) and problem.answer > 0
        assert problem.size in {4, 5, 7, 8, 10, 12}
        assert "An airport terminal must assign scheduled flights" in problem.question


def test_run_parser_accepts_opsor_split():
    """Verify that --split opsor is valid in optverify/run.py CLI parsing."""
    args = parse_args(["baseline", "--model", "dummy", "--split", "opsor", "--per-class", "3"])
    assert args.split == "opsor"
    assert args.per_class == 3

    # Load problem subset using parsed args
    problems = load_split(args.split)
    assert len(problems) == 12


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
