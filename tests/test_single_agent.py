from optverify.contracts import TokenUsage
from optverify.systems import majority_vote, run_baseline, run_single_agent, samples_within_budget
from tests.fake_llm import TOY_CODE, TOY_OPTIMUM, FakeLLM
from tests.test_verifier_and_systems import TOY_PROBLEM

OTHER_CODE = TOY_CODE.replace("50 * tables", "60 * tables")  # a wrong model with optimum 600


def _sample_tokens() -> int:
    usage = run_baseline(TOY_PROBLEM, FakeLLM()).usage
    return usage.input_tokens + usage.output_tokens


def test_majority_vote_and_agreement_score():
    assert majority_vote([570.0, 570.5, 600.0, None]) == (570.0, 0.5)  # 570 and 570.5 are the same optimum
    assert majority_vote([600.0, 570.0]) == (600.0, 0.5)  # a tie goes to the optimum found first
    assert majority_vote([None, None]) == (None, 0.0)
    assert majority_vote([]) == (None, 0.0)


def test_samples_within_budget_picks_the_closest_total():
    assert samples_within_budget([100, 100, 100], 260) == 3
    assert samples_within_budget([100, 100, 100], 250) == 2  # 200 and 300 are equally close: fewer samples
    assert samples_within_budget([100, 100, 100], 50) == 1  # always at least one sample
    assert samples_within_budget([100, 100, 100], 10_000) == 3


def test_sampling_stops_at_the_token_budget():
    tokens = _sample_tokens()
    record = run_single_agent(TOY_PROBLEM, FakeLLM(), FakeLLM(), token_budget=2.6 * tokens, max_repairs=1)
    assert len(record.samples) == 3  # 2 samples are below the budget, the third reaches it
    assert list(record.usage_by_step) == ["sample_1", "sample_2", "sample_3"]
    assert record.usage == TokenUsage.total(record.usage_by_step)
    assert record.token_budget == 2.6 * tokens

    capped = run_single_agent(TOY_PROBLEM, FakeLLM(), FakeLLM(), token_budget=100 * tokens, max_samples=4)
    assert len(capped.samples) == 4

    one = run_single_agent(TOY_PROBLEM, FakeLLM(), FakeLLM(), token_budget=1)
    assert len(one.samples) == 1  # sample 1 (B1) is always drawn


def test_first_sample_is_b1_and_later_samples_use_the_sampling_model():
    first, later = FakeLLM(), FakeLLM()
    record = run_single_agent(TOY_PROBLEM, first, later, token_budget=2.6 * _sample_tokens())
    assert len(first.prompts) == 1 and len(later.prompts) == 2
    assert record.attempts == record.samples[0]
    assert record.decision.action == "answer" and record.correct
    assert record.sample_agreement == 1.0


def test_disagreeing_samples_are_escalated():
    first, later = FakeLLM(), FakeLLM(code_reply=OTHER_CODE)
    record = run_single_agent(TOY_PROBLEM, first, later, token_budget=2.6 * _sample_tokens())
    assert record.predicted == 600.0 and not record.correct  # 2 of 3 samples reach the wrong optimum
    assert abs(record.sample_agreement - 2 / 3) < 1e-9
    assert record.decision.action == "escalate"
    assert "2 of 3" in record.decision.reasons[0]
    assert all(str(TOY_OPTIMUM) not in prompt for prompt in first.prompts + later.prompts)  # no answer leak


def test_abstains_when_no_sample_is_optimal():
    broken = FakeLLM(code_reply="no code in this reply")
    record = run_single_agent(TOY_PROBLEM, broken, broken, token_budget=1, max_repairs=1)
    assert record.decision.action == "abstain" and record.sample_agreement == 0.0
    assert len(record.samples[0]) == 2  # first try plus one repair, as in B1

