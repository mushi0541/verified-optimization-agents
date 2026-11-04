import pytest

from scripts.explore_combination import by_class


def outcome(correct: bool, score: float) -> dict:
    return {"answer": 1.0, "score": score, "correct": correct, "tokens": 100}


def test_by_class_splits_each_system_and_weights_every_class_equally():
    ids = ["a1", "a2", "b1", "b2", "b3", "b4"]
    classes = {"a1": "A", "a2": "A", "b1": "B", "b2": "B", "b3": "B", "b4": "B"}
    # Class A: 2 of 2 correct. Class B: 1 of 4 correct.
    systems = {"s": [outcome(True, 0.9), outcome(True, 0.8),
                     outcome(True, 0.9), outcome(False, 0.8), outcome(False, 0.7), outcome(False, 0.6)]}
    per_class, equal_weight = by_class(ids, classes, systems)
    assert per_class["A"]["problems"] == 2 and per_class["B"]["problems"] == 4
    assert per_class["A"]["systems"]["s"]["accuracy"] == 1.0
    assert per_class["B"]["systems"]["s"]["accuracy"] == 0.25
    # The pooled accuracy would be 3/6; with each class weighted equally it is (1 + 0.25) / 2.
    assert equal_weight["s"]["accuracy"] == pytest.approx(0.625)
    # At 50% coverage class A answers its 1 best (right) and class B its 2 best (one wrong): (0 + 0.5) / 2.
    assert equal_weight["s"]["wrong_accept_rate"]["0.5"] == pytest.approx(0.25)
