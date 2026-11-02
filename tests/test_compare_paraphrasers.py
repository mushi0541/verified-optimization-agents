"""Tests for the paraphrase model comparison (#56) on small hand-made records."""

from scripts.compare_paraphrasers import shared_answers


def _record(pid: str, predicted: float, correct: bool, agreement: float, feasible: bool = True) -> dict:
    return {"problem_id": pid, "problem_class": "A", "predicted": predicted, "correct": correct,
            "verifier": {"feasible": feasible, "paraphrase_agreement": agreement, "score": agreement}}


def test_shared_answers_find_misreadings_only_one_paraphraser_catches():
    same = [_record("a", 10, False, 1.0), _record("b", 20, False, 0.333), _record("c", 30, True, 1.0),
            _record("d", 40, False, 1.0), _record("e", 50, True, 1.0), {"problem_id": "f", "failed": True}]
    other = [_record("a", 10, False, 0.333), _record("b", 20, False, 1.0), _record("c", 30, True, 0.667),
             _record("d", 41, False, 1.0), _record("e", 50, True, 1.0, feasible=False), _record("f", 1, True, 1.0)]
    result = shared_answers(same, other)
    # d differs in its answer, e is infeasible in one run and f failed in one run, so only a, b and c are shared.
    assert (result["shared"], result["wrong"], result["correct"]) == (3, 2, 1)
    assert result["caught_only_by_other"] == ["a"]
    assert result["caught_only_by_same"] == ["b"]
    assert (result["correct_full_agreement_same"], result["correct_full_agreement_other"]) == (1, 0)
