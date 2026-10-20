import json

import pytest

from optverify.data import load_split, sample_per_class


def _write_split(tmp_path, rows):
    path = tmp_path / "canonical.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    return tmp_path


def _row(problem_class: str, answer="10", **extra) -> dict:
    return {"question": f"A {problem_class} question.", "answer": answer, "problem_class": problem_class, "size": "3", **extra}


def test_load_split_builds_problem_records(tmp_path):
    data_dir = _write_split(tmp_path, [_row("Knapsack", source="gen"), _row("TSP", answer="not a number")])
    first, second = load_split("canonical", data_dir)
    assert first.problem_id == "canonical-0000" and second.problem_id == "canonical-0001"
    assert first.answer == 10.0 and first.size == 3 and first.split == "canonical"
    assert first.meta == {"source": "gen"}  # fields outside the standard ones are kept
    assert second.answer is None  # an unreadable reference answer is stored as missing


def test_load_split_explains_missing_data(tmp_path):
    with pytest.raises(FileNotFoundError, match="download_data.py"):
        load_split("canonical", tmp_path)


def test_sample_per_class_is_balanced_and_repeatable(tmp_path):
    rows = [_row("Knapsack") for _ in range(6)] + [_row("TSP") for _ in range(4)] + [_row("Inventory")]
    problems = load_split("canonical", _write_split(tmp_path, rows))

    sample = sample_per_class(problems, per_class=2, seed=0)
    classes = [problem.problem_class for problem in sample]
    assert classes == ["Inventory", "Knapsack", "Knapsack", "TSP", "TSP"]  # sorted by class; a small class gives all it has
    assert [p.problem_id for p in sample] == [p.problem_id for p in sample_per_class(problems, 2, seed=0)]
    assert len({p.problem_id for p in sample}) == len(sample)  # no problem is drawn twice


def test_sample_canonical_and_linguistic(tmp_path):
    from optverify.data import sample_canonical, sample_linguistic

    rows = [_row("Knapsack") for _ in range(12)] + [_row("TSP") for _ in range(12)]
    problems = load_split("canonical", _write_split(tmp_path, rows))

    canonical_sample = sample_canonical(problems, per_class=10, seed=0)
    assert len(canonical_sample) == 20
    assert len([p for p in canonical_sample if p.problem_class == "Knapsack"]) == 10
    assert len([p for p in canonical_sample if p.problem_class == "TSP"]) == 10

    linguistic_sample = sample_linguistic(problems, per_class=5, seed=0)
    assert len(linguistic_sample) == 10


def test_sample_ablation_subset_is_strict_subset(tmp_path):
    from optverify.data import sample_ablation_subset, sample_canonical

    rows = [_row("Knapsack") for _ in range(15)] + [_row("TSP") for _ in range(15)]
    problems = load_split("canonical", _write_split(tmp_path, rows))

    canonical_sample = sample_canonical(problems, per_class=10, seed=0)
    ablation_sample = sample_ablation_subset(canonical_sample, per_class=3, seed=0)

    assert len(ablation_sample) == 6
    assert len([p for p in ablation_sample if p.problem_class == "Knapsack"]) == 3
    assert len([p for p in ablation_sample if p.problem_class == "TSP"]) == 3

    canonical_ids = {p.problem_id for p in canonical_sample}
    ablation_ids = {p.problem_id for p in ablation_sample}
    assert ablation_ids.issubset(canonical_ids)
    assert len(ablation_ids) < len(canonical_ids)
