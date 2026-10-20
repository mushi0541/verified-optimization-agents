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


def test_constraint_pairing_logic():
    from optverify.contracts import Problem
    from optverify.data import match_inventory_pairs, match_knapsack_pairs, match_tsp_pairs, sample_constraint_pairs

    # Knapsack pair: identical items and capacity
    k_orig_q = "Packages:\n* Item A: size 10 units, revenue 20 credits\n* Item B: size 15 units, revenue 30 credits\nCapacity of 50 units."
    k_aug_q = "Items:\n* Crate A: weight 10kg, profit 20 units\n* Crate B: weight 15kg, profit 30 units\nExtra constraint.\nVehicle payload limit of 50."
    k_orig = Problem("constraint-0001", k_orig_q, 50.0, "Knapsack", 2, "constraint", {"constraint_type": "original"})
    k_aug = Problem("constraint-0501", k_aug_q, 45.0, "Knapsack", 2, "constraint", {"constraint_type": "augmented"})

    # TSP pair: 3-node graph with 3 edges in orig, 2 edges in aug (1 forbidden)
    t_orig_q = "Stations:\nA to B: 10.0\nA to C: 20.0\nB to C: 30.0"
    t_aug_q = "Stations:\nA to B: 10.0\nB to C: 30.0\nPath A to C is forbidden."
    t_orig = Problem("constraint-0002", t_orig_q, 60.0, "TSP", 3, "constraint", {"constraint_type": "original"})
    t_aug = Problem("constraint-0502", t_aug_q, 70.0, "TSP", 3, "constraint", {"constraint_type": "augmented"})

    # Inventory pair: same class and size
    i_orig = Problem("constraint-0003", "Inv orig question", 100.0, "Inventory", 5, "constraint", {"constraint_type": "original"})
    i_aug = Problem("constraint-0503", "Inv aug question", 120.0, "Inventory", 5, "constraint", {"constraint_type": "augmented"})

    problems = [k_orig, k_aug, t_orig, t_aug, i_orig, i_aug]

    kp = match_knapsack_pairs(problems)
    assert len(kp) == 1
    assert kp[0]["original"] == "constraint-0001" and kp[0]["augmented"] == "constraint-0501"
    assert kp[0]["pairing"] == "matched_data"

    tp = match_tsp_pairs(problems)
    assert len(tp) == 1
    assert tp[0]["original"] == "constraint-0002" and tp[0]["augmented"] == "constraint-0502"
    assert tp[0]["pairing"] == "matched_data"

    ip = match_inventory_pairs(problems, seed=0)
    assert len(ip) == 1
    assert ip[0]["original"] == "constraint-0003" and ip[0]["augmented"] == "constraint-0503"
    assert ip[0]["pairing"] == "class_and_size"

    sampled = sample_constraint_pairs(problems, per_class=1, seed=0)
    assert len(sampled) == 3
    assert [p["pair_id"] for p in sampled] == [0, 1, 2]


def test_save_and_load_sample_file(tmp_path):
    from optverify.data import load_sample_file, save_sample_file

    rows = [_row("Knapsack", answer="10"), _row("TSP", answer="20")]
    data_dir = _write_split(tmp_path, rows)

    # Test saving and loading a simple list of IDs
    sample_path = tmp_path / "sample_test.json"
    ids = ["canonical-0001", "canonical-0000"]
    save_sample_file(sample_path, ids)

    # Check formatting: 2-space indent, trailing newline, valid json
    raw = sample_path.read_bytes()
    assert raw.endswith(b"\n")
    assert b"\r" not in raw  # Unix line endings "\n"

    problems = load_sample_file(sample_path, data_dir=data_dir)
    assert len(problems) == 2
    assert [p.problem_id for p in problems] == ["canonical-0001", "canonical-0000"]
    assert problems[0].problem_class == "TSP"
    assert problems[1].problem_class == "Knapsack"

    # Test loading pair dicts loads both original and augmented
    pair_path = tmp_path / "pairs_test.json"
    pairs = [{"augmented": "canonical-0001", "original": "canonical-0000", "pair_id": 0, "pairing": "matched_data", "problem_class": "Knapsack"}]
    save_sample_file(pair_path, pairs)
    pair_problems = load_sample_file(pair_path, data_dir=data_dir)
    assert len(pair_problems) == 2
    assert [p.problem_id for p in pair_problems] == ["canonical-0000", "canonical-0001"]

    # Test error handling on bad json structure or missing ID
    bad_path = tmp_path / "bad.json"
    bad_path.write_text('{"not": "a list"}', encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a list"):
        load_sample_file(bad_path, data_dir=data_dir)

    missing_id_path = tmp_path / "missing.json"
    save_sample_file(missing_id_path, ["canonical-9999"])
    with pytest.raises(KeyError, match="canonical-9999"):
        load_sample_file(missing_id_path, data_dir=data_dir)
