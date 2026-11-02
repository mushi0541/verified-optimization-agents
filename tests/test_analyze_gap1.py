"""Tests for the Gap 1 (H1) analysis on small hand-made records."""

import json
import random
from pathlib import Path

import pytest

import optverify.calibration
from optverify.calibration import load_run
from scripts.analyze_gap1 import (
    analyze_run,
    at_threshold,
    auroc,
    b0_reference,
    calibrated_threshold,
    outcomes,
    problem_groups,
    summarize,
    verdict,
)

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def _usage(tokens: int, calls: int) -> dict:
    return {"input_tokens": tokens, "output_tokens": 0, "calls": calls}


def _record(pid: str, correct: bool, number: float, requirement: float | None, others: list, feasible: bool = True) -> dict:
    """A saved pipeline record whose final optimum is 100 (correct) or 90 (wrong) against a reference of 100."""
    objective = (100.0 if correct else 90.0) if feasible else None
    steps = {"parse": _usage(10, 1), "formalize": _usage(10, 1), "repair": _usage(0, 0)}
    for j in range(1, len(others) + 1):
        steps[f"paraphrase_{j}"] = _usage(10, 2)
    return {
        "problem_id": pid, "problem_class": "A", "reference": 100.0, "correct": correct,
        "attempts": [{"code": "", "solve": {"status": "optimal" if feasible else "error", "objective": objective}}],
        "usage": _usage(sum(s["input_tokens"] for s in steps.values()), sum(s["calls"] for s in steps.values())),
        "usage_by_step": steps,
        "verifier": {"feasible": feasible, "number_coverage": number, "requirement_coverage": requirement,
                     "paraphrase_agreement": None, "paraphrase_objectives": others, "score": 0.0},
    }


def _brute_force(scores, labels):
    pairs = [(p, n) for p, lp in zip(scores, labels) if lp for n, ln in zip(scores, labels) if not ln]
    return sum(1.0 if p > n else 0.5 if p == n else 0.0 for p, n in pairs) / len(pairs)


def test_auroc_matches_the_pairwise_definition_with_ties():
    rng = random.Random(1)
    for _ in range(20):
        scores = [rng.choice([0.0, 0.25, 0.5, 0.75, 1.0]) for _ in range(40)]
        labels = [rng.random() < 0.6 for _ in range(40)]
        if 0 < sum(labels) < 40:
            assert auroc(scores, labels) == pytest.approx(_brute_force(scores, labels))
    assert auroc([0.1, 0.9], [True, True]) is None


def test_paraphrase_separates_and_number_does_not():
    # Correct answers: rewordings agree. Wrong answers: rewordings disagree. Number coverage is 1 everywhere.
    records = [_record(f"c{i}", True, 1.0, 1.0, [100.0, 100.0]) for i in range(6)]
    records += [_record(f"w{i}", False, 1.0, 1.0, [100.0, 100.0]) for i in range(3)]  # wrong model at 90
    records += [_record("x", False, 0.0, None, [], feasible=False), {"problem_id": "f", "problem_class": "A", "failed": True}]
    rows = outcomes(records)
    assert len(rows) == 10 and sum(r["correct"] for r in rows) == 6
    result = analyze_run(records, 0.8, draws=200, seed=0, groups={})
    values = result["auroc"]
    assert values["feasibility"] == pytest.approx(0.5 + 0.5 * 0.25)  # only the infeasible wrong answer is separated
    assert values["number"] == values["feasibility"]  # coverage is 1 for every feasible model
    assert values["paraphrase"] == 1.0 and values["combined"] == 1.0
    assert values["combined_without_number"] == 1.0
    assert result["failed_problems"] == 1
    assert result["at_threshold"]["accepted"] == 6 and result["at_threshold"]["precision"] == 1.0
    assert result["at_threshold"]["problems"] == 11  # the failed problem counts in coverage, not in the AUROCs


def test_verdict_needs_the_gain_and_every_drop():
    values = {"combined": 0.9, "feasibility": 0.6}
    intervals = {"gain": [0.2, 0.4], "drop_number": [0.01, 0.1], "drop_requirement": [0.02, 0.1], "drop_paraphrase": [0.1, 0.3]}
    assert verdict(values, intervals)["supported"]
    intervals["drop_number"] = [-0.01, 0.05]
    v = verdict(values, intervals)
    assert v["gain_ok"] and not v["supported"] and v["drops_ok"]["number"] is False
    assert not verdict({"combined": 0.65, "feasibility": 0.6}, {**intervals, "gain": [0.01, 0.1]})["gain_ok"]  # gain < 0.10

    run = {"auroc": {}, "verdict": v, "at_threshold": {"precision": 1.0, "recall": 0.5, "coverage": 0.4}}
    run["auroc"] = {name: 0.5 for name in ("feasibility", "number", "requirement", "paraphrase", "combined",
                                            "combined_without_number", "combined_without_requirement",
                                            "combined_without_paraphrase")}
    assert summarize([run, run])["h1"].startswith("partly")
    assert summarize([{**run, "verdict": {**v, "gain_ok": False}}])["h1"] == "not supported"


def test_precision_recall_and_b0():
    rows = [{"feasible": True, "combined": 0.9, "correct": True}, {"feasible": True, "combined": 0.9, "correct": False},
            {"feasible": True, "combined": 0.5, "correct": True}, {"feasible": False, "combined": 0.0, "correct": False}]
    t = at_threshold(rows, 0.8)
    assert (t["accepted"], t["precision"], t["recall"], t["coverage"]) == (2, 0.5, 0.5, 0.5)
    assert at_threshold(rows, float("inf"))["accepted"] == 0

    baseline = [
        {"problem_id": "a", "reference": 5.0, "attempts": [{"solve": {"status": "optimal", "objective": 5.0}}]},
        {"problem_id": "b", "reference": 5.0, "attempts": [{"solve": {"status": "optimal", "objective": 7.0}}]},
        {"problem_id": "c", "reference": 5.0, "attempts": [{"solve": {"status": "error", "objective": None}}]},
        {"problem_id": "z", "reference": 5.0, "attempts": [{"solve": {"status": "optimal", "objective": 5.0}}]},
    ]
    b0 = b0_reference(baseline, {"a", "b", "c"})
    assert (b0["problems"], b0["accepted"], b0["wrong_accepted"], b0["precision"]) == (3, 2, 1, 0.5)


def test_groups_come_from_the_split_metadata():
    pair = json.loads((SAMPLES / "constraint_pairs_30.json").read_text(encoding="utf-8"))[0]
    word = json.loads((SAMPLES / "linguistic_30.json").read_text(encoding="utf-8"))[0]
    groups = problem_groups({pair["original"], pair["augmented"], word, "canonical-0001"})
    assert groups[pair["original"]] == "original" and groups[pair["augmented"]] == "augmented"
    assert groups[word] in {"easy", "moderate", "hard"}
    assert "canonical-0001" not in groups


def _run_folder(tmp_path, finished, failed_ids):
    # A real run folder: run.py lists failed problems only in summary.json.
    (tmp_path / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in finished), encoding="utf-8")
    summary = {"config": {"no_parser": False}, "failed_problems": failed_ids}
    (tmp_path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return tmp_path / "records.jsonl"


def test_failed_problems_from_the_summary_count_in_coverage(tmp_path, monkeypatch):
    finished = [_record(f"c{i}", True, 1.0, 1.0, [100.0, 100.0]) | {"system": "pipeline_p2"} for i in range(6)]
    finished += [_record(f"w{i}", False, 1.0, 1.0, [100.0, 100.0]) | {"system": "pipeline_p2"} for i in range(2)]
    path = _run_folder(tmp_path, finished, ["canonical-0001", "canonical-0002"])
    monkeypatch.setattr(optverify.calibration, "problem_classes", lambda ids: {i: "A" for i in ids})
    result = analyze_run(load_run(path), 0.8, draws=100, seed=0, groups={})
    assert (result["problems"], result["failed_problems"]) == (8, 2)
    assert result["at_threshold"]["accepted"] == 6
    assert result["at_threshold"]["coverage"] == pytest.approx(6 / 10)  # not 6 / 8


def test_groups_have_their_own_intervals():
    records = [_record(f"c{i}", True, 1.0, 1.0, [100.0, 100.0]) for i in range(8)]
    records += [_record(f"w{i}", False, 1.0, 1.0, [90.0, 100.0]) for i in range(4)]
    groups = {r["problem_id"]: ("easy" if int(r["problem_id"][1:]) % 2 else "hard") for r in records}
    result = analyze_run(records, 0.8, draws=100, seed=0, groups=groups)
    for group in result["groups"].values():
        assert group["intervals"]["combined"] is not None and group["intervals"]["gain"] is not None


def test_a_run_without_wrong_answers_is_not_testable():
    records = [_record(f"c{i}", True, 1.0, 1.0, [100.0, 100.0]) for i in range(5)]
    run = analyze_run(records, 0.8, draws=50, seed=0, groups={})
    assert run["verdict"]["testable"] is False
    assert summarize([run])["h1"].startswith("not testable")


def test_calibration_file_must_fit_the_runs(tmp_path):
    finished = [_record("c0", True, 1.0, 1.0, [100.0, 100.0]) | {"system": "pipeline_p2"}]
    path = _run_folder(tmp_path, finished, [])
    records = load_run(path)
    fitting = {"system": "pipeline_p2", "signals": ["number", "requirement", "paraphrase"], "use_parser": True,
               "alpha": 0.1, "threshold": 0.9}
    assert calibrated_threshold(fitting, [path], [records]) == 0.9
    with pytest.raises(SystemExit, match="pipeline_p3"):
        calibrated_threshold(fitting | {"system": "pipeline_p3"}, [path], [records])
    with pytest.raises(SystemExit, match="signals"):
        calibrated_threshold(fitting | {"signals": ["number"]}, [path], [records])


def test_sample_keeps_its_problems_in_every_run_and_names_it(tmp_path):
    import subprocess
    import sys

    finished = [_record(f"c{i}", True, 1.0, 1.0, [100.0, 100.0]) | {"system": "pipeline_p2"} for i in range(6)]
    finished += [_record(f"w{i}", False, 1.0, 0.5, [90.0, 100.0]) | {"system": "pipeline_p2"} for i in range(4)]
    path = _run_folder(tmp_path, finished, [])
    sample = tmp_path / "sample.json"
    sample.write_text(json.dumps(["c0", "c1", "c2", "w0", "w1"]), encoding="utf-8")
    out = tmp_path / "out"
    script = Path(__file__).resolve().parent.parent / "scripts" / "analyze_gap1.py"
    subprocess.run([sys.executable, str(script), "--records", str(path), "--sample", str(sample), "--draws", "50",
                    "--out", str(out)], check=True, capture_output=True)
    result = json.loads((out / "gap1.json").read_text(encoding="utf-8"))
    assert result["runs"][0]["problems"] == 5 and result["settings"]["sample"].endswith("sample.json")
    assert "**Only the problems of" in (out / "gap1.md").read_text(encoding="utf-8")
