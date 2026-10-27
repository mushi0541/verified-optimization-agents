"""Offline tests for per-step trace logging and secret safety."""

from __future__ import annotations

import json
from pathlib import Path

from optverify.contracts import Problem, TokenUsage
from optverify.run import build_parser, parse_args
from optverify.systems import run_baseline, run_pipeline
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
        output_info="Output containing super-secret-aws-key inside",
    )

    raw_text = trace_file.read_text(encoding="utf-8")
    assert "secret-test-key-999" not in raw_text
    assert "super-secret-aws-key" not in raw_text
    assert "[REDACTED]" in raw_text


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
    assert "verifier" in roles
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


def test_without_trace_no_logs_folder_created(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    assert not logs_dir.exists()

    problem = Problem("sample-3", TOY_QUESTION, TOY_OPTIMUM, "Production", 1, "test")
    run_baseline(problem, FakeLLM(), max_repairs=0, trace=None)
    run_pipeline(problem, FakeLLM(), paraphrases=1, max_repairs=0, threshold=0.8, trace=None)

    assert not logs_dir.exists()


class DisagreeingFakeLLM(FakeLLM):
    def complete(self, prompt: str, max_tokens: int = 4096):
        if "A small factory produces" in prompt:
            diff_code = (
                "```python\n"
                "import pulp\n"
                'model = pulp.LpProblem("alt", pulp.LpMaximize)\n'
                'x = pulp.LpVariable("x", lowBound=0, cat="Integer")\n'
                "model += 20 * x\n"
                "model += x <= 10\n"
                "model.solve(pulp.HiGHS(msg=False, timeLimit=120))\n"
                "```"
            )
            from optverify.contracts import LLMReply, TokenUsage
            return LLMReply(diff_code, TokenUsage(10, 20, 1), 0.0)
        return super().complete(prompt, max_tokens)


def make_sample_traces(output_dir: Path = Path("logs/sample")) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    created_paths: list[Path] = []

    # 1 to 7: Answered cases
    for i in range(1, 8):
        pid = f"sample-{i:04d}"
        file_path = output_dir / f"{pid}.jsonl"
        if file_path.exists():
            file_path.unlink()
        writer = TraceWriter(file_path)
        problem = Problem(pid, TOY_QUESTION, TOY_OPTIMUM, "Production", 10, "sample")
        run_pipeline(problem, FakeLLM(), paraphrases=1, max_repairs=0, threshold=0.8, trace=writer)
        created_paths.append(file_path)

    # 8: Escalated due to missing number coverage (unused requirements)
    pid = "sample-0008"
    file_path = output_dir / f"{pid}.jsonl"
    if file_path.exists():
        file_path.unlink()
    writer = TraceWriter(file_path)
    q_esc1 = "100 workers, 200 parts, 300 tools, 400 bolts, 500 screws. " + TOY_QUESTION
    problem = Problem(pid, q_esc1, TOY_OPTIMUM, "Production", 10, "sample")
    run_pipeline(problem, FakeLLM(), paraphrases=1, max_repairs=0, threshold=0.8, trace=writer)
    created_paths.append(file_path)

    # 9: Escalated due to paraphrase agreement failure
    pid = "sample-0009"
    file_path = output_dir / f"{pid}.jsonl"
    if file_path.exists():
        file_path.unlink()
    writer = TraceWriter(file_path)
    problem = Problem(pid, TOY_QUESTION, TOY_OPTIMUM, "Production", 10, "sample")
    run_pipeline(problem, DisagreeingFakeLLM(), paraphrases=1, max_repairs=0, threshold=0.8, trace=writer)
    created_paths.append(file_path)

    # 10: Escalated due to high decision threshold requirement
    pid = "sample-0010"
    file_path = output_dir / f"{pid}.jsonl"
    if file_path.exists():
        file_path.unlink()
    writer = TraceWriter(file_path)
    q_esc3 = "12 safety inspectors. " + TOY_QUESTION
    problem = Problem(pid, q_esc3, TOY_OPTIMUM, "Production", 10, "sample")
    run_pipeline(problem, FakeLLM(), paraphrases=1, max_repairs=0, threshold=0.99, trace=writer)
    created_paths.append(file_path)

    # Also write a combined sample trace file containing all 10 problem traces
    combined_path = output_dir / "sample.jsonl"
    with combined_path.open("w", encoding="utf-8", newline="\n") as comb:
        for p in created_paths:
            comb.write(p.read_text(encoding="utf-8"))
    created_paths.append(combined_path)

    return created_paths


def test_make_sample_traces_integrity(tmp_path: Path) -> None:
    sample_files = make_sample_traces(output_dir=tmp_path)
    assert len(sample_files) == 11

    actions = []
    for f in sample_files[:-1]:
        lines = [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines()]
        decision_line = next(line for line in lines if line["role"] == "decision")
        actions.append(decision_line["output"]["action"])

    assert "answer" in actions
    assert "escalate" in actions
    assert actions.count("answer") == 7
    assert actions.count("escalate") == 3


