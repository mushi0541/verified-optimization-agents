from optverify.contracts import Decision, TokenUsage, VerifierReport
from optverify.roles import _first_json_object, explain, parse_problem
from tests.fake_llm import TOY_QUESTION, FakeLLM


def test_first_json_object_skips_reasoning_and_surrounding_text():
    text = '<think>maybe {"wrong": 1}</think>Here is the spec: {"objective_sense": "maximize"} Done.'
    assert _first_json_object(text) == {"objective_sense": "maximize"}


def test_first_json_object_returns_none_when_there_is_no_valid_json():
    assert _first_json_object("no braces here") is None
    assert _first_json_object("{not: valid json}") is None


def test_parser_counts_its_call():
    usage = TokenUsage()
    spec = parse_problem(TOY_QUESTION, FakeLLM(), usage)
    assert spec["objective_sense"] == "maximize"
    assert usage.calls == 1 and usage.input_tokens > 0


def _report(agreement: float | None) -> VerifierReport:
    return VerifierReport(True, 0.75, ["7"], agreement, [], 0.8)


def test_explain_gives_the_answer_and_the_checks():
    text = explain(Decision("answer", 570.0, ["A reason."]), _report(1.0))
    assert text.startswith("Recommended plan found. Optimal objective value: 570.")
    assert "number coverage 75%" in text and "reworded-question agreement 100%" in text and text.endswith("A reason.")


def test_explain_escalation_and_abstention():
    assert "analyst" in explain(Decision("escalate", 570.0, []), _report(None))
    assert "reworded" not in explain(Decision("escalate", 570.0, []), _report(None))  # no paraphrase runs, no agreement
    assert "not giving an answer" in explain(Decision("abstain", None, []), _report(None))
