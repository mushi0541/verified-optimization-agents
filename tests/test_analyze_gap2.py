"""Tests for the Gap 2 (H2) analysis on small hand-made records."""

import json

import pytest

import optverify.calibration
from optverify.calibration import load_run
from scripts.analyze_gap2 import analyze_run, b0_reference, h2_check, risk_coverage, summarize


def _record(pid: str, problem_class: str, score: float, correct: bool, feasible: bool = True) -> dict:
    return {"problem_id": pid, "problem_class": problem_class, "system": "pipeline_p3", "correct": correct,
            "verifier": {"feasible": feasible, "score": score}}


def _canonical(per_class: int) -> list[dict]:
    """Ten classes; in each, problem 0 is a low-score wrong answer and problem 9 a confident wrong answer.

    With 20 per class each fold calibrates on 171 answers at score 1.0 with 9 wrong (exact bound 0.090), so alpha = 10%
    is met at threshold 1.0, and 0.5 is not (18 wrong of 180, bound 0.145).
    """
    records = []
    for c in range(10):
        for i in range(per_class):
            pid = f"c{c}-{i}"
            if i == 0:
                records.append(_record(pid, f"Class{c}", 0.5, False))
            elif i == 9:
                records.append(_record(pid, f"Class{c}", 1.0, False))
            else:
                records.append(_record(pid, f"Class{c}", 1.0, True))
    return records


def test_risk_coverage_moves_from_strict_to_lenient():
    records = [_record("a", "A", 1.0, True), _record("b", "A", 0.9, False), _record("c", "A", 0.5, True),
               _record("d", "A", 0.0, False, feasible=False), {"problem_id": "e", "problem_class": "A", "failed": True}]
    points = risk_coverage(records)
    assert [p["threshold"] for p in points] == [1.0, 0.9, 0.5]
    assert [p["coverage"] for p in points] == [0.2, 0.4, 0.6]  # over all 5 problems: the failed one is not answered
    assert [p["wrong_accept_rate"] for p in points] == [0.0, 0.5, pytest.approx(1 / 3)]


def test_twenty_per_class_narrows_the_interval_against_ten():
    records = _canonical(20)
    subset = {r["problem_id"] for r in records if int(r["problem_id"].split("-")[1]) < 10}
    run = analyze_run(records, [0.10], 0.8, subset)
    test = run["by_alpha"]["0.1"]["test"]
    assert [fold["threshold"] for fold in test["folds"]] == [1.0] * 10
    assert test["problems"] == 200 and test["pooled"]["answered"] == 190  # each held-out class answers its 1.0 scores
    assert test["pooled"]["wrong_accepted"] == 10 and test["pooled"]["wrong_accept_rate"] == pytest.approx(10 / 190)
    # With the first 10 per class, each fold has 81 answers with 9 wrong: no threshold meets 10%, nothing is answered.
    assert run["by_alpha"]["0.1"]["subset"]["pooled"]["answered"] == 0
    width = run["by_alpha"]["0.1"]["interval_width"]
    assert width["all"] < width["subset"] == 1.0
    assert run["fixed"]["answered"] == 190 and run["fixed"]["wrong_accepted"] == 10


def test_h2_needs_the_rate_and_half_of_the_problems_answered():
    def test_with(wrong, answered, coverage):
        rate = wrong / answered if answered else None
        return {"alpha": 0.10,
                "pooled": {"wrong_accepted": wrong, "answered": answered, "wrong_accept_rate": rate, "coverage": coverage}}

    check = h2_check(test_with(2, 100, 0.9))
    assert (check["rate_ok"], check["coverage_ok"], check["upper_bound_ok"], check["supported"]) == (True, True, True, True)
    assert check["one_sided_upper_bound"] == pytest.approx(0.0616, abs=1e-4)  # the bound the calibration uses
    point_only = h2_check(test_with(5, 100, 0.9))  # 5% wrong, but the one-sided bound is 10.2%
    assert point_only["supported"] and not point_only["upper_bound_ok"]
    assert not h2_check(test_with(5, 100, 0.4))["supported"]  # too few answered
    assert not h2_check(test_with(12, 100, 0.9))["supported"]
    assert not h2_check(test_with(0, 0, 0.0))["supported"]  # nothing answered

    run = analyze_run(_canonical(20), [0.10], 0.8, None)
    summary = summarize([run, run], [0.10])
    assert summary["h2"].startswith("supported")
    assert summary["by_alpha"]["0.1"]["coverage"]["mean"] == pytest.approx(0.95)
    only_five = analyze_run(_canonical(20), [0.05], 0.8, None)
    assert summarize([only_five], [0.05])["h2"].startswith("not tested")


def test_b0_answers_whenever_its_first_model_is_optimal():
    baseline = [
        {"problem_id": "a", "reference": 5.0, "attempts": [{"solve": {"status": "optimal", "objective": 5.0}}]},
        {"problem_id": "b", "reference": 5.0, "attempts": [{"solve": {"status": "optimal", "objective": 7.0}}]},
        {"problem_id": "c", "reference": 5.0, "attempts": [{"solve": {"status": "error", "objective": None}}]},
    ]
    b0 = b0_reference(baseline, {"a", "b", "c", "z"})
    assert (b0["problems"], b0["answered"], b0["wrong_accepted"], b0["wrong_accept_rate"]) == (3, 2, 1, 0.5)
    with_failed = b0_reference(baseline + [{"problem_id": "z", "problem_class": "A", "failed": True}], {"a", "b", "c", "z"})
    assert (with_failed["problems"], with_failed["answered"]) == (4, 2)  # a failed problem is not answered


def test_failed_problems_in_the_summary_lower_coverage(tmp_path, monkeypatch):
    # A real run folder: run.py writes failed problems only to summary.json, never to records.jsonl.
    records = _canonical(20)
    failed = [r for r in records if int(r["problem_id"].split("-")[1]) >= 12]  # 8 per class, 80 of 200
    finished = [r for r in records if r not in failed]
    (tmp_path / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in finished), encoding="utf-8")
    summary = {"failed_problems": [r["problem_id"] for r in failed]}
    (tmp_path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    monkeypatch.setattr(optverify.calibration, "problem_classes",
                        lambda ids: {r["problem_id"]: r["problem_class"] for r in failed if r["problem_id"] in ids})

    run = analyze_run(load_run(tmp_path / "records.jsonl"), [0.10], 0.8, None)
    assert (run["problems"], run["failed_problems"]) == (200, 80)
    pooled = run["by_alpha"]["0.1"]["test"]["pooled"]
    assert pooled["coverage"] < 0.5  # with the failed problems counted, H2's coverage condition fails
    assert not run["by_alpha"]["0.1"]["h2"]["coverage_ok"]


def test_subset_must_be_in_the_records():
    with pytest.raises(SystemExit, match="0 of the 2 --subset problems"):
        analyze_run(_canonical(20), [0.10], 0.8, {"other-1", "other-2"})


def _folder(tmp_path, name, records):
    folder = tmp_path / name
    folder.mkdir()
    (folder / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    (folder / "summary.json").write_text(json.dumps({"failed_problems": []}), encoding="utf-8")
    return str(folder / "records.jsonl")


def test_runs_joined_with_plus_form_one_repeat(tmp_path):
    from scripts.analyze_gap2 import load_repeat

    first = _folder(tmp_path, "a", _canonical(10))
    second = _folder(tmp_path, "b", [dict(r, problem_id="x" + r["problem_id"]) for r in _canonical(10)])
    assert len(load_repeat(f"{first}+{second}")) == 200
    with pytest.raises(SystemExit, match="more than one"):
        load_repeat(f"{first}+{first}")


def test_alpha_scan_finds_the_smallest_supported_alpha():
    from scripts.analyze_gap2 import alpha_scan

    scan = alpha_scan(_canonical(20))
    # Each fold calibrates on 171 answers with 9 wrong, a bound of 9.004%: below 10% no threshold passes, so nothing
    # is answered. At 10% the held-out pool has 10 wrong of 190 (5.3%), with a one-sided bound of 8.8%.
    assert scan["smallest_alpha_meeting_h2_rule"] == 0.10
    assert scan["smallest_alpha_meeting_the_bound_too"] == 0.10
    nine = next(p for p in scan["points"] if p["alpha"] == 0.09)
    assert nine["coverage"] == 0.0 and not nine["supported"]


def test_command_line_sensitivity_without_classes(tmp_path):
    import subprocess
    import sys

    path = _folder(tmp_path, "run", _canonical(20))
    out = tmp_path / "out"
    subprocess.run([sys.executable, "scripts/analyze_gap2.py", "--records", path, "--exclude-classes", "Class0", "Class1",
                    "--alpha-scan", "--out", str(out)], check=True, capture_output=True)
    result = json.loads((out / "gap2.json").read_text(encoding="utf-8"))
    assert result["settings"]["excluded_classes"] == ["Class0", "Class1"]
    assert result["runs"][0]["problems"] == 160 and "alpha_scan" in result["runs"][0]
    assert "Sensitivity analysis without Class0, Class1" in (out / "gap2.md").read_text(encoding="utf-8")
    assert (out / "alpha_scan.csv").exists() and (out / "alpha_scan.png").exists()
