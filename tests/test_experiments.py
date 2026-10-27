"""Offline tests for experiment runner, configurations, aggregation, and manifest."""

import json
import math
import statistics
from pathlib import Path

import pytest

import optverify.prompts
from experiments.aggregate import aggregate_experiment, extract_repeat_metrics, update_manifest
from experiments.prompt_version import get_git_commit, get_prompt_version
from experiments.run import load_experiment_config, run_experiment
from optverify.contracts import Problem
from tests.fake_llm import FakeLLM

REQUIRED_KEYS = {
    "name",
    "description",
    "system",
    "sample_file",
    "paraphrases",
    "repairs",
    "budget",
    "repeats",
    "notes",
}


def test_configs_load_and_have_required_keys():
    for exp_name in ["E1", "E2", "E3", "E4", "E5", "E6"]:
        cfg = load_experiment_config(exp_name)
        assert REQUIRED_KEYS.issubset(cfg.keys()), f"{exp_name} missing required keys"

    # Specific configuration assertions
    e1 = load_experiment_config("E1")
    assert e1["system"] == "baseline"
    assert e1["repairs"] == 1
    assert e1["repeats"] == 3

    e2 = load_experiment_config("E2")
    assert e2["system"] == "baseline"
    assert e2["repairs"] == 0
    assert e2["repeats"] == 3
    assert "reported" in e2
    assert e2["reported"]["TSP"]["sir_accuracy"] == 0.859
    assert e2["reported"]["Knapsack"]["sir_accuracy"] == 0.932
    assert e2["reported"]["NetworkFlow"]["sir_accuracy"] == 1.0

    e3 = load_experiment_config("E3")
    assert e3["system"] == "pipeline"
    assert e3["paraphrases"] == 3
    assert e3["repairs"] == 1
    assert e3["threshold"] == 0.8
    assert e3["repeats"] == 3

    e4 = load_experiment_config("E4")
    assert e4["system"] is None
    assert e4["analysis"] is True
    assert e4["repeats"] is None

    e5 = load_experiment_config("E5")
    assert e5["system"] == "pipeline"
    assert e5["sample_file"] == "samples/ablation_30.json"
    assert len(e5["ablations"]) == 7

    e6 = load_experiment_config("E6")
    assert e6["system"] is None
    assert e6["analysis"] is True
    assert e6["repeats"] is None
    assert "metrics" in e6


def test_dry_run_e1_e2_e3(tmp_path):
    override_sample = tmp_path / "sample_2.json"
    override_sample.write_text(json.dumps(["canonical-0394", "canonical-0430"]), encoding="utf-8")
    results_dir = tmp_path / "results"

    fake_llm = FakeLLM()

    for exp in ["E1", "E2", "E3"]:
        out_dirs = run_experiment(
            exp_name=exp,
            repeat=0,
            sample_file=override_sample,
            results_dir=results_dir,
            workers=1,
            llm=fake_llm,
        )
        assert len(out_dirs) == 1
        repeat_dir = results_dir / exp / "0"
        assert repeat_dir.exists()
        assert (repeat_dir / "config.json").exists()
        assert (repeat_dir / "records.jsonl").exists()
        assert (repeat_dir / "summary.json").exists()

        records_lines = (repeat_dir / "records.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(records_lines) == 2

    # Assert real results/ was not modified
    real_results = Path(__file__).resolve().parent.parent / "results"
    assert not (real_results / "E1").exists()
    assert not (real_results / "E2").exists()
    assert not (real_results / "E3").exists()


def test_aggregation_mean_and_stdev(tmp_path):
    results_dir = tmp_path / "results"
    e1_dir = results_dir / "E1"

    # Setup fake repeat 0: acc = 0.5 (1/2), tokens = 1000, latency = 10.0
    r0_dir = e1_dir / "0"
    r0_dir.mkdir(parents=True)
    rec0 = [
        {"problem_id": "p1", "correct": True, "usage": {"input_tokens": 400, "output_tokens": 600, "calls": 1}, "latency_s": 6.0},
        {"problem_id": "p2", "correct": False, "usage": {"input_tokens": 400, "output_tokens": 600, "calls": 1}, "latency_s": 14.0},
    ]
    (r0_dir / "records.jsonl").write_text("\n".join(json.dumps(r) for r in rec0) + "\n", encoding="utf-8")
    (r0_dir / "config.json").write_text(json.dumps({"repeat": 0}), encoding="utf-8")

    # Setup fake repeat 1: acc = 1.0 (2/2), tokens = 1200, latency = 20.0
    r1_dir = e1_dir / "1"
    r1_dir.mkdir(parents=True)
    rec1 = [
        {"problem_id": "p1", "correct": True, "usage": {"input_tokens": 500, "output_tokens": 700, "calls": 2}, "latency_s": 18.0},
        {"problem_id": "p2", "correct": True, "usage": {"input_tokens": 500, "output_tokens": 700, "calls": 2}, "latency_s": 22.0},
    ]
    (r1_dir / "records.jsonl").write_text("\n".join(json.dumps(r) for r in rec1) + "\n", encoding="utf-8")
    (r1_dir / "config.json").write_text(json.dumps({"repeat": 1}), encoding="utf-8")

    summary = aggregate_experiment("E1", results_dir=results_dir)

    # Hand-computed expectations:
    # accuracy: [0.5, 1.0] -> mean = 0.75, stdev = sqrt(((0.5-0.75)^2 + (1.0-0.75)^2)/1) = sqrt(0.125) = 0.3535533905932738
    # mean_tokens: [1000.0, 1200.0] -> mean = 1100.0, stdev = 141.4213562373095
    # mean_latency: [10.0, 20.0] -> mean = 15.0, stdev = 7.0710678118654755
    assert math.isclose(summary["accuracy"]["mean"], 0.75, rel_tol=1e-6)
    assert math.isclose(summary["accuracy"]["stdev"], 0.3535533905932738, rel_tol=1e-6)

    assert math.isclose(summary["mean_tokens"]["mean"], 1100.0, rel_tol=1e-6)
    assert math.isclose(summary["mean_tokens"]["stdev"], 141.4213562373095, rel_tol=1e-6)

    assert math.isclose(summary["mean_latency"]["mean"], 15.0, rel_tol=1e-6)
    assert math.isclose(summary["mean_latency"]["stdev"], 7.0710678118654755, rel_tol=1e-6)

    # Check files created
    assert (e1_dir / "summary.json").exists()
    assert (e1_dir / "summary.csv").exists()
    assert (results_dir / "manifest.json").exists()

    # Test single-repeat stdev is None
    single_dir = results_dir / "SINGLE" / "0"
    single_dir.mkdir(parents=True)
    (single_dir / "records.jsonl").write_text(json.dumps(rec0[0]) + "\n", encoding="utf-8")
    (single_dir / "config.json").write_text(json.dumps({"repeat": 0}), encoding="utf-8")
    single_summary = aggregate_experiment("SINGLE", results_dir=results_dir)
    assert single_summary["accuracy"]["stdev"] is None


def test_config_no_key_like_values(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_RUNNER_SECRET_KEY", "super_secret_key_val_99999")
    monkeypatch.setenv("LLM_AUTH_TOKEN", "top_secret_auth_token_88888")

    override_sample = tmp_path / "sample_2.json"
    override_sample.write_text(json.dumps(["canonical-0394", "canonical-0430"]), encoding="utf-8")
    results_dir = tmp_path / "results"

    run_experiment(
        exp_name="E1",
        repeat=0,
        sample_file=override_sample,
        results_dir=results_dir,
        workers=1,
        llm=FakeLLM(),
    )

    config_text = (results_dir / "E1" / "0" / "config.json").read_text(encoding="utf-8")
    assert "super_secret_key_val_99999" not in config_text
    assert "top_secret_auth_token_88888" not in config_text


def test_prompt_version_stable_and_changes(monkeypatch):
    v1 = get_prompt_version()
    v2 = get_prompt_version()
    assert v1 == v2
    assert len(v1) == 64

    monkeypatch.setattr(optverify.prompts, "PARSE", "MODIFIED PARSE TEMPLATE FOR TESTING")
    v3 = get_prompt_version()
    assert v3 != v1

    git_commit = get_git_commit()
    assert isinstance(git_commit, str)
    assert len(git_commit) > 0


def test_analysis_experiments_refuse_to_run(tmp_path):
    results_dir = tmp_path / "results"
    for exp in ["E4", "E6"]:
        with pytest.raises(ValueError) as excinfo:
            run_experiment(exp_name=exp, results_dir=results_dir)
        assert "Refusing to run analysis-only experiment" in str(excinfo.value)
        assert "Aggregate E1, E2, and E3 instead" in str(excinfo.value)
