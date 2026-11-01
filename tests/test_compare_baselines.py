import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.analyze_e3 import load_records
from scripts.compare_baselines import (
    REPORTED,
    compare,
    compare_models,
    compare_repeats,
    markdown_table,
    mean_and_sd,
    outcomes,
    write_repeat_tables,
)

RESULTS = Path(__file__).resolve().parent.parent / "results"


def _attempt(status: str, objective: float | None) -> dict:
    return {"solve": {"status": status, "objective": objective}}


def _record(
    problem_id: str,
    problem_class: str,
    attempts: list,
    reference: float = 1000.0,
    model: str = "openai.gpt-oss-120b-1:0",
    system: str = "baseline_r1",
) -> dict:
    steps = {"formalize": {"input_tokens": 100, "output_tokens": 0, "calls": 1}}
    steps["repair"] = {"input_tokens": 50 * (len(attempts) - 1), "output_tokens": 0, "calls": len(attempts) - 1}
    return {
        "problem_id": problem_id,
        "model": model,
        "system": system,
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


def _repeat(tsp_answers: list, model: str = "openai.gpt-oss-120b-1:0", system: str = "baseline_r1") -> dict:
    records = {}
    for i, answer in enumerate(tsp_answers):
        attempts = answer if isinstance(answer, list) else [_attempt("optimal", answer)]
        records[f"t{i}"] = _record(f"t{i}", "TSP", attempts, model=model, system=system)
    return records


def test_repeats_give_mean_and_sd_with_labelled_columns(tmp_path):
    repeats = [_repeat([1000.0, 1000.0]), _repeat([1000.0, 900.0]), _repeat([1001.5, 900.0])]  # 1001.5: 0.2% only
    result = compare_models(repeats, {"TSP": {"sir_accuracy": 0.8, "source": "Table 2"}})
    (block,) = result["models"]
    tsp = block["classes"]["TSP"]
    assert block["label"] == "reproduced (openai.gpt-oss-120b-1:0, our runs)"
    assert block["repeats"] == 3 and len(block["runs"]) == 3 and block["with_repair"]
    assert tsp["B0"]["accuracy"]["mean"] == pytest.approx(2 / 3)  # 100%, 50%, 50%
    assert tsp["B0"]["accuracy"]["sd"] == pytest.approx(0.2886751, abs=1e-6)
    assert tsp["B0"]["accuracy_strict"]["mean"] == pytest.approx(0.5)  # 100%, 50%, 0%
    assert tsp["reported"] == {"accuracy": 0.8, "source": "Table 2"}
    assert tsp["b0_strict_minus_reported"] == pytest.approx(0.5 - 0.8)

    write_repeat_tables(result, tmp_path)
    table = (tmp_path / "e1_e2.md").read_text(encoding="utf-8")
    assert block["label"] in table and REPORTED in table and "66.7% ± 28.9%" in table
    assert "sample standard deviation (n - 1)" in table and "no standard deviation" in table
    header = (tmp_path / "e1_e2.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header.startswith("model,repeats,class,problems") and "(mean)" in header and "(sd)" in header
    assert json.loads((tmp_path / "e1_e2.json").read_text(encoding="utf-8"))["models"][0]["repeats"] == 3


def test_repeats_are_grouped_by_model_and_a_b0_only_block_works(tmp_path):
    gpt = [_repeat([1000.0, 900.0]), _repeat([1000.0, 1000.0])]
    deepseek = [_repeat([1000.0, 1000.0], model="deepseek.v3.2", system="baseline_r0")]
    result = compare_models(gpt + deepseek)
    blocks = {block["model"]: block for block in result["models"]}
    assert set(blocks) == {"openai.gpt-oss-120b-1:0", "deepseek.v3.2"}
    assert blocks["openai.gpt-oss-120b-1:0"]["repeats"] == 2
    ds = blocks["deepseek.v3.2"]
    assert ds["label"] == "reproduced (deepseek.v3.2, our runs)" and not ds["with_repair"]
    assert ds["overall"]["B0"]["accuracy"] == {"mean": 1.0, "sd": None}
    assert ds["overall"]["B1"]["accuracy"] == {"mean": None, "sd": None}  # B0 only: no B1
    assert ds["overall"]["repair"]["fixed"] == {"mean": None, "sd": None}

    write_repeat_tables(result, tmp_path)
    table = (tmp_path / "e1_e2.md").read_text(encoding="utf-8")
    assert "### reproduced (deepseek.v3.2, our runs): 1 repeat(s), B0 only (no repair round)" in table
    rows = (tmp_path / "e1_e2.csv").read_text(encoding="utf-8").splitlines()
    assert sum(row.startswith("deepseek.v3.2,") for row in rows) == 2  # TSP and all classes


def test_tables_show_silent_failures_and_repair_counts(tmp_path):
    repeats = [
        _repeat([[_attempt("error", None), _attempt("optimal", 1000.0)], 900.0]),  # 1 fixed, 1 silent failure
        _repeat([[_attempt("error", None), _attempt("optimal", 1000.0)], 1000.0]),  # 1 fixed
    ]
    result = compare_models(repeats)
    overall = result["models"][0]["overall"]
    assert overall["repair"]["fixed"]["mean"] == 1 and overall["repair"]["broken"]["mean"] == 0
    assert overall["B1"]["silent_failures"] == {"mean": 0.5, "sd": pytest.approx(0.7071068, abs=1e-6)}
    write_repeat_tables(result, tmp_path)
    table = (tmp_path / "e1_e2.md").read_text(encoding="utf-8")
    assert "B1 silent failures" in table and "Fixed by repair" in table and "0.5 ± 0.7" in table


def test_repeats_must_cover_the_same_problems_and_settings():
    with pytest.raises(ValueError, match="same problems; for example t1"):
        compare_repeats([_repeat([1000.0, 1000.0]), _repeat([1000.0])])
    with pytest.raises(ValueError, match="mix settings"):
        compare_repeats([_repeat([1000.0]), _repeat([1000.0], system="baseline_r0")])


def test_mismatched_repeats_give_a_clean_command_line_error(tmp_path):
    paths = []
    for name, answers in (("a", [1000.0, 1000.0]), ("b", [1000.0])):
        path = tmp_path / f"{name}.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in _repeat(answers).values()), encoding="utf-8")
        paths.append(str(path))
    script = Path(__file__).resolve().parent.parent / "scripts" / "compare_baselines.py"
    done = subprocess.run(
        [sys.executable, str(script), "--repeat", paths[0], "--repeat", paths[1]], capture_output=True, text=True
    )
    assert done.returncode == 2  # argparse error, not a traceback
    assert "same problems; for example t1" in done.stderr and "Traceback" not in done.stderr


def test_one_repeat_of_the_bedrock_run_matches_the_single_run_numbers():
    path = str(next(RESULTS.glob("baseline_bedrock*_canonical_100_r1_*/records.jsonl")))
    overall = compare_repeats([load_records([path])])["overall"]
    assert overall["B0"]["accuracy"] == {"mean": pytest.approx(0.78), "sd": None}  # as in PR #15
    assert overall["B1"]["accuracy"]["mean"] == pytest.approx(0.80)
    assert overall["repair"]["fixed"]["mean"] == 2 and overall["repair"]["broken"]["mean"] == 0
    assert overall["B0"]["silent_failures"]["mean"] == 19 and overall["B1"]["silent_failures"]["mean"] == 20
