"""Tests for run.py --resume: continue a run after failed problems (for example a network outage)."""

import json
from pathlib import Path

import pytest

from optverify import run as run_module
from tests.fake_llm import FakeLLM


def _run(monkeypatch, tmp_path, *extra):
    argv = ["run", "baseline", "--model", "bedrock:openai.gpt-oss-120b-1:0", "--split", "opsor", "--per-class", "1",
            "--workers", "1", "--env-file", str(tmp_path / "none"), *extra]
    monkeypatch.setattr("sys.argv", argv)
    run_module.main()


@pytest.fixture(autouse=True)
def v1_prompts_after_each_test():
    """run.py switches the prompt version for the whole process, so every test here ends with v1, even a failing one."""
    yield
    from optverify import prompts

    prompts.use_version("v1")


@pytest.fixture
def offline(monkeypatch, tmp_path):
    """A fake model, results in tmp_path, and a baseline that fails once for the first problem it is given."""
    monkeypatch.setattr(run_module, "make_llm", lambda spec, temperature=0.0: FakeLLM())
    monkeypatch.setattr(run_module, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    real_baseline = run_module.run_baseline
    state = {"failed": None, "calls": []}

    def flaky_baseline(problem, llm, max_repairs=0, trace=None):
        state["calls"].append(problem.problem_id)
        if state["failed"] is None:
            state["failed"] = problem.problem_id
            raise ConnectionError("Could not connect to the endpoint URL")
        return real_baseline(problem, llm, max_repairs, trace=trace)

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


def test_a_resumed_run_writes_its_traces_under_the_original_run(monkeypatch, tmp_path, offline):
    monkeypatch.setattr(run_module, "LOGS_DIR", tmp_path / "logs")
    _run(monkeypatch, tmp_path)  # without --trace
    (out_dir,) = (tmp_path / "results").iterdir()
    _run(monkeypatch, tmp_path, "--resume", str(out_dir), "--trace")  # tracing may be switched on when resuming
    assert [path.name for path in (tmp_path / "logs").iterdir()] == [out_dir.name]
    assert [path.stem for path in (tmp_path / "logs" / out_dir.name).iterdir()] == [offline["failed"]]


def test_a_baseline_run_saved_with_a_paraphrase_endpoint_can_be_resumed(monkeypatch, tmp_path, offline):
    _run(monkeypatch, tmp_path)
    (out_dir,) = (tmp_path / "results").iterdir()
    summary_file = out_dir / "summary.json"
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    summary["config"]["paraphrase_endpoint"] = summary["config"]["endpoint"]  # as written before the pipeline-only rule
    summary_file.write_text(json.dumps(summary), encoding="utf-8")
    _run(monkeypatch, tmp_path, "--resume", str(out_dir))
    assert json.loads(summary_file.read_text(encoding="utf-8"))["failed_problems"] == []


def test_the_env_file_is_saved_by_name_only(monkeypatch, tmp_path, offline):
    _run(monkeypatch, tmp_path)  # passes a full temporary path as --env-file
    (out_dir,) = (tmp_path / "results").iterdir()
    summary = (out_dir / "summary.json").read_text(encoding="utf-8")
    assert json.loads(summary)["config"]["env_file"] == "none"
    assert str(tmp_path.name) not in summary  # no local folder in results/


def test_the_sample_file_is_saved_without_a_local_folder(tmp_path):
    repo = run_module.RESULTS_DIR.parent
    assert run_module._saved_path(None) is None
    assert run_module._saved_path(Path("samples") / "tsp_60.json") == str(Path("samples") / "tsp_60.json")  # as before
    assert run_module._saved_path(repo / "samples" / "tsp_60.json") == "samples/tsp_60.json"
    assert run_module._saved_path(tmp_path / "copy" / "tsp_60.json") == "tsp_60.json"  # outside the repository


def test_resume_refuses_other_settings_or_an_unfinished_folder(monkeypatch, tmp_path, offline):
    _run(monkeypatch, tmp_path)
    (out_dir,) = (tmp_path / "results").iterdir()
    with pytest.raises(SystemExit, match="repairs"):
        _run(monkeypatch, tmp_path, "--resume", str(out_dir), "--repairs", "1")

    (out_dir / "summary.json").unlink()
    with pytest.raises(SystemExit, match="summary.json"):
        _run(monkeypatch, tmp_path, "--resume", str(out_dir))


def test_prompt_version_v2_has_its_own_folder_and_v1_runs_still_resume(monkeypatch, tmp_path, offline):
    _run(monkeypatch, tmp_path, "--prompt-version", "v2")
    (v2_dir,) = (tmp_path / "results").iterdir()
    assert "_prompts-v2_" in v2_dir.name  # the two prompt versions never share a folder name
    assert json.loads((v2_dir / "summary.json").read_text(encoding="utf-8"))["config"]["prompt_version"] == "v2"
    with pytest.raises(SystemExit, match="prompt_version"):
        _run(monkeypatch, tmp_path, "--resume", str(v2_dir))  # a v2 run cannot be resumed with v1

    # A run from before #95 has no prompt_version in its config; it used the v1 prompts and still resumes with them.
    offline["failed"] = None
    _run(monkeypatch, tmp_path)
    (v1_dir,) = [d for d in (tmp_path / "results").iterdir() if d != v2_dir]
    summary = json.loads((v1_dir / "summary.json").read_text(encoding="utf-8"))
    del summary["config"]["prompt_version"]
    (v1_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    _run(monkeypatch, tmp_path, "--resume", str(v1_dir))
    assert json.loads((v1_dir / "summary.json").read_text(encoding="utf-8"))["failed_problems"] == []
