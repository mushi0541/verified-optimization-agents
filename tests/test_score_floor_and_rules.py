"""Tests for the score floor and the exploratory threshold rules (#36), on small hand-made records."""

from scripts.score_floor import floor
from scripts.threshold_rules import compare, nested_strictest, pooled_rate, worst_class


def _record(pid: str, problem_class: str, score: float, correct: bool) -> dict:
    return {"problem_id": pid, "problem_class": problem_class, "correct": correct,
            "verifier": {"feasible": True, "score": score}}


def test_the_floor_counts_wrong_answers_at_the_top_score_only():
    records = [_record("a", "A", 1.0, True), _record("b", "A", 1.0, False), _record("c", "A", 0.5, False),
               _record("d", "Pollution", 1.0, False), {"problem_id": "e", "problem_class": "A", "failed": True}]
    result = floor(records)
    assert result["top_score"] == 1.0
    assert result["by_class"]["A"] == {"answers": 2, "wrong": 1}  # the 0.5 answer is below the top score
    assert (result["all"]["wrong"], result["all"]["answers"]) == (2, 3)
    assert (result["without_pollution"]["wrong"], result["without_pollution"]["answers"]) == (1, 2)


def test_worst_class_stops_at_the_first_class_above_alpha():
    clean = [_record(f"a{i}", "A", 1.0, True) for i in range(10)]
    noisy = [_record(f"b{i}", "B", 0.9, i < 3) for i in range(6)]  # 3 of 6 wrong at 0.9
    assert worst_class(clean + noisy, 0.10) == 1.0  # class B alone is 50% wrong at 0.9, so 0.9 is refused
    more_clean = [_record(f"c{i}", "A", 1.0, True) for i in range(30)]
    assert pooled_rate(more_clean + noisy, 0.10) == 0.9  # pooled, 3 wrong of 36 is 8.3%, so 0.9 is allowed


def test_nested_strictest_has_no_threshold_when_an_inner_fold_has_none():
    records = [_record(f"{c}{i}", c, 1.0, True) for c in "AB" for i in range(40)]
    assert nested_strictest(records, 0.10) == 1.0
    records += [_record(f"C{i}", "C", 1.0, i % 2 == 0) for i in range(40)]  # half wrong at the top score
    assert nested_strictest(records, 0.10) is None


def test_compare_pools_the_held_out_folds():
    records = [_record(f"{c}{i}", c, 1.0, True) for c in "ABC" for i in range(40)]
    rows = {(r["rule"], r["alpha"]): r for r in compare(records, alphas=(0.10,))}
    assert rows[("R3 pooled rate", 0.10)]["answered"] == 120
    assert rows[("R3 pooled rate", 0.10)]["wrong_accept_rate"] == 0.0
