import json
from pathlib import Path

import pytest

from scripts.analyze_e3 import load_records
from scripts.compare_baselines import (
    REPORTED,
    REPRODUCED,
    compare,
    compare_repeats,
    markdown_table,
    mean_and_sd,
    outcomes,
    write_repeat_tables,
)

RESULTS = Path(__file__).resolve().parent.parent / "results"


def _attempt(status: str, objective: float | None) -> dict:
    return {"solve": {"status": status, "objective": objective}}


def _record(problem_id: str, problem_class: str, attempts: list, reference: float = 1000.0) -> dict:
    steps = {"formalize": {"input_tokens": 100, "output_tokens": 0, "calls": 1}}
    steps["repair"] = {"input_tokens": 50 * (len(attempts) - 1), "output_tokens": 0, "calls": len(attempts) - 1}
    return {
        "problem_id": problem_id,
        "problem_class": problem_class,
        "reference": reference,
        "attempts": attempts,
        "usage": {"input_tokens": 100 + 50 * (len(attempts) - 1), "output_tokens": 0, "calls": len(attempts)},
        "usage_by_step": steps,
    }


def test_outcomes_grade_b0_and_b1_at_both_tolerances():
    record = _record("p", "TSP", [_attempt("error", None), _attempt("optimal", 1001.5)])  # 0.15% off
    graded = outcomes(record)
    assert graded["B0"] == {"correct": False, "correct_strict": False, "solved": False, "tokens": 100, "calls": 1}
    assert graded["B1"] == {"correct": True, "correct_strict": False, "solved": True, "tokens": 150, "calls": 2}


def test_compare_counts_repairs_and_silent_failures():
    records = {
        "a": _record("a", "TSP", [_attempt("error", None), _attempt("optimal", 1000.0)]),  # fixed by repair
        "b": _record("b", "TSP", [_attempt("optimal", 900.0)]),  # silent failure in B0 and B1
        "c": _record("c", "Knapsack", [_attempt("optimal", 1000.0)]),
    }
    result = compare(records)
    tsp = result["classes"]["TSP"]
    assert tsp["problems"] == 2
    assert tsp["B0"]["accuracy"] == 0.0 and tsp["B1"]["accuracy"] == 0.5
    assert tsp["B0"]["silent_failures"] == 1 and tsp["B1"]["silent_failures"] == 1
    assert tsp["repair"] == {"fixed": 1, "broken": 0, "mcnemar_p": 1.0}
    assert result["overall"]["B1"]["accuracy"] == pytest.approx(2 / 3)
    assert result["overall"]["B0"]["mean_tokens"] == 100 and result["overall"]["B1"]["mean_calls"] == pytest.approx(4 / 3)
    assert "| All classes | 3 |" in markdown_table(result)


def test_paper_values_are_compared_at_the_strict_rule():
    records = {"a": _record("a", "TSP", [_attempt("optimal", 1001.5)])}  # correct at 0.2%, wrong at 0.1%
    result = compare(records, {"TSP": {"sir_accuracy": 0.8, "source": "Table 2"}})
    assert result["classes"]["TSP"]["paper_sir"] == {"accuracy": 0.8, "source": "Table 2", "b0_minus_paper": -0.8}
    with pytest.raises(ValueError, match="not in the records"):
        compare(records, {"Travelling Salesman": {"sir_accuracy": 0.8}})


def test_phase1_records_give_the_report_numbers():
    run_a = compare(load_records([str(next(RESULTS.glob("baseline_bedrock*_r0_20261020-1634/records.jsonl")))]))
    run_b = compare(load_records([str(next(RESULTS.glob("baseline_bedrock*_20261020-1340/records.jsonl")))]))
    assert run_a["overall"]["B0"]["accuracy"] == pytest.approx(20 / 30)  # 66.7% in report Table 10
    assert run_b["overall"]["B0"]["accuracy"] == pytest.approx(0.8)  # 80.0%
    solved = run_a["overall"]["B0"]["solved_rate"] * 30 + run_b["overall"]["B0"]["solved_rate"] * 10
    silent = run_a["overall"]["B0"]["silent_failures"] + run_b["overall"]["B0"]["silent_failures"]
    assert (round(solved), silent) == (39, 11)  # "11 of the 39 runs that reached an optimal solver status"


def test_paper_values_file_uses_the_data_class_names():
    paper = json.loads((RESULTS.parent / "docs" / "paper_sir.json").read_text(encoding="utf-8"))
    run_b = compare(load_records([str(next(RESULTS.glob("baseline_bedrock*_20261020-1340/records.jsonl")))]), paper)  # all 10 classes
    compared = sorted(name for name, summary in run_b["classes"].items() if "paper_sir" in summary)
    assert compared == ["Knapsack", "NetworkFlow", "TSP"]  # the only classes with SIR values in a table of the paper


def test_mean_and_sd_over_repeats():
    result = mean_and_sd([0.7, 0.8, 0.9])
    assert result["mean"] == pytest.approx(0.8) and result["sd"] == pytest.approx(0.1)
    assert mean_and_sd([0.8]) == {"mean": 0.8, "sd": None}  # a deviation needs two repeats
    assert mean_and_sd([None, 100]) == {"mean": None, "sd": None}  # an unknown cost stays unknown


def _repeat(tsp_answers: list) -> dict:
    return {f"t{i}": _record(f"t{i}", "TSP", [_attempt("optimal", answer)]) for i, answer in enumerate(tsp_answers)}


def test_repeats_give_mean_and_sd_with_labelled_columns(tmp_path):
    repeats = [_repeat([1000.0, 1000.0]), _repeat([1000.0, 900.0]), _repeat([1001.5, 900.0])]  # 1001.5: 0.2% only
    result = compare_repeats(repeats, {"TSP": {"sir_accuracy": 0.8, "source": "Table 2"}})
    tsp = result["classes"]["TSP"]
    assert result["repeats"] == 3 and len(result["runs"]) == 3
    assert tsp["B0"]["accuracy"]["mean"] == pytest.approx(2 / 3)  # 100%, 50%, 50%
    assert tsp["B0"]["accuracy"]["sd"] == pytest.approx(0.2886751, abs=1e-6)
    assert tsp["B0"]["accuracy_strict"]["mean"] == pytest.approx(0.5)  # 100%, 50%, 0%
    assert tsp["reported"] == {"accuracy": 0.8, "source": "Table 2"}
    assert tsp["b0_strict_minus_reported"] == pytest.approx(0.5 - 0.8)

    write_repeat_tables(result, tmp_path)
    table = (tmp_path / "e1_e2.md").read_text(encoding="utf-8")
    assert REPRODUCED in table and REPORTED in table and "66.7% ± 28.9%" in table
    header = (tmp_path / "e1_e2.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "(mean)" in header and "(sd)" in header
    assert json.loads((tmp_path / "e1_e2.json").read_text(encoding="utf-8"))["repeats"] == 3


def test_repeats_must_cover_the_same_problems():
    with pytest.raises(ValueError, match="same problems"):
        compare_repeats([_repeat([1000.0, 1000.0]), _repeat([1000.0])])


def test_one_repeat_of_the_bedrock_run_matches_the_single_run_numbers():
    path = str(next(RESULTS.glob("baseline_bedrock*_canonical_100_r1_*/records.jsonl")))
    overall = compare_repeats([load_records([path])])["overall"]
    assert overall["B0"]["accuracy"] == {"mean": pytest.approx(0.78), "sd": None}  # as in PR #15
    assert overall["B1"]["accuracy"]["mean"] == pytest.approx(0.80)
    assert overall["repair"]["fixed"]["mean"] == 2 and overall["repair"]["broken"]["mean"] == 0
