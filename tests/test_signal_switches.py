"""Tests for the Gap 1 switches (signals, parser) and for rescoring saved records (ablations i to vii)."""

import argparse
import json

import pytest

from optverify.contracts import Problem
from optverify.rescore import rescore
from optverify.run import parse_args, parse_signals
from optverify.systems import run_pipeline
from optverify.verifier import combined_score
from scripts.rescore import rescore_records, summarize
from tests.fake_llm import TOY_OPTIMUM, TOY_QUESTION, FakeLLM

TOY_PROBLEM = Problem("toy-1", TOY_QUESTION, TOY_OPTIMUM, "Toy", 2, "canonical")


def _usage(tokens: int, calls: int) -> dict:
    return {"input_tokens": tokens, "output_tokens": 0, "calls": calls}


def _record(first_status="optimal", objective=100.0, others=(100.0, 90.0), number=0.5, requirement=1.0, cls="A"):
    """A saved pipeline record: parse 100, formalize 200, repair 50 (when the first attempt failed), 100 per run."""
    attempts = [{"code": "", "solve": {"status": first_status, "objective": objective if first_status == "optimal" else None}}]
    steps = {"parse": _usage(100, 1), "formalize": _usage(200, 1), "repair": _usage(0, 0)}
    if first_status != "optimal":
        attempts.append({"code": "", "solve": {"status": "optimal", "objective": objective}})
        steps["repair"] = _usage(50, 1)
    for j in range(1, len(others) + 1):
        steps[f"paraphrase_{j}"] = _usage(100, 2)
    total = sum(s["input_tokens"] for s in steps.values())
    return {
        "problem_id": f"p-{cls}-{first_status}", "problem_class": cls, "reference": 100.0, "correct": True,
        "attempts": attempts, "usage": _usage(total, sum(s["calls"] for s in steps.values())), "usage_by_step": steps,
        "verifier": {
            "feasible": True, "number_coverage": number, "requirement_coverage": requirement,
            "paraphrase_agreement": 0.5, "paraphrase_objectives": list(others), "score": 0.0,
        },
    }


def test_score_uses_only_the_enabled_signals():
    assert combined_score(True, 0.5, 1.0, 0.0) == pytest.approx(0.5)
    assert combined_score(True, 0.5, 1.0, 0.0, ("number", "paraphrase")) == pytest.approx(0.75)
    assert combined_score(True, 0.5, None, 0.0, ("paraphrase",)) == 1.0  # nothing available: feasibility alone
    assert combined_score(True, 0.5, 1.0, 0.0, ()) == 1.0
    assert combined_score(False, 1.0, 1.0, 1.0, ()) == 0.0


def test_signal_option_parsing():
    assert parse_signals("paraphrase, number") == ("number", "paraphrase")  # fixed order
    assert parse_signals("none") == ()
    with pytest.raises(argparse.ArgumentTypeError, match="coverage"):
        parse_signals("number,coverage")
    args = parse_args(["pipeline", "--model", "dummy"])
    assert args.signals == ("number", "requirement", "paraphrase") and args.no_parser is False
    args = parse_args(["pipeline", "--model", "dummy", "--signals", "requirement", "--no-parser"])
    assert args.signals == ("requirement",) and args.no_parser is True


def test_pipeline_without_the_paraphrase_signal_makes_no_paraphrase_runs():
    llm = FakeLLM()
    record = run_pipeline(TOY_PROBLEM, llm, paraphrases=2, signals=("number", "requirement"))
    assert not any("Rewrite the optimization problem" in prompt for prompt in llm.prompts)
    assert "paraphrase_1" not in record.usage_by_step
    assert record.verifier.paraphrase_agreement is None and record.verifier.score == 1.0


def test_pipeline_without_the_parser_formalizes_from_the_question():
    llm = FakeLLM()
    record = run_pipeline(TOY_PROBLEM, llm, paraphrases=1, use_parser=False)
    assert not any("Return only a JSON object" in prompt for prompt in llm.prompts)
    assert "Below is an operations research question" in llm.prompts[0]
    assert record.spec is None and record.usage_by_step["parse"].calls == 0
    assert record.verifier.requirement_coverage is None  # no requirements, so the signal is left out
    assert record.decision.action == "answer"


def test_rescore_signals_and_k():
    record = _record()
    full = rescore(record)
    assert full["score"] == pytest.approx((0.5 + 1.0 + 0.5) / 3)
    assert (full["tokens"], full["calls"]) == (500, 6)

    assert rescore(record, ("number", "paraphrase"))["score"] == pytest.approx(0.5)  # ablation ii
    no_paraphrase = rescore(record, ("number", "requirement"))  # ablation iii: the runs and their tokens go
    assert no_paraphrase["score"] == pytest.approx(0.75) and (no_paraphrase["tokens"], no_paraphrase["calls"]) == (300, 2)

    k1 = rescore(record, k=1)  # ablation v: the first run agrees, the dropped second one did not
    assert k1["score"] == pytest.approx((0.5 + 1.0 + 1.0) / 3) and k1["tokens"] == 400
    with pytest.raises(ValueError, match="fewer than k"):
        rescore(record, k=3)


def test_rescore_without_repair_uses_the_first_attempt():
    repaired = _record(first_status="error")
    assert rescore(repaired)["answer"] == 100.0 and rescore(repaired)["tokens"] == 550
    r0 = rescore(repaired, repairs=False)  # ablation vii: no repair means no feasible model and no paraphrase runs
    assert r0["answer"] is None and r0["score"] == 0.0 and not r0["correct"]
    assert (r0["tokens"], r0["calls"]) == (300, 2)

    first_try = _record()
    assert rescore(first_try, repairs=False) == rescore(first_try)  # nothing was repaired, nothing changes


def test_rescore_script_summarizes_a_fixed_and_a_calibrated_threshold(tmp_path):
    records = [_record(cls=c) for c in "ABC"] + [{"problem_id": "x", "failed": "timeout"}]
    rescored = rescore_records(records, ("number",))
    assert rescored[-1] == {"problem_id": "x", "failed": "timeout"}

    args = argparse.Namespace(records=[tmp_path / "r.jsonl"], signals=("number",), k=None, no_repair=False,
                              threshold=0.5, calibration=None, alpha=None)
    result = summarize(rescored, args)
    assert result["problems"] == 3 and result["failed_problems"] == 1
    assert result["decision"]["threshold"] == 0.5 and result["decision"]["answered"] == 3
    assert result["mean_tokens"] == 300  # number only: the paraphrase runs are dropped

    calibration = tmp_path / "calibration.json"
    calibration.write_text(json.dumps({"alpha": 0.1, "threshold": None}), encoding="utf-8")
    args.calibration = calibration
    assert summarize(rescored, args)["decision"]["answered"] == 0  # no passing threshold: answer nothing

    args.calibration, args.alpha = None, 0.10
    loco = summarize(rescored, args)["decision"]
    assert [fold["held_out_class"] for fold in loco["folds"]] == ["A", "B", "C"]
    assert loco["pooled"]["answered"] == 0  # 2 classes of 1 problem each are far below 29 accepted answers
