from optverify.contracts import LLMReply, Problem, TokenUsage
from optverify.systems import run_baseline, run_pipeline
from optverify.verifier import build_report, decide, number_coverage, paraphrase_agreement
from tests.fake_llm import TOY_OPTIMUM, TOY_QUESTION, FakeLLM

TOY_PROBLEM = Problem("toy-0", TOY_QUESTION, TOY_OPTIMUM, "Production", 2, "test")


class NoCodeForRewordings(FakeLLM):
    """Solves the original question but returns no code for reworded ones, so every paraphrase run fails."""

    def complete(self, prompt: str, max_tokens: int = 4096) -> LLMReply:
        if "small factory" in prompt:
            self.prompts.append(prompt)
            return LLMReply("no code in this reply", TokenUsage(input_tokens=10, output_tokens=5, calls=1), 0.0)
        return super().complete(prompt, max_tokens)


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


def test_item_labels_are_not_data():
    question = "Package 1: size 33\nPackage 2: size 45\nPackage 3: size 4\nOnly 3 trucks are free."
    coverage, missing = number_coverage(question, "sizes = [33, 45, 4]\ntrucks = 3")
    assert coverage == 1.0 and missing == []
    # "Only 3" is not a label (one number only), so the 3 is still required.
    assert number_coverage(question, "sizes = [33, 45, 4]")[1] == ["3"]


def test_percentages_may_appear_as_fractions():
    assert number_coverage("loss is reduced by 24% and costs 7", "reduction = 0.24\ncost = 7") == (1.0, [])


def test_failed_paraphrase_runs_are_not_disagreements():
    assert paraphrase_agreement(570.0, [None, 570.0]) == 1.0
    assert paraphrase_agreement(570.0, [None, None]) is None
    assert paraphrase_agreement(570.0, [520.0, None]) == 0.0


def test_pipeline_retries_failed_paraphrase_runs_once():
    record = run_pipeline(TOY_PROBLEM, NoCodeForRewordings(), paraphrases=2)
    assert record.usage.calls == 10  # parse + formalize + 2 runs x 2 tries x (paraphrase + formalize)
    assert record.usage_by_step["paraphrase_1"].calls == 4  # the retry is counted in the same run's step
    assert record.verifier.paraphrase_objectives == [None, None]
    assert record.verifier.paraphrase_agreement is None
    assert record.decision.action == "answer" and record.correct  # coverage alone decides when no run succeeds
    assert any("returned no optimum" in reason for reason in record.decision.reasons)
