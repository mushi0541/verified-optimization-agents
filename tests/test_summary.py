import pytest

from optverify.grading import summarize


def _record(problem_class: str, correct: bool, status: str = "optimal", action: str | None = None) -> dict:
    record = {
        "problem_class": problem_class,
        "correct": correct,
        "attempts": [{"solve": {"status": status}}],
        "usage": {"input_tokens": 100, "output_tokens": 50, "calls": 2},
        "latency_s": 4.0,
    }
    if action:
        record["decision"] = {"action": action}
    return record


def test_summary_of_a_baseline_run():
    records = [_record("TSP", True), _record("TSP", False, "error"), _record("Knapsack", True)]
    summary = summarize(records)
    assert summary["problems"] == 3
    assert summary["accuracy"] == pytest.approx(2 / 3)
    assert summary["solved_rate"] == pytest.approx(2 / 3)
    assert summary["status_counts"] == {"error": 1, "optimal": 2}
    assert summary["mean_input_tokens"] == 100 and summary["mean_output_tokens"] == 50 and summary["mean_llm_calls"] == 2
    assert summary["accuracy_by_class"] == {"Knapsack": 1.0, "TSP": 0.5}
    assert "coverage" not in summary  # the baseline never decides, so there are no decision metrics


def test_summary_of_decisions():
    records = [
        _record("TSP", True, action="answer"),
        _record("TSP", False, action="answer"),
        _record("TSP", True, action="escalate"),
        _record("TSP", False, "error", action="abstain"),
    ]
    summary = summarize(records)
    assert summary["decision_counts"] == {"abstain": 1, "answer": 2, "escalate": 1}
    assert summary["coverage"] == 0.5
    assert summary["selective_accuracy"] == 0.5
    assert summary["wrong_accept_rate"] == 0.5


def test_summary_when_nothing_is_answered_or_run():
    summary = summarize([_record("TSP", False, action="escalate")])
    assert summary["coverage"] == 0.0
    assert summary["selective_accuracy"] is None and summary["wrong_accept_rate"] is None
    assert summarize([]) == {"problems": 0}
    assert summarize([{**_record("TSP", False), "attempts": []}])["status_counts"] == {"no_code": 1}
