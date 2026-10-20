import random

import pytest

from scripts.analyze_e3 import (
    analyze,
    b2_at,
    baseline_points,
    clopper_pearson,
    mcnemar_p,
    percentile_interval,
    pipeline_at,
    wrong_accept_at_coverage,
)


def _usage(tokens: int, calls: int) -> dict:
    return {"input_tokens": tokens, "output_tokens": 0, "calls": calls}


def _solve(objective):
    return {"solve": {"status": "optimal" if objective is not None else "error", "objective": objective}}


def pipeline_record(problem_id: str, main: float | None, others: list, reference: float = 100.0) -> dict:
    """A k = 3 pipeline record: parse 100, formalize 200 and each paraphrase run 50 tokens."""
    steps = {"parse": _usage(100, 1), "formalize": _usage(200, 1), "repair": _usage(0, 0)}
    if main is not None:
        steps.update({f"paraphrase_{j}": _usage(50, 2) for j in range(1, len(others) + 1)})
    return {
        "problem_id": problem_id,
        "reference": reference,
        "attempts": [_solve(main)],
        "verifier": {"feasible": main is not None, "number_coverage": 1.0, "paraphrase_objectives": others if main else []},
        "usage": _usage(sum(s["input_tokens"] for s in steps.values()), sum(s["calls"] for s in steps.values())),
        "usage_by_step": steps,
    }


def b2_record(problem_id: str, objectives: list, reference: float = 100.0, tokens: int = 100) -> dict:
    steps = {f"sample_{i}": _usage(tokens, 1) for i in range(1, len(objectives) + 1)}
    return {
        "problem_id": problem_id,
        "reference": reference,
        "attempts": [_solve(objectives[0])],
        "samples": [[_solve(objective)] for objective in objectives],
        "usage": _usage(tokens * len(objectives), len(objectives)),
        "usage_by_step": steps,
    }


def _outcome(score: float, correct: bool, answer: float | None = 1.0) -> dict:
    return {"score": score, "correct": correct, "answer": answer}


def test_wrong_accept_rate_without_ties():
    outcomes = [_outcome(0.9, True), _outcome(0.8, False), _outcome(0.5, False), _outcome(0.1, True)]
    assert wrong_accept_at_coverage(outcomes, 0.5, 10, random.Random(0)) == {"wrong_accept_rate": 0.5, "coverage": 0.5}


def test_wrong_accept_rate_breaks_ties_at_random():
    # 4 problems, 2 accepted: one above the cut, then 1 of 3 tied problems (2 of them wrong).
    outcomes = [_outcome(0.9, True), _outcome(0.5, False), _outcome(0.5, False), _outcome(0.5, True)]
    exact = wrong_accept_at_coverage(outcomes, 0.5, 0, None)["wrong_accept_rate"]
    assert exact == pytest.approx((0 + 2 / 3) / 2)
    drawn = wrong_accept_at_coverage(outcomes, 0.5, 1000, random.Random(0))["wrong_accept_rate"]
    assert drawn == pytest.approx(exact, abs=0.03)
    assert drawn == wrong_accept_at_coverage(outcomes, 0.5, 1000, random.Random(0))["wrong_accept_rate"]


def test_problems_without_an_answer_are_never_accepted():
    outcomes = [_outcome(0.9, False), _outcome(0.0, False, answer=None), _outcome(0.0, False, answer=None), _outcome(0, False, None)]
    assert wrong_accept_at_coverage(outcomes, 0.5, 10, random.Random(0)) == {"wrong_accept_rate": 1.0, "coverage": 0.25}
    assert wrong_accept_at_coverage([_outcome(0, False, None)], 0.5, 10, random.Random(0))["wrong_accept_rate"] is None


def test_mcnemar_exact_p_value():
    assert mcnemar_p([True] * 5, [False] * 5) == pytest.approx(2 / 32)
    assert mcnemar_p([True, False], [False, True]) == 1.0
    assert mcnemar_p([True, True], [True, True]) == 1.0


def test_clopper_pearson_interval():
    assert clopper_pearson(0, 10)[0] == 0.0
    assert clopper_pearson(0, 10)[1] == pytest.approx(1 - 0.025 ** (1 / 10), abs=1e-6)
    low, high = clopper_pearson(5, 10)
    assert low == pytest.approx(0.1871, abs=1e-4) and high == pytest.approx(0.8129, abs=1e-4)


def test_percentile_interval_skips_missing_values():
    assert percentile_interval(list(range(101))) == [2, 98]
    assert percentile_interval([None, None]) is None


def test_pipeline_at_lower_k_drops_later_paraphrase_runs():
    record = pipeline_record("p", 100.0, [100.0, 200.0, 300.0])
    assert pipeline_at(record, 3) == {"answer": 100.0, "score": pytest.approx((1 + 1 / 3) / 2), "correct": True, "tokens": 450, "calls": 8}
    assert pipeline_at(record, 1) == {"answer": 100.0, "score": 1.0, "correct": True, "tokens": 350, "calls": 4}

    failed = pipeline_record("f", None, [])
    assert pipeline_at(failed, 1) == {"answer": None, "score": 0.0, "correct": False, "tokens": 300, "calls": 2}


def test_records_without_steps_or_runs_are_refused():
    old = pipeline_record("p", 100.0, [100.0, 100.0, 100.0])
    del old["usage_by_step"]
    assert pipeline_at(old, 3)["tokens"] == 450  # nothing to drop at the recorded k
    with pytest.raises(ValueError, match="usage_by_step"):
        pipeline_at(old, 1)
    with pytest.raises(ValueError, match="fewer than k"):
        pipeline_at(pipeline_record("p", 100.0, [100.0, 100.0]), 3)


def test_b2_at_budget_keeps_the_first_samples():
    record = b2_record("b", [100.0, 200.0, 200.0, 100.0, 100.0])
    assert b2_at(record, 300) == {"answer": 200.0, "score": 2 / 3, "correct": False, "tokens": 300, "calls": 3, "samples": 3}
    assert b2_at(record, 500)["answer"] == 100.0


def test_baseline_points_read_b0_from_the_first_attempt():
    record = {
        "reference": 100.0,
        "attempts": [_solve(None), _solve(100.0)],
        "usage": _usage(300, 2),
        "usage_by_step": {"formalize": _usage(200, 1), "repair": _usage(100, 1)},
    }
    points = baseline_points(record)
    assert points["B0"] == {"answer": None, "correct": False, "tokens": 200, "calls": 1}
    assert points["B1"] == {"answer": 100.0, "correct": True, "tokens": 300, "calls": 2}


def _synthetic_runs() -> tuple[dict, dict]:
    """20 problems. The pipeline flags its wrong models by disagreement; B2's wrong samples agree with each other.
    B2 samples cost 90 tokens, so 5 samples match the k = 3 budget of 450 exactly."""
    pipeline, b2 = {}, {}
    for n in range(20):
        problem_id = f"q{n:02d}"
        wrong = n % 4 == 0
        main = 150.0 if wrong else 100.0
        pipeline[problem_id] = pipeline_record(problem_id, main, [100.0] * 3)
        b2[problem_id] = b2_record(
            problem_id, [150.0] * 8 if wrong else [100.0, 100.0, 120.0, 100.0, 100.0, 100.0, 100.0, 100.0], tokens=90
        )
    return pipeline, b2


def test_analysis_is_repeatable_and_tests_h3_at_k3():
    pipeline, b2 = _synthetic_runs()
    first = analyze(pipeline, b2, bootstrap=200)
    assert first == analyze(pipeline, b2, bootstrap=200)  # fixed seeds give the same numbers

    assert [level["k"] for level in first["levels"]] == [1, 2, 3]
    assert [level["budget_tokens"] for level in first["levels"]] == [350, 400, 450]
    top = first["levels"][-1]
    assert top["pipeline"]["wrong_accept_rate"] == 0.0
    assert top["b2"]["wrong_accept_rate"] > 0.0
    assert top["b2"]["within_budget_tolerance"]
    assert first["h3"]["supported"]


def test_analysis_flags_a_b2_budget_mismatch_and_adds_reference_points():
    pipeline, b2 = _synthetic_runs()
    short = {problem_id: b2_record(problem_id, [100.0], tokens=100) for problem_id in b2}  # 100 tokens, budget 450
    result = analyze(pipeline, short, baseline={"q00": {"reference": 100.0, "attempts": [_solve(100.0)], "usage": _usage(200, 1)}}, bootstrap=50)
    assert not result["levels"][-1]["b2"]["within_budget_tolerance"]
    assert result["reference_points"]["B0"]["accuracy"] == 1.0
