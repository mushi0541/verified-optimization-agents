import json
from pathlib import Path

import pytest

from optverify import interactive
from optverify import run as run_module
from optverify.run import paraphrase_client, parse_args
from optverify.systems import PARAPHRASE_TEMPERATURE, run_pipeline
from optverify.verifier import combined_score, paraphrase_agreement
from tests.fake_llm import FakeLLM
from tests.test_verifier_and_systems import TOY_PROBLEM

RESULTS = Path(__file__).resolve().parent.parent / "results"
PARAPHRASER_PROMPT = "Rewrite the optimization problem"


def test_agreement_treats_a_value_and_its_negative_as_the_same_optimum():
    assert paraphrase_agreement(1908.17, [-1908.17, 1908.17]) == 1.0
    assert paraphrase_agreement(-570.0, [570.4]) == 1.0  # within the 0.2% tolerance, either sign
    assert paraphrase_agreement(570.0, [-600.0, 600.0]) == 0.0  # a different value stays a disagreement
    assert paraphrase_agreement(570.0, [None, -570.0]) == 1.0  # failed runs are still left out
    assert paraphrase_agreement(570.0, [None]) is None


def test_agreement_at_zero():
    assert paraphrase_agreement(0.0, [0.0, -0.0]) == 1.0
    assert paraphrase_agreement(0.0, [5.0]) == 0.0
    assert paraphrase_agreement(0.0, [-5.0]) == 0.0


def test_phase1_production_false_alarm_is_now_answered():
    path = next(RESULTS.glob("pipeline_bedrock*_canonical_r1_20261020-1634/records.jsonl"))
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    production = next(r for r in records if r["problem_class"] == "Production")
    report = production["verifier"]
    assert production["correct"] and production["decision"]["action"] == "escalate"  # as saved in Phase 1
    assert report["paraphrase_objectives"] == [1908.1704221829584, -1908.1704221829584]

    objective = production["attempts"][-1]["solve"]["objective"]
    agreement = paraphrase_agreement(objective, report["paraphrase_objectives"])
    assert agreement == 1.0
    assert combined_score(True, report["number_coverage"], agreement) >= 0.8  # answered at the Phase 1 threshold


def test_pipeline_rewords_with_the_paraphrase_client_only():
    main, paraphraser = FakeLLM(), FakeLLM()
    record = run_pipeline(TOY_PROBLEM, main, paraphrases=2, paraphrase_llm=paraphraser)
    assert len(paraphraser.prompts) == 2 and all(PARAPHRASER_PROMPT in prompt for prompt in paraphraser.prompts)
    assert not any(PARAPHRASER_PROMPT in prompt for prompt in main.prompts)  # parse, formalize and reworded formalize
    assert len(main.prompts) == 4
    assert record.usage_by_step["paraphrase_1"].calls == 2  # the paraphraser call still counts in its run's step
    assert record.decision.action == "answer"


def test_pipeline_without_a_paraphrase_client_uses_the_main_client():
    main = FakeLLM()
    run_pipeline(TOY_PROBLEM, main, paraphrases=2)
    assert sum(PARAPHRASER_PROMPT in prompt for prompt in main.prompts) == 2


def test_cli_records_the_paraphrase_temperature():
    assert parse_args(["pipeline", "--model", "dummy"]).paraphrase_temperature == PARAPHRASE_TEMPERATURE == 0.7
    assert parse_args(["pipeline", "--model", "dummy", "--paraphrase-temperature", "0.3"]).paraphrase_temperature == 0.3


def test_interface_rewords_at_the_paraphrase_temperature(monkeypatch):
    seen = {}

    def fake_run_pipeline(problem, llm, **settings):
        seen.update(settings, main_llm=llm)

    monkeypatch.setattr(interactive, "run_pipeline", fake_run_pipeline)
    main = FakeLLM()
    interactive.solve_interactive_problem("Maximize 3x with x <= 4.", main)
    assert seen["paraphrase_llm"].temperature == PARAPHRASE_TEMPERATURE
    assert seen["main_llm"] is main and not hasattr(main, "temperature")  # the main client is left unchanged


def test_paraphrase_model_defaults_to_the_main_model():
    args = parse_args(["pipeline", "--model", "dummy"])
    assert args.paraphrase_model is None
    main = FakeLLM()
    client = paraphrase_client(args, main, make=lambda spec: pytest.fail("no second model was asked for"))
    assert client is not main and client.temperature == PARAPHRASE_TEMPERATURE
    assert not hasattr(main, "temperature")  # the main client is left unchanged


def test_a_second_paraphrase_model_rewords_and_the_main_model_solves():
    args = parse_args(["pipeline", "--model", "dummy", "--paraphrase-model", "bedrock:deepseek.v3.2"])
    main, second, asked = FakeLLM(), FakeLLM(), []

    def make(spec):
        asked.append(spec)
        return second

    paraphraser = paraphrase_client(args, main, make=make)
    assert asked == ["bedrock:deepseek.v3.2"] and paraphraser.temperature == PARAPHRASE_TEMPERATURE
    record = run_pipeline(TOY_PROBLEM, main, paraphrases=2, paraphrase_llm=paraphraser)
    assert len(second.prompts) == 2 and all(PARAPHRASER_PROMPT in prompt for prompt in second.prompts)
    assert not any(PARAPHRASER_PROMPT in prompt for prompt in main.prompts)  # rewordings are solved by the main model
    assert record.model == main.name and record.decision.action == "answer"


def test_the_run_records_the_paraphrase_model_and_its_endpoint(tmp_path, monkeypatch):
    made = []

    def fake_make_llm(spec, temperature=0.0):
        made.append(spec)
        return FakeLLM()

    monkeypatch.setattr(run_module, "make_llm", fake_make_llm)
    monkeypatch.setattr(run_module, "RESULTS_DIR", tmp_path)
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    argv = ["run", "pipeline", "--model", "bedrock:openai.gpt-oss-120b-1:0", "--paraphrase-model", "bedrock:deepseek.v3.2",
            "--split", "opsor", "--per-class", "1", "--paraphrases", "1", "--workers", "1", "--env-file", str(tmp_path / "none")]
    monkeypatch.setattr("sys.argv", argv)
    run_module.main()

    assert made == ["bedrock:openai.gpt-oss-120b-1:0", "bedrock:deepseek.v3.2"]
    (folder,) = tmp_path.iterdir()
    assert "_para-bedrock-deepseek.v3.2_" in folder.name  # the two paraphraser settings never share a folder name
    config = json.loads((folder / "summary.json").read_text(encoding="utf-8"))["config"]
    assert config["paraphrase_model"] == "bedrock:deepseek.v3.2"
    assert config["paraphrase_endpoint"] == "bedrock us-east-1" and config["endpoint"] == "bedrock us-east-1"


def test_only_the_pipeline_builds_a_second_paraphrase_client(tmp_path, monkeypatch):
    made = []

    def fake_make_llm(spec, temperature=0.0):
        made.append(spec)
        return FakeLLM()

    monkeypatch.setattr(run_module, "make_llm", fake_make_llm)
    monkeypatch.setattr(run_module, "RESULTS_DIR", tmp_path)
    argv = ["run", "baseline", "--model", "bedrock:openai.gpt-oss-120b-1:0", "--paraphrase-model", "bedrock:deepseek.v3.2",
            "--split", "opsor", "--per-class", "1", "--workers", "1", "--env-file", str(tmp_path / "none")]
    monkeypatch.setattr("sys.argv", argv)
    run_module.main()

    assert made == ["bedrock:openai.gpt-oss-120b-1:0"]  # no unused second client for a baseline run
    (folder,) = tmp_path.iterdir()
    assert "_para-" not in folder.name
    config = json.loads((folder / "summary.json").read_text(encoding="utf-8"))["config"]
    assert config["paraphrase_endpoint"] is None
