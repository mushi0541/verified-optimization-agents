from optverify.contracts import Problem
from optverify.systems import run_baseline, run_pipeline
from optverify.verifier import build_report, decide, number_coverage
from tests.fake_llm import TOY_OPTIMUM, TOY_QUESTION, FakeLLM

TOY_PROBLEM = Problem("toy-0", TOY_QUESTION, TOY_OPTIMUM, "Production", 2, "test")


def test_number_coverage_finds_missing_numbers():
    coverage, missing = number_coverage("capacity 40, cost 2.5, demand 7", "model += x <= 40\nmodel += 2.5 * x")
    assert missing == ["7"]
    assert abs(coverage - 2 / 3) < 1e-9


def test_decision_rules():
    good = build_report(TOY_QUESTION, "30 50 2 4 40 3", "optimal", 570.0, [570.0, 570.0])
    assert decide(good, 570.0, threshold=0.8).action == "answer"

    disagreeing = build_report(TOY_QUESTION, "30 50 2 4 40 3", "optimal", 570.0, [600.0, 520.0])
    decision = decide(disagreeing, 570.0, threshold=0.8)
    assert decision.action == "escalate" and decision.reasons

    failed = build_report(TOY_QUESTION, "", "error", None, [])
    assert decide(failed, None, threshold=0.8).action == "abstain"


def test_baseline_end_to_end():
    record = run_baseline(TOY_PROBLEM, FakeLLM())
    assert record.correct and record.usage.calls == 1


def test_baseline_repairs_from_solver_errors_only():
    llm = FakeLLM(code_reply="no code in this reply")
    record = run_baseline(TOY_PROBLEM, llm, max_repairs=2)
    assert len(record.attempts) == 3 and not record.correct
    assert all(str(TOY_OPTIMUM) not in prompt for prompt in llm.prompts)  # the reference answer never leaks


def test_pipeline_end_to_end():
    record = run_pipeline(TOY_PROBLEM, FakeLLM(), paraphrases=2)
    assert record.decision.action == "answer"
    assert record.correct
    assert record.verifier.number_coverage == 1.0
    assert record.verifier.paraphrase_agreement == 1.0
    assert record.usage.calls == 6  # parse + formalize + 2 x (paraphrase + formalize)
    assert "Recommended plan" in record.explanation
