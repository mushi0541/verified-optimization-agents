"""Offline tests for per-step trace logging and secret safety."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import optverify.run
from optverify.contracts import Problem, TokenUsage
from optverify.run import build_parser, parse_args
from optverify.systems import run_baseline, run_pipeline, run_single_agent
from optverify.trace import TraceWriter
from tests.fake_llm import TOY_OPTIMUM, TOY_QUESTION, FakeLLM


def test_trace_writer_writes_valid_json_lines(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace.jsonl"
    writer = TraceWriter(trace_file)

    writer.record(
        role="formalizer",
        input_info="Write model code for toy question",
        output_info="model = pulp.LpProblem()",
        tokens=TokenUsage(input_tokens=15, output_tokens=30, calls=1),
        latency_s=0.25,
    )

    lines = trace_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])

    expected_keys = {"time", "role", "input", "output", "tokens", "latency_s"}
    assert expected_keys.issubset(entry.keys())
    assert entry["role"] == "formalizer"
    assert entry["input"] == "Write model code for toy question"
    assert entry["output"] == "model = pulp.LpProblem()"
    assert entry["tokens"] == {"input_tokens": 15, "output_tokens": 30, "calls": 1}
    assert entry["latency_s"] == 0.25


def test_trace_writer_none_path_writes_nothing(tmp_path: Path) -> None:
    writer = TraceWriter(None)
    writer.record("formalizer", "input", "output")
    assert not list(tmp_path.iterdir())


def test_secret_safety_strips_keys_from_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TEST_API_KEY", "secret-test-key-999")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "super-secret-aws-key")

    trace_file = tmp_path / "secret.jsonl"
    writer = TraceWriter(trace_file)

    writer.record(
        role="formalizer",
        input_info="Prompt containing secret-test-key-999 inside",
        output_info={"key": "Output containing super-secret-aws-key inside"},
    )

    raw_text = trace_file.read_text(encoding="utf-8")
    assert "secret-test-key-999" not in raw_text
    assert "super-secret-aws-key" not in raw_text
    assert "[REDACTED]" in raw_text


def test_secret_safety_handles_quotes_backslashes_newlines(tmp_path: Path, monkeypatch) -> None:
    tricky_secret = 'sec"ret\\with\nnewline'
    monkeypatch.setenv("COMPLEX_SECRET_TOKEN", tricky_secret)

    trace_file = tmp_path / "complex_secret.jsonl"
    writer = TraceWriter(trace_file)

    writer.record(
        role="formalizer",
        input_info=f"Prompt with {tricky_secret} inside",
        output_info={"nested": f"Output with {tricky_secret} inside"},
    )

    raw_text = trace_file.read_text(encoding="utf-8")
    assert tricky_secret not in raw_text
    assert "[REDACTED]" in raw_text

    # Verify JSON lines remain well-formed
    entry = json.loads(raw_text.strip())
    assert entry["input"] == "Prompt with [REDACTED] inside"
    assert entry["output"]["nested"] == "Output with [REDACTED] inside"


def test_baseline_run_with_trace_records_roles(tmp_path: Path) -> None:
    trace_file = tmp_path / "baseline.jsonl"
    writer = TraceWriter(trace_file)
    problem = Problem("sample-1", TOY_QUESTION, TOY_OPTIMUM, "Production", 1, "test")

    run_baseline(problem, FakeLLM(), max_repairs=0, trace=writer)

    lines = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines()]
    roles = [entry["role"] for entry in lines]
    assert "formalizer" in roles
    assert "solver" in roles


def test_pipeline_run_writes_all_pipeline_roles(tmp_path: Path) -> None:
    trace_file = tmp_path / "pipeline.jsonl"
    writer = TraceWriter(trace_file)
    problem = Problem("sample-2", TOY_QUESTION, TOY_OPTIMUM, "Production", 1, "test")

    run_pipeline(problem, FakeLLM(), paraphrases=1, max_repairs=0, threshold=0.8, trace=writer)

    lines = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines()]
    roles = [entry["role"] for entry in lines]

    assert "parser" in roles
    assert "formalizer" in roles
    assert "solver" in roles
    assert "paraphrase_1" in roles
    assert "verifier" in roles
    assert "decision" in roles
    assert "explainer" in roles


def test_b2_trace_records_sample_steps(tmp_path: Path) -> None:
    trace_file = tmp_path / "b2.jsonl"
    writer = TraceWriter(trace_file)
    problem = Problem("sample-b2", TOY_QUESTION, TOY_OPTIMUM, "Production", 1, "test")

    run_single_agent(
        problem,
        FakeLLM(),
        FakeLLM(),
        token_budget=1000,
        max_repairs=0,
        threshold=0.8,
        trace=writer,
    )

    lines = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines()]
    roles = [entry["role"] for entry in lines]

    assert "formalizer" in roles
    assert "solver" in roles
    assert "decision" in roles
    assert "explainer" in roles


def test_cli_trace_flag_defaults_to_false() -> None:
    parser = build_parser()
    args = parser.parse_args(["baseline", "--model", "openai:gpt", "--sample-file", "samples/canonical_100.json"])
    assert args.trace is False

    args_trace = parser.parse_args(
        ["baseline", "--model", "openai:gpt", "--sample-file", "samples/canonical_100.json", "--trace"]
    )
    assert args_trace.trace is True


def test_cli_trace_creates_log_file(tmp_path: Path, monkeypatch) -> None:
    logs_dir = tmp_path / "logs"
    results_dir = tmp_path / "results"
    sample_file = tmp_path / "sample.json"
    sample_file.write_text(json.dumps(["test-0001"]), encoding="utf-8")

    test_prob = Problem("test-0001", TOY_QUESTION, TOY_OPTIMUM, "Production", 1, "test")

    monkeypatch.setattr(optverify.run, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(optverify.run, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(optverify.run, "make_llm", lambda spec, temperature=0.0: FakeLLM())
    monkeypatch.setattr(optverify.run, "load_sample_file", lambda path: [test_prob])

    cli_args = [
        "run.py",
        "baseline",
        "--model",
        "openai:gpt",
        "--sample-file",
        str(sample_file),
        "--trace",
        "--workers",
        "1",
    ]
    monkeypatch.setattr(sys, "argv", cli_args)

    optverify.run.main()

    assert logs_dir.exists()
    trace_files = list(logs_dir.glob("*/*.jsonl"))
    assert len(trace_files) == 1
    assert trace_files[0].name == "test-0001.jsonl"
    assert trace_files[0].stat().st_size > 0


def test_without_trace_no_logs_folder_created(tmp_path: Path, monkeypatch) -> None:
    logs_dir = tmp_path / "logs_not_created"
    results_dir = tmp_path / "results"
    sample_file = tmp_path / "sample.json"
    sample_file.write_text(json.dumps(["test-0002"]), encoding="utf-8")

    test_prob = Problem("test-0002", TOY_QUESTION, TOY_OPTIMUM, "Production", 1, "test")

    monkeypatch.setattr(optverify.run, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(optverify.run, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(optverify.run, "make_llm", lambda spec, temperature=0.0: FakeLLM())
    monkeypatch.setattr(optverify.run, "load_sample_file", lambda path: [test_prob])

    cli_args = [
        "run.py",
        "baseline",
        "--model",
        "openai:gpt",
        "--sample-file",
        str(sample_file),
        "--workers",
        "1",
    ]
    monkeypatch.setattr(sys, "argv", cli_args)

    optverify.run.main()

    assert not logs_dir.exists()
