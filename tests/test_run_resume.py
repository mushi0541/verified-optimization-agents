"""Tests for run.py --resume: continue a run after failed problems (for example a network outage)."""

import json

import pytest

from optverify import run as run_module
from tests.fake_llm import FakeLLM


def _run(monkeypatch, tmp_path, *extra):
    argv = ["run", "baseline", "--model", "bedrock:openai.gpt-oss-120b-1:0", "--split", "opsor", "--per-class", "1",
            "--workers", "1", "--env-file", str(tmp_path / "none"), *extra]
    monkeypatch.setattr("sys.argv", argv)
    run_module.main()


@pytest.fixture
def offline(monkeypatch, tmp_path):
    """A fake model, results in tmp_path, and a baseline that fails once for the first problem it is given."""
    monkeypatch.setattr(run_module, "make_llm", lambda spec, temperature=0.0: FakeLLM())
    monkeypatch.setattr(run_module, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    real_baseline = run_module.run_baseline
    state = {"failed": None, "calls": []}

    def flaky_baseline(problem, llm, max_repairs=0):
        state["calls"].append(problem.problem_id)
        if state["failed"] is None:
            state["failed"] = problem.problem_id
            raise ConnectionError("Could not connect to the endpoint URL")
        return real_baseline(problem, llm, max_repairs)

    monkeypatch.setattr(run_module, "run_baseline", flaky_baseline)
    return state


def test_resume_runs_only_the_missing_problems(monkeypatch, tmp_path, offline):
    _run(monkeypatch, tmp_path)
    (out_dir,) = (tmp_path / "results").iterdir()
    first = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert first["failed_problems"] == [offline["failed"]] and first["resumes"] == 0
    finished_before = (out_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(finished_before) == len(offline["calls"]) - 1

    offline["calls"].clear()
    _run(monkeypatch, tmp_path, "--resume", str(out_dir), "--workers", "2")  # workers may change
    assert offline["calls"] == [first["failed_problems"][0]]  # only the failed problem runs again
    records = (out_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()
    assert records[: len(finished_before)] == finished_before  # earlier records are kept, the new one is added
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["failed_problems"] == [] and summary["resumes"] == 1
    assert summary["run"] == out_dir.name and summary["problems"] == len(records)
    assert len(list((tmp_path / "results").iterdir())) == 1  # no new folder


def test_resume_refuses_other_settings_or_an_unfinished_folder(monkeypatch, tmp_path, offline):
    _run(monkeypatch, tmp_path)
    (out_dir,) = (tmp_path / "results").iterdir()
    with pytest.raises(SystemExit, match="repairs"):
        _run(monkeypatch, tmp_path, "--resume", str(out_dir), "--repairs", "1")

    (out_dir / "summary.json").unlink()
    with pytest.raises(SystemExit, match="summary.json"):
        _run(monkeypatch, tmp_path, "--resume", str(out_dir))
