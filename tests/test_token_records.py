import json
from pathlib import Path

from optverify.contracts import TokenUsage
from optverify.grading import summarize
from optverify.systems import run_baseline, run_pipeline
from tests.fake_llm import FakeLLM
from tests.test_verifier_and_systems import TOY_PROBLEM


def _sum_of_steps(record_json: dict) -> dict:
    keys = ("input_tokens", "output_tokens", "calls")
    return {key: sum(step[key] for step in record_json["usage_by_step"].values()) for key in keys}


def test_total_adds_up_steps():
    total = TokenUsage.total({"a": TokenUsage(10, 5, 1), "b": TokenUsage(3, 2, 1)})
    assert total == TokenUsage(13, 7, 2)
    assert TokenUsage.total({}) == TokenUsage()


def test_pipeline_records_tokens_per_step():
    record = run_pipeline(TOY_PROBLEM, FakeLLM(), paraphrases=2)
    assert list(record.usage_by_step) == ["parse", "formalize", "repair", "paraphrase_1", "paraphrase_2"]
    assert record.usage_by_step["repair"].calls == 0  # the first model is optimal, so no repair
    assert record.usage_by_step["paraphrase_1"].calls == 2  # paraphraser call plus its formalizer call

    saved = json.loads(json.dumps(record.to_json()))  # as written to records.jsonl
    assert _sum_of_steps(saved) == saved["usage"]


def test_baseline_records_formalize_and_repair_steps():
    record = run_baseline(TOY_PROBLEM, FakeLLM(code_reply="no code in this reply"), max_repairs=2)
    assert list(record.usage_by_step) == ["formalize", "repair"]
    assert record.usage_by_step["formalize"].calls == 1
    assert record.usage_by_step["repair"].calls == 2
    assert _sum_of_steps(record.to_json()) == record.to_json()["usage"]


def test_phase1_records_without_steps_still_summarize():
    path = next(Path(__file__).resolve().parent.parent.glob("results/pipeline_*_20261017-1424/records.jsonl"))
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert all("usage_by_step" not in record for record in records)
    assert summarize(records)["problems"] == len(records)
