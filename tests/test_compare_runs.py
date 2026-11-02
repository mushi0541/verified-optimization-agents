"""scripts/compare_runs.py: paired counts per class, for pipeline runs and for runs with no verifier (B0, B1)."""

from scripts.compare_runs import compare


def _record(problem_id, problem_class, correct, verifier=None, tokens=100):
    return {"problem_id": problem_id, "problem_class": problem_class, "correct": correct, "verifier": verifier,
            "usage": {"input_tokens": tokens, "output_tokens": 0}}


def _verifier(score, feasible=True):
    return {"feasible": feasible, "score": score}


def test_pipeline_runs_are_paired_and_counted_at_the_threshold():
    first = [_record("a", "TSP", True, _verifier(0.9)), _record("b", "TSP", False, _verifier(0.85)),
             _record("c", "Inventory", False, _verifier(0.0, feasible=False))]
    second = [_record("a", "TSP", True, _verifier(0.9)), _record("b", "TSP", True, _verifier(0.5)),
              _record("c", "Inventory", False, _verifier(0.9)), _record("d", "TSP", True, _verifier(1.0))]
    result = compare(first, second, threshold=0.8)
    assert result["shared_problems"] == 3 and result["only_in_second"] == ["d"]
    overall = result["groups"]["all"]
    assert overall["first"] == {"problems": 3, "correct": 1, "no_feasible_model": 1, "accepted": 2,
                                "wrong_accepted": 1, "mean_tokens": 100.0}
    assert (overall["second"]["accepted"], overall["second"]["wrong_accepted"]) == (2, 1)
    assert (overall["only_first_correct"], overall["only_second_correct"]) == (0, 1)
    assert list(result["groups"]) == ["Inventory", "TSP", "all"]


def test_runs_without_a_verifier_have_no_acceptance_counts():
    first = [_record("a", "JobShop", False), _record("b", "JobShop", True)]
    second = [_record("a", "JobShop", True), _record("b", "JobShop", True)]
    overall = compare(first, second, threshold=0.8)["groups"]["all"]
    assert overall["first"]["accepted"] is None and overall["first"]["no_feasible_model"] is None
    assert (overall["first"]["correct"], overall["second"]["correct"]) == (1, 2)
