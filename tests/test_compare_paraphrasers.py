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



def test_a_shared_answer_without_agreement_is_shown_as_n_a():
    from scripts.compare_paraphrasers import markdown

    # Every reworded run of "a" failed in the first run, so it has no agreement value.
    shared = shared_answers([_record("a", 10, False, None)], [_record("a", 10, False, 1.0)])
    assert (shared["wrong_full_agreement_same"], shared["wrong_full_agreement_other"]) == (0, 1)
    run = {"problems": 1, "correct": 0, "paraphrase_auroc": 0.5, "combined_auroc": 0.5, "false_alarms": 0, "mean_tokens": 1.0}
    text = markdown({"records": {"same": "s", "other": "o"}, "same": run, "other": run, "shared": shared})
    assert "| a | A | n/a | 1.000 |" in text
