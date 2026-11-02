"""Tests for trajectory parser and formatter script (#41)."""

import json
from pathlib import Path
import pytest

from scripts.format_trajectories import (
    parse_trace_file,
    format_summary_table,
    format_single_trajectory_markdown,
    clean_code_block,
)


SAMPLE_DIR = Path("logs/sample")


def test_clean_code_block() -> None:
    assert clean_code_block("```python\nx = 1\n```") == "x = 1"
    assert clean_code_block("```\nx = 2\n```") == "x = 2"
    assert clean_code_block("x = 3") == "x = 3"


def test_parse_clean_trace() -> None:
    trace_path = SAMPLE_DIR / "canonical-1155.jsonl"
    if not trace_path.exists():
        pytest.skip("Sample trace not found")

    traj = parse_trace_file(trace_path)
    assert traj["problem_id"] == "canonical-1155"
    assert traj["steps_count"] == 15
    assert traj["total_latency_s"] > 0
    assert traj["total_tokens"]["calls"] > 0
    assert traj["final_solver_status"] == "optimal"
    assert traj["final_objective"] == 3424.0
    assert len(traj["solver_attempts"]) == 1
    assert len(traj["repair_steps"]) == 0

    v = traj["verifier"]
    assert v["feasible"] is True
    assert v["number_coverage"] == 1.0
    assert v["requirement_coverage"] == 1.0
    assert v["paraphrase_agreement"] == 1.0
    assert v["score"] == 1.0

    d = traj["decision"]
    assert d["action"] == "answer"
    assert d["answer"] == 3424.0
    assert len(d["reasons"]) == 0


def test_parse_repair_trace() -> None:
    trace_path = SAMPLE_DIR / "canonical-1250.jsonl"
    if not trace_path.exists():
        pytest.skip("Sample trace not found")

    traj = parse_trace_file(trace_path)
    assert traj["problem_id"] == "canonical-1250"
    assert len(traj["solver_attempts"]) == 2
    assert traj["solver_attempts"][0]["status"] == "error"
    assert traj["solver_attempts"][1]["status"] == "optimal"
    assert len(traj["repair_steps"]) == 1
    assert traj["decision"]["action"] == "answer"
    assert traj["verifier"]["score"] > 0.98


def test_parse_escalated_trace() -> None:
    trace_path = SAMPLE_DIR / "canonical-0890.jsonl"
    if not trace_path.exists():
        pytest.skip("Sample trace not found")

    traj = parse_trace_file(trace_path)
    assert traj["problem_id"] == "canonical-0890"
    assert traj["decision"]["action"] == "escalate"
    assert traj["verifier"]["paraphrase_agreement"] == 0.0
    assert len(traj["decision"]["reasons"]) >= 1


def test_format_summary_table() -> None:
    fake_trajs = [
        {
            "problem_id": "test-0001",
            "steps_count": 10,
            "solver_attempts": [{"status": "optimal", "objective": 42.0}],
            "final_solver_status": "optimal",
            "final_objective": 42.0,
            "total_latency_s": 5.2,
            "total_tokens": {"input_tokens": 100, "output_tokens": 50, "calls": 2},
            "verifier": {"paraphrase_agreement": 1.0, "score": 0.95},
            "decision": {"action": "answer"},
        }
    ]
    table = format_summary_table(fake_trajs)
    assert "| Problem ID |" in table
    assert "test-0001" in table
    assert "42.0000" in table
    assert "answer" in table


def test_format_single_trajectory_markdown() -> None:
    fake_traj = {
        "problem_id": "prob-test",
        "path": "logs/test.jsonl",
        "steps_count": 5,
        "total_latency_s": 12.3,
        "total_tokens": {"input_tokens": 500, "output_tokens": 200, "calls": 3},
        "prompt_text": "Solve knapsack problem with capacity 10.",
        "parsed_spec": '{"objective_sense": "maximize"}',
        "formalizer_code": "import pulp\nmodel = pulp.LpProblem()",
        "repair_steps": [],
        "solver_attempts": [{"status": "optimal", "objective": 100.0, "error": ""}],
        "final_solver_status": "optimal",
        "final_objective": 100.0,
        "paraphrases": {
            "1": {"text": "Variant question", "code": "", "solve": {"status": "optimal", "objective": 100.0}}
        },
        "verifier": {
            "feasible": True,
            "number_coverage": 1.0,
            "missing_numbers": [],
            "requirement_coverage": 1.0,
            "missing_requirements": [],
            "paraphrase_agreement": 1.0,
            "paraphrase_objectives": [100.0],
            "score": 1.0,
        },
        "decision": {"action": "answer", "answer": 100.0, "reasons": []},
        "explainer": "Optimal solution found.",
    }
    md = format_single_trajectory_markdown(fake_traj)
    assert "### Problem: `prob-test`" in md
    assert "Input Problem Statement" in md
    assert "Parser Specification" in md
    assert "Formalizer Initial Code" in md
    assert "Verification Signals" in md
    assert "Decision Gate & Explainer" in md
    assert "Optimal solution found." in md


def test_synthetic_trace_file(tmp_path: Path) -> None:
    lines = [
        {"role": "parser", "input": "Question text", "output": '{"objective_sense": "minimize"}', "tokens": {"input_tokens": 10, "output_tokens": 20, "calls": 1}, "latency_s": 1.0},
        {"role": "formalizer", "input": "Code prompt", "output": "import pulp", "tokens": {"input_tokens": 30, "output_tokens": 40, "calls": 1}, "latency_s": 2.0},
        {"role": "solver", "input": "code", "output": {"status": "optimal", "objective": 15.5, "error": ""}, "latency_s": 0.5},
        {"role": "verifier", "output": {"feasible": True, "score": 0.85, "number_coverage": 1.0, "requirement_coverage": 1.0, "paraphrase_agreement": 1.0, "missing_numbers": [], "missing_requirements": [], "paraphrase_objectives": [15.5]}},
        {"role": "decision", "output": {"action": "answer", "answer": 15.5, "reasons": []}},
        {"role": "explainer", "output": "Done."},
    ]
    trace_file = tmp_path / "test_trace.jsonl"
    with open(trace_file, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item) + "\n")

    traj = parse_trace_file(trace_file)
    assert traj["problem_id"] == "test_trace"
    assert traj["steps_count"] == 6
    assert traj["total_tokens"]["calls"] == 2
    assert traj["final_objective"] == 15.5
    assert traj["decision"]["action"] == "answer"
