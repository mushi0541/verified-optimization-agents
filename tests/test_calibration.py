"""Tests for the Gap 2 calibrated threshold and its leave-one-class-out test."""

import json
import threading
import urllib.request

import pytest

from optverify.calibration import (
    binomial_cdf,
    calibrate_threshold,
    check_system,
    exact_interval,
    fixed_threshold,
    leave_one_class_out,
    record_system,
    scored_answers,
    threshold_from_file,
    upper_bound,
)
from optverify.run import _config_value, parse_args
from optverify.web import make_server
from tests.fake_llm import TOY_QUESTION, FakeLLM


def _record(problem_class: str, score: float, correct: bool, feasible: bool = True) -> dict:
    return {"problem_class": problem_class, "correct": correct, "verifier": {"feasible": feasible, "score": score}}


def test_exact_bounds_match_known_values():
    # With no wrong answers the one-sided bound is 1 - (1 - confidence) ** (1 / n).
    assert upper_bound(0, 29) == pytest.approx(1 - 0.05 ** (1 / 29), abs=1e-9)  # 0.0982: 29 is the smallest n below 10%
    assert upper_bound(0, 28) > 0.10
    assert exact_interval(0, 10) == pytest.approx((0.0, 0.30850), abs=1e-4)
    assert exact_interval(5, 10) == pytest.approx((0.18709, 0.81291), abs=1e-4)
    bound = upper_bound(3, 50)
    assert binomial_cdf(3, 50, bound) == pytest.approx(0.05, abs=1e-9)
    assert upper_bound(4, 4) == 1.0


def test_threshold_is_the_most_lenient_one_within_alpha():
    scored = [(1.0, True)] * 40 + [(0.75, True)] * 10 + [(0.75, False)] * 10
    assert calibrate_threshold(scored, alpha=0.10) == 1.0


def test_thresholds_accepting_fewer_than_29_problems_are_skipped():
    scored = [(1.0, True)] * 10 + [(0.9, True)] * 30
    assert calibrate_threshold(scored, alpha=0.10) == 0.9


def test_scan_stops_at_the_first_failing_threshold():
    # 0.8 alone would pass (5 wrong of 240), but the scan must stop at 0.9, where the bound first exceeds alpha.
    scored = [(1.0, True)] * 30 + [(0.9, True)] * 5 + [(0.9, False)] * 5 + [(0.8, True)] * 200
    assert calibrate_threshold(scored, alpha=0.10) == 1.0


def test_no_passing_threshold_answers_nothing():
    assert calibrate_threshold([(1.0, False)] * 50, alpha=0.10) is None
    assert threshold_from_file({"alpha": 0.1, "threshold": None}) == float("inf")
    assert threshold_from_file({"alpha": 0.1, "threshold": 0.75}) == 0.75


def test_leave_one_class_out_uses_only_the_other_classes():
    classes = [f"Class{i}" for i in range(10)]
    records = [_record(c, 1.0, c != "Class9") for c in classes for _ in range(10)]
    records += [_record("Class0", 0.0, False, feasible=False), {"problem_id": "x", "failed": "timeout"}]
    result = leave_one_class_out(records, alpha=0.10)

    folds = {f["held_out_class"]: f for f in result["folds"]}
    assert folds["Class9"]["threshold"] == 1.0  # calibrated on nine all-correct classes
    assert folds["Class9"]["answered"] == 10 and folds["Class9"]["wrong_accepted"] == 10
    assert folds["Class0"]["threshold"] is None  # the wrong Class9 answers break the bound for every other fold
    assert result["pooled"]["answered"] == 10 and result["pooled"]["wrong_accepted"] == 10
    assert result["pooled"]["coverage"] == pytest.approx(10 / 101)
    assert result["problems"] == 101 and result["failed_problems"] == 1
    assert result["threshold"] is None


def test_fixed_threshold_comparison():
    records = [_record("A", 0.9, True)] * 8 + [_record("A", 0.9, False)] * 2 + [_record("A", 0.5, True)] * 10
    result = fixed_threshold(records, 0.8)
    assert result["answered"] == 10 and result["wrong_accepted"] == 2
    assert result["coverage"] == 0.5 and result["wrong_accept_rate"] == 0.2


def _b2_record(problem_class: str, agreement: float, correct: bool, action: str = "answer") -> dict:
    """A B2 record: no verifier report; the decision used the sample agreement rate."""
    return {"problem_class": problem_class, "system": "b2_r1", "correct": correct, "verifier": None,
            "samples": [[], []], "sample_agreement": agreement, "decision": {"action": action}}


def test_b2_records_are_scored_by_their_agreement_rate():
    records = [_b2_record("A", 1.0, True)] * 30 + [_b2_record("A", 0.5, False)] * 5 + [_b2_record("B", 0.0, False, "abstain")]
    assert scored_answers(records[-2:]) == [(0.5, False)]  # an abstained B2 problem could not be accepted
    assert calibrate_threshold(scored_answers(records), alpha=0.10) == 1.0
    assert fixed_threshold(records, 0.8)["answered"] == 30
    assert leave_one_class_out(records, alpha=0.10)["problems"] == 36
    assert record_system(records) == "b2_r1"
    with pytest.raises(ValueError, match="one system"):
        record_system(records + [_record("A", 1.0, True) | {"system": "pipeline_p3"}])


def test_run_reads_alpha_and_threshold_from_a_calibration_file(tmp_path):
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"system": "pipeline_p2", "alpha": 0.1, "threshold": 0.875}), encoding="utf-8")
    args = parse_args(["pipeline", "--model", "dummy", "--calibration", str(path)])
    assert (args.alpha, args.threshold) == (0.1, 0.875)

    path.write_text(json.dumps({"system": "pipeline_p2", "alpha": 0.1, "threshold": None}), encoding="utf-8")
    args = parse_args(["pipeline", "--model", "dummy", "--calibration", str(path)])
    assert args.threshold == float("inf") and _config_value(args.threshold) is None
    assert parse_args(["pipeline", "--model", "dummy"]).alpha is None


def test_a_calibration_file_is_refused_for_another_system(tmp_path, capsys):
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"system": "pipeline_p2", "alpha": 0.1, "threshold": 0.875}), encoding="utf-8")
    with pytest.raises(SystemExit):  # pipeline scores cannot set B2's agreement threshold
        parse_args(["b2", "--model", "dummy", "--budget-tokens", "1000", "--calibration", str(path)])
    assert "made from pipeline_p2 records, not b2_r0" in capsys.readouterr().err

    path.write_text(json.dumps({"system": "b2_r1", "alpha": 0.1, "threshold": 1.0}), encoding="utf-8")
    args = parse_args(["b2", "--model", "dummy", "--budget-tokens", "1000", "--repairs", "1", "--calibration", str(path)])
    assert args.threshold == 1.0
    with pytest.raises(SystemExit):
        parse_args(["pipeline", "--model", "dummy", "--calibration", str(path)])
    with pytest.raises(ValueError, match="unknown"):
        check_system({"alpha": 0.1, "threshold": 0.9}, "pipeline")  # files without a system are refused


def test_a_calibration_file_must_match_k_signals_and_parser(tmp_path, capsys):
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"system": "pipeline_p2", "alpha": 0.1, "threshold": 0.9,
                                "signals": ["number", "requirement", "paraphrase"], "use_parser": True}), encoding="utf-8")
    assert parse_args(["pipeline", "--model", "dummy", "--calibration", str(path)]).threshold == 0.9
    for extra in (["--paraphrases", "3"], ["--signals", "number,paraphrase"], ["--no-parser"]):
        with pytest.raises(SystemExit):
            parse_args(["pipeline", "--model", "dummy", "--calibration", str(path), *extra])
    errors = capsys.readouterr().err
    assert "not pipeline_p3" in errors and "parser True" in errors

    # Without the paraphrase signal no paraphrase runs are made, so the records are pipeline_p0.
    path.write_text(json.dumps({"system": "pipeline_p0", "alpha": 0.1, "threshold": 0.9,
                                "signals": ["number", "requirement"], "use_parser": True}), encoding="utf-8")
    args = parse_args(["pipeline", "--model", "dummy", "--signals", "number,requirement", "--calibration", str(path)])
    assert args.threshold == 0.9
    check_system({"system": "pipeline_p3"}, "pipeline")  # the web page checks only the kind


def test_web_server_uses_the_calibrated_threshold():
    server = make_server("127.0.0.1", 0, FakeLLM(), {"alpha": 0.1, "threshold": None})
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(f"{base}/api/config") as response:
            assert json.loads(response.read()) == {"alpha": 0.1, "threshold": None}
        request = urllib.request.Request(
            f"{base}/api/solve",
            data=json.dumps({"question": TOY_QUESTION, "threshold": 0.0}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            reply = json.loads(response.read())
        # The page asked for threshold 0, but no calibrated threshold met alpha, so nothing is answered.
        assert reply["alpha"] == 0.1 and reply["threshold"] is None
        assert reply["action"] != "answer"
    finally:
        server.shutdown()
