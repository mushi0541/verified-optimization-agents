"""Tests for the requirement coverage signal (Gap 1): requirement IDs, constraint names and the score."""

import pytest

from optverify.contracts import Decision, Problem, TokenUsage
from optverify.roles import explain, number_requirements, parse_problem
from optverify.solver_tool import run_model_code
from optverify.systems import run_baseline, run_pipeline
from optverify.verifier import build_report, combined_score, decide, requirement_coverage
from tests.fake_llm import TOY_CODE, TOY_OPTIMUM, TOY_QUESTION, FakeLLM

TOY_PROBLEM = Problem("toy-1", TOY_QUESTION, TOY_OPTIMUM, "Toy", 2, "canonical")
CODE = TOY_CODE.removeprefix("```python\n").removesuffix("```")


def test_requirements_get_ids_in_order():
    spec, ids = number_requirements({"objective": "cost", "requirements": ["a <= 1", "b >= 2"]})
    assert ids == ["R1", "R2"]
    assert spec["requirements"] == {"R1": "a <= 1", "R2": "b >= 2"}
    assert spec["objective"] == "cost"


@pytest.mark.parametrize("spec", [None, {}, {"requirements": []}, {"requirements": "a <= 1"}])
def test_no_requirement_list_gives_no_ids(spec):
    assert number_requirements(spec) == (spec, [])


def test_solver_reports_requirement_ids_from_constraint_names():
    code = """import pulp
model = pulp.LpProblem("ids", pulp.LpMinimize)
x = pulp.LpVariable("x", lowBound=0)
y = pulp.LpVariable("y", lowBound=0)
model += x + y
model += x >= 1, "R10_min_x"
model += y >= 1, "R1_R2_min_y"
model += x + y >= 3, "capacity_R3"
model += x <= 50, "xR4_not_an_id"
model += y <= 50
model.solve(pulp.HiGHS(msg=False))
"""
    result = run_model_code(code)
    assert result.status == "optimal"
    assert result.requirement_ids == ["R1", "R2", "R3", "R10"]  # sorted by number, R4 is not a separate word
    assert "REQUIREMENTS" not in result.stdout


def test_model_without_named_constraints_links_nothing():
    code = CODE.replace(', "R1_work_hours"', "").replace(', "R2_min_tables"', "")
    assert run_model_code(code).requirement_ids == []


def test_coverage_is_the_share_of_linked_requirements():
    assert requirement_coverage(["R1", "R2", "R3", "R4"], ["R1", "R3", "R9"]) == (0.5, ["R2", "R4"])
    assert requirement_coverage(["R1"], ["R1"]) == (1.0, [])
    assert requirement_coverage([], ["R1"]) == (None, [])


def test_score_is_the_mean_of_the_available_signals():
    assert combined_score(True, 1.0, 1.0, 0.4) == pytest.approx(0.8)
    assert combined_score(True, 1.0, None, 0.5) == pytest.approx(0.75)
    assert combined_score(True, 0.6, 1.0) == pytest.approx(0.8)  # records without the signal score as before
    assert combined_score(False, 1.0, 1.0, 1.0) == 0.0


def test_missing_requirements_are_reported_and_explained():
    report = build_report(TOY_QUESTION, "30 50 2 4 40 3", "optimal", 570.0, [570.0], ["R1", "R2"], ["R1"])
    assert report.requirement_coverage == 0.5 and report.missing_requirements == ["R2"]
    assert report.score == pytest.approx((1.0 + 1.0 + 0.5) / 3)

    decision = decide(report, 570.0, threshold=0.9)
    assert decision.action == "escalate"
    assert "Requirements not linked to any named constraint: R2." in decision.reasons
    text = explain(decision, report)
    assert "requirement coverage 50%" in text and "R2" in text


def test_explainer_leaves_out_the_signal_when_there_are_no_requirements():
    report = build_report(TOY_QUESTION, "30 50 2 4 40 3", "optimal", 570.0, [570.0])
    assert report.requirement_coverage is None
    assert "requirement" not in explain(Decision("answer", 570.0, []), report)


class FailsOnce(FakeLLM):
    """Returns code that crashes on the first formalizer call, then the toy model."""

    def complete(self, prompt, max_tokens=4096):
        reply = super().complete(prompt, max_tokens)
        if reply.text == TOY_CODE and not any("Your script for the optimization problem" in p for p in self.prompts):
            reply.text = "```python\nraise ValueError('broken')\n```"
        return reply


def test_only_the_pipeline_repair_asks_to_keep_constraint_names():
    llm = FailsOnce()
    record = run_pipeline(TOY_PROBLEM, llm, paraphrases=0, max_repairs=1)
    repair_prompt = next(p for p in llm.prompts if "Your script for the optimization problem" in p)
    assert "Keep the constraint names" in repair_prompt
    assert record.verifier.requirement_coverage == 1.0

    llm = FailsOnce()
    run_baseline(TOY_PROBLEM, llm, max_repairs=1)
    repair_prompt = next(p for p in llm.prompts if "Your script for the optimization problem" in p)
    assert "Keep the constraint names" not in repair_prompt
    assert "models the problem correctly and runs.\n" in repair_prompt  # the baseline prompt is unchanged


class BadJsonOnce(FakeLLM):
    """The first parser reply is cut off, as when it runs out of output tokens."""

    def complete(self, prompt, max_tokens=4096):
        reply = super().complete(prompt, max_tokens)
        if "Return only a JSON object" in prompt and sum("Return only a JSON object" in p for p in self.prompts) == 1:
            reply.text = reply.text[:40]
        return reply


def test_parser_retries_once_with_a_large_output_cap():
    llm = BadJsonOnce()
    usage = TokenUsage()
    spec = parse_problem(TOY_QUESTION, llm, usage)
    assert spec["requirements"] == ["work hours <= 40", "tables >= 3"]
    assert usage.calls == 2 and len(llm.prompts) == 2


def test_pipeline_records_requirement_coverage():
    llm = FakeLLM()
    record = run_pipeline(TOY_PROBLEM, llm, paraphrases=1)
    assert record.spec["requirements"] == {"R1": "work hours <= 40", "R2": "tables >= 3"}
    assert '"R1": "work hours <= 40"' in llm.prompts[1]  # the formalizer sees the IDs
    assert record.attempts[-1].solve.requirement_ids == ["R1", "R2"]
    assert record.verifier.requirement_coverage == 1.0 and record.decision.action == "answer"

    unnamed = FakeLLM(TOY_CODE.replace(', "R2_min_tables"', ""))
    record = run_pipeline(TOY_PROBLEM, unnamed, paraphrases=1)
    assert record.verifier.missing_requirements == ["R2"]
    assert record.verifier.score == pytest.approx((1.0 + 1.0 + 0.5) / 3)
