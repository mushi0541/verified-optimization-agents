"""Tests for scripts/failure_analysis.py (synthetic records, no API calls)."""

import csv
import json

import pytest

from scripts.failure_analysis import draft, table


def _record(pid, cls, action, correct, status="optimal", predicted=10.0, reference=10.0, sense="LpMinimize", **report):
    code = f"model = pulp.LpProblem('m', pulp.{sense})"
    return {
        "problem_id": pid,
        "problem_class": cls,
        "reference": reference,
        "predicted": predicted,
        "correct": correct,
        "attempts": [{"code": code, "solve": {"status": status}}],
        "spec": {"objective_sense": "minimize"},
        "verifier": {"paraphrase_agreement": 1.0, "missing_requirements": [], **report},
        "decision": {"action": action, "reasons": ["a reason"] if action != "answer" else []},
    }


@pytest.fixture
def run(tmp_path):
    records = [
        _record("p1", "Knapsack", "answer", True),  # success: no row
        _record("p2", "Knapsack", "answer", False, predicted=8.0),  # wrong accept, below the reference while minimizing
        _record("p3", "Inventory", "escalate", False, predicted=12.0),  # correct refusal, doubtful class
        _record("p4", "TSP", "abstain", False, status="infeasible", predicted=None),
        _record("p5", "TSP", "abstain", False, status="error", predicted=None),
        _record("p6", "TSP", "escalate", True, paraphrase_agreement=0.5),  # false alarm
        {"problem_id": "p7", "failed": "connection error"},
    ]
    folder = tmp_path / "run"
    folder.mkdir()
    (folder / "summary.json").write_text(json.dumps({"config": {"sample_file": "samples/canonical_200.json"}}))
    (folder / "records.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return folder / "records.jsonl"


def test_draft_rows_evidence_and_automatic_labels(run, tmp_path):
    rows = {row["problem_id"]: row for row in draft([run], tmp_path / "labels.csv")}
    assert sorted(rows) == ["p2", "p3", "p4", "p5", "p6"]
    assert rows["p2"]["outcome"] == "wrong accept"
    assert (rows["p2"]["direction"], rows["p2"]["code_sense"], rows["p2"]["relative_gap"]) == ("looser", "minimize", -0.2)
    assert rows["p3"]["outcome"] == "correct refusal" and rows["p3"]["direction"] == "tighter"
    assert rows["p3"]["doubtful_reference_class"] == "yes"
    assert rows["p4"]["label"] == "infeasible model"
    assert rows["p5"]["label"] == "code error"
    assert (rows["p6"]["outcome"], rows["p6"]["label"]) == ("false alarm", "paraphrase disagreement")
    assert rows["p2"]["label"] == rows["p3"]["label"] == ""
    assert all(row["sample"] == "canonical_200" for row in rows.values())


def test_table_needs_every_label_then_counts(run, tmp_path):
    labels = tmp_path / "labels.csv"
    draft([run], labels)
    with pytest.raises(SystemExit, match="label ''"):
        table(labels, [run], tmp_path / "out")

    with labels.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        row["label"] = row["label"] or "missing constraint"
    with labels.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    result = table(labels, [run], tmp_path / "out")
    assert result["outcomes"]["canonical_200"] == {
        "problems": 6, "wrong accept": 1, "correct refusal": 3, "false alarm": 1,
    }
    assert result["wrong_by_label"]["missing constraint"] == {"wrong accept": 1, "correct refusal": 1}
    assert result["wrong_by_label"]["code error"]["correct refusal"] == 1
    assert result["false_alarms_by_signal"]["paraphrase disagreement"] == 1
    assert "| missing constraint | 1 | 1 | 2 | 50.0% |" in (tmp_path / "out" / "failures.md").read_text(encoding="utf-8")


def test_table_refuses_a_label_file_from_other_records(run, tmp_path):
    labels = tmp_path / "labels.csv"
    draft([run], labels)
    with labels.open(encoding="utf-8") as file:
        rows = [row for row in csv.DictReader(file) if row["problem_id"] != "p2"]
    for row in rows:
        row["label"] = row["label"] or "other"
    with labels.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(SystemExit, match="does not match the records"):
        table(labels, [run], tmp_path / "out")
