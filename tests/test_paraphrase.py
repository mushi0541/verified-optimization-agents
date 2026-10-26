import json
from pathlib import Path

from optverify.verifier import combined_score, paraphrase_agreement

RESULTS = Path(__file__).resolve().parent.parent / "results"


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

