"""Tests for the Gap 2 (H2) analysis on small hand-made records."""

import pytest

from scripts.analyze_gap2 import analyze_run, b0_reference, h2_check, risk_coverage, summarize


def _record(pid: str, problem_class: str, score: float, correct: bool, feasible: bool = True) -> dict:
    return {"problem_id": pid, "problem_class": problem_class, "system": "pipeline_p3", "correct": correct,
            "verifier": {"feasible": feasible, "score": score}}


def _canonical(per_class: int) -> list[dict]:
    """Ten classes; in each, problem 0 is a low-score wrong answer and problem 9 a confident wrong answer.

    With 20 per class each fold calibrates on 171 answers at score 1.0 with 9 wrong (exact bound 0.090), so alpha = 10%
    is met at threshold 1.0, and 0.5 is not (18 wrong of 180, bound 0.145).
    """
    records = []
    for c in range(10):
        for i in range(per_class):
            pid = f"c{c}-{i}"
            if i == 0:
                records.append(_record(pid, f"Class{c}", 0.5, False))
            elif i == 9:
                records.append(_record(pid, f"Class{c}", 1.0, False))
            else:
                records.append(_record(pid, f"Class{c}", 1.0, True))
    return records


def test_risk_coverage_moves_from_strict_to_lenient():
    records = [_record("a", "A", 1.0, True), _record("b", "A", 0.9, False), _record("c", "A", 0.5, True),
               _record("d", "A", 0.0, False, feasible=False), {"problem_id": "e", "failed": "timeout"}]
    points = risk_coverage(records)
    assert [p["threshold"] for p in points] == [1.0, 0.9, 0.5]
    assert [p["coverage"] for p in points] == [0.25, 0.5, 0.75]  # over the 4 finished problems
    assert [p["wrong_accept_rate"] for p in points] == [0.0, 0.5, pytest.approx(1 / 3)]


def test_twenty_per_class_narrows_the_interval_against_ten():
    records = _canonical(20)
    subset = {r["problem_id"] for r in records if int(r["problem_id"].split("-")[1]) < 10}
    run = analyze_run(records, [0.10], 0.8, subset)
    test = run["by_alpha"]["0.1"]["test"]
    assert [fold["threshold"] for fold in test["folds"]] == [1.0] * 10
    assert test["problems"] == 200 and test["pooled"]["answered"] == 190  # each held-out class answers its 1.0 scores
    assert test["pooled"]["wrong_accepted"] == 10 and test["pooled"]["wrong_accept_rate"] == pytest.approx(10 / 190)
    # With the first 10 per class, each fold has 81 answers with 9 wrong: no threshold meets 10%, nothing is answered.
    assert run["by_alpha"]["0.1"]["subset"]["pooled"]["answered"] == 0
    width = run["by_alpha"]["0.1"]["interval_width"]
    assert width["all"] < width["subset"] == 1.0
    assert run["fixed"]["answered"] == 190 and run["fixed"]["wrong_accepted"] == 10


def test_h2_needs_the_rate_and_half_of_the_problems_answered():
    def test_with(rate, coverage, upper):
        return {"alpha": 0.10, "pooled": {"wrong_accept_rate": rate, "coverage": coverage, "exact_interval": [0.0, upper]}}

    assert h2_check(test_with(0.05, 0.9, 0.08)) == {"rate_ok": True, "coverage_ok": True, "upper_bound_ok": True, "supported": True}
    assert not h2_check(test_with(0.05, 0.4, 0.08))["supported"]  # too few answered
    assert not h2_check(test_with(0.12, 0.9, 0.2))["supported"]
    assert not h2_check(test_with(None, 0.0, 1.0))["supported"]  # nothing answered

    run = analyze_run(_canonical(20), [0.10], 0.8, None)
    summary = summarize([run, run], [0.10])
    assert summary["h2"].startswith("supported")
    assert summary["by_alpha"]["0.1"]["coverage"]["mean"] == pytest.approx(0.95)
    only_five = analyze_run(_canonical(20), [0.05], 0.8, None)
    assert summarize([only_five], [0.05])["h2"].startswith("not tested")


def test_b0_answers_whenever_its_first_model_is_optimal():
    baseline = [
        {"problem_id": "a", "reference": 5.0, "attempts": [{"solve": {"status": "optimal", "objective": 5.0}}]},
        {"problem_id": "b", "reference": 5.0, "attempts": [{"solve": {"status": "optimal", "objective": 7.0}}]},
        {"problem_id": "c", "reference": 5.0, "attempts": [{"solve": {"status": "error", "objective": None}}]},
    ]
    b0 = b0_reference(baseline, {"a", "b", "c", "z"})
    assert (b0["problems"], b0["answered"], b0["wrong_accepted"], b0["wrong_accept_rate"]) == (3, 2, 1, 0.5)
