import json
from pathlib import Path

import pytest

from scripts.efficiency import (
    PRICES,
    configuration,
    cost_usd,
    efficiency,
    load_run,
    run_metrics,
    solver_calls,
    tokens_by_step,
    write_tables,
)

RESULTS = Path(__file__).resolve().parent.parent / "results"


def _usage(tokens: int, calls: int) -> dict:
    return {"input_tokens": tokens, "output_tokens": 0, "calls": calls}


def _attempt(status: str) -> dict:
    return {"solve": {"status": status, "objective": 1.0 if status == "optimal" else None}}


def _baseline(problem_id: str, statuses: list[str], model: str = "openai.gpt-oss-120b-1:0") -> dict:
    return {
        "problem_id": problem_id,
        "system": "baseline_r1",
        "model": model,
        "attempts": [_attempt(status) for status in statuses],
        "usage": _usage(100 * len(statuses), len(statuses)),
        "usage_by_step": {"formalize": _usage(100, 1), "repair": _usage(100 * (len(statuses) - 1), len(statuses) - 1)},
        "latency_s": 2.0,
    }


def _run(name: str, records: list[dict], failed: list[str] = (), sample_file: str = "samples/canonical_100.json") -> dict:
    config = {
        "endpoint": "bedrock us-east-1",
        "sample_file": sample_file,
        "system": "baseline",
        "repairs": 1,
        "model": "bedrock:openai.gpt-oss-120b-1:0",
    }
    return {"name": name, "summary": {"config": config, "failed_problems": list(failed)}, "records": records}


def test_solver_calls_per_system():
    assert solver_calls(_baseline("a", ["error", "optimal"])) == 2

    pipeline = {
        "attempts": [_attempt("optimal")],
        "verifier": {"paraphrase_objectives": [1.0, 1.0]},
        "usage_by_step": {"parse": _usage(1, 1), "formalize": _usage(1, 1), "paraphrase_1": _usage(4, 4), "paraphrase_2": _usage(2, 2)},
    }
    assert solver_calls(pipeline) == 1 + 2 + 1  # paraphrase_1 was retried once
    old_pipeline = {"attempts": [_attempt("optimal")], "verifier": {"paraphrase_objectives": [1.0, None]}}
    assert solver_calls(old_pipeline) == 3  # no steps saved: one try per reworded run

    b2 = {
        "attempts": [_attempt("optimal")],
        "samples": [[_attempt("optimal")], [_attempt("error"), _attempt("optimal")], [_attempt("optimal")]],
        "samples_used": 2,
        "verifier": None,
    }
    assert solver_calls(b2) == 3  # the third sample was drawn but not used


def test_cost_uses_the_price_of_the_run_model():
    gpt = PRICES["openai.gpt-oss-120b-1:0"]
    assert cost_usd(1_000_000, 1_000_000, gpt) == pytest.approx(0.15 + 0.60)
    assert cost_usd(902, 1819, gpt) == pytest.approx(0.0012267)  # 902 x 0.15 + 1,819 x 0.60 = 1,226.7 per million
    assert run_metrics(_run("r", [_baseline("a", ["optimal"])]))["mean_cost_usd"] == pytest.approx(100 * 0.15 / 1e6)


def test_a_model_without_a_price_gets_no_cost(tmp_path):
    run = _run("ds", [_baseline("a", ["optimal"], model="deepseek.v3.2")])
    assert run_metrics(run)["mean_cost_usd"] is None  # never another model's price
    result = efficiency([run])
    assert result["configurations"][0]["price"] is None
    write_tables(result, tmp_path)
    row = (tmp_path / "efficiency.csv").read_text(encoding="utf-8").splitlines()[1]
    assert row.endswith(",,,")  # price input, output and date are empty

    priced = efficiency([_run("gpt", [_baseline("a", ["optimal"])])])["configurations"][0]
    assert priced["price"] == {"model": "openai.gpt-oss-120b-1:0", "input": 0.15, "output": 0.60, "date": "2026-10-20"}


def test_a_run_in_which_every_problem_failed():
    run = _run("all-failed", [], failed=["a", "b"])
    assert configuration(run).startswith("baseline_r1 | openai.gpt-oss-120b-1:0 | bedrock us-east-1")
    metrics = run_metrics(run)
    assert metrics["failed_run_rate"] == 1.0 and metrics["problems"] == 0
    assert metrics["mean_input_tokens"] is None and metrics["mean_cost_usd"] is None  # no usage is saved
    assert metrics["solver_error_rate"] is None and metrics["tokens_by_step"] is None
    group = efficiency([run])["configurations"][0]
    assert not group["meets_failed_run_target"]
    empty_attempts = dict(_baseline("c", ["optimal"]), attempts=[])
    assert run_metrics(_run("r", [empty_attempts]))["repair_success_rate"] is None  # no crash on empty attempts


def test_the_mean_over_repeats_skips_repeats_without_the_measure():
    nothing_to_repair = _run("one", [_baseline("a", ["optimal"]), _baseline("b", ["optimal"])])
    repaired = _run("two", [_baseline("a", ["error", "optimal"]), _baseline("b", ["optimal"])])
    group = efficiency([nothing_to_repair, repaired])["configurations"][0]
    assert group["metrics"]["repair_success_rate"] == {"mean": 1.0, "sd": None, "repeats_with_value": 1}
    assert group["metrics"]["mean_llm_calls"]["repeats_with_value"] == 2


def test_reliability_rates():
    records = [
        _baseline("a", ["optimal"]),
        _baseline("b", ["error", "optimal"]),  # repaired
        _baseline("c", ["timeout", "error"]),  # repair failed
    ]
    metrics = run_metrics(_run("r", records, failed=["d"]))
    assert metrics["failed_run_rate"] == pytest.approx(1 / 4)
    assert metrics["solver_error_rate"] == pytest.approx(2 / 5)
    assert metrics["solver_timeout_rate"] == pytest.approx(1 / 5)
    assert metrics["repair_success_rate"] == pytest.approx(1 / 2)
    assert metrics["mean_solver_calls"] == pytest.approx(5 / 3)
    assert run_metrics(_run("r", [_baseline("a", ["optimal"])]))["repair_success_rate"] is None  # nothing to repair


def test_b2_tokens_by_step_leave_out_unused_samples():
    record = {
        "samples": [[], [], []],
        "samples_used": 2,
        "usage_by_step": {"sample_1": _usage(100, 1), "sample_2": _usage(50, 1), "sample_3": _usage(70, 1)},
    }
    assert tokens_by_step([record]) == {"sample_1": 100, "sample_2": 50}
    assert tokens_by_step([{"usage_by_step": {}}]) is None  # records saved before Phase 2


def test_repeats_are_grouped_only_on_the_same_configuration_and_problems(tmp_path):
    one = _run("one", [_baseline("a", ["optimal"]), _baseline("b", ["optimal"])])
    two = _run("two", [_baseline("a", ["error", "optimal"]), _baseline("b", ["optimal"])])
    other_problems = _run("three", [_baseline("a", ["optimal"])])
    assert configuration(one) == configuration(two) != configuration(other_problems)

    result = efficiency([one, two, other_problems])
    assert len(result["configurations"]) == 2
    group = next(g for g in result["configurations"] if g["runs"] == ["one", "two"])
    calls = group["metrics"]["mean_llm_calls"]
    assert calls == {"mean": 1.25, "sd": pytest.approx(0.3535534, abs=1e-6), "repeats_with_value": 2}
    assert group["meets_failed_run_target"]
    assert group["price"]["date"] == "2026-10-20"

    write_tables(result, tmp_path)
    assert (tmp_path / "efficiency.csv").read_text(encoding="utf-8").startswith("configuration,repeats")
    assert "formalize" in (tmp_path / "tokens_by_step.csv").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "efficiency.json").read_text(encoding="utf-8"))["failed_run_target"] == 0.05


def test_bedrock_b1_run_matches_its_own_summary():
    folder = next(RESULTS.glob("baseline_bedrock*_canonical_100_r1_*"))
    run = load_run(folder)
    metrics = run_metrics(run)
    summary = run["summary"]
    for name in ("mean_input_tokens", "mean_output_tokens", "mean_llm_calls", "mean_latency_s"):
        assert metrics[name] == pytest.approx(summary[name])
    assert metrics["failed_run_rate"] == 0.0 and metrics["problems"] == 100
    steps = metrics["tokens_by_step"]
    assert sum(steps.values()) == pytest.approx(summary["mean_input_tokens"] + summary["mean_output_tokens"])
