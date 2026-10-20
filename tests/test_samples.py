import hashlib
import json
from pathlib import Path
import pytest


from optverify.data import DATA_DIR

DATA_READY = all(
    (DATA_DIR / name).exists()
       for name in ("canonical.jsonl", "linguistic_complexity.jsonl", "constraint_augmentation.jsonl")
   )
needs_data = pytest.mark.skipif(
       not DATA_READY,
       reason="Benchmark data missing. Run: python scripts/download_data.py",
   )
from optverify.data import (
    DATA_DIR,
    knapsack_item_key,
    load_sample_file,
    load_split,
    tsp_distance_set,
)
from scripts.make_samples import generate_samples

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def test_canonical_sample_integrity():
    canonical_file = SAMPLES_DIR / "canonical_100.json"
    ids = json.loads(canonical_file.read_text(encoding="utf-8"))
    assert len(ids) == 100
    assert len(set(ids)) == 100

    problems = load_sample_file(canonical_file)
    assert len(problems) == 100

    by_class: dict[str, int] = {}
    for problem in problems:
        assert problem.split == "canonical"
        assert problem.question.strip()
        by_class[problem.problem_class] = by_class.get(problem.problem_class, 0) + 1

    assert len(by_class) == 10
    assert all(count == 10 for count in by_class.values())


def test_linguistic_sample_integrity():
    linguistic_file = SAMPLES_DIR / "linguistic_30.json"
    ids = json.loads(linguistic_file.read_text(encoding="utf-8"))
    assert len(ids) == 30
    assert len(set(ids)) == 30

    problems = load_sample_file(linguistic_file)
    assert len(problems) == 30

    by_class: dict[str, int] = {}
    for problem in problems:
        assert problem.split == "linguistic"
        assert problem.question.strip()
        by_class[problem.problem_class] = by_class.get(problem.problem_class, 0) + 1

    assert set(by_class.keys()) == {"Inventory", "Knapsack", "TSP"}
    assert all(count == 10 for count in by_class.values())


def test_ablation_sample_integrity():
    canonical_file = SAMPLES_DIR / "canonical_100.json"
    ablation_file = SAMPLES_DIR / "ablation_30.json"

    canonical_ids = set(json.loads(canonical_file.read_text(encoding="utf-8")))
    ablation_ids = json.loads(ablation_file.read_text(encoding="utf-8"))

    assert len(ablation_ids) == 30
    assert len(set(ablation_ids)) == 30
    assert set(ablation_ids).issubset(canonical_ids)
    assert len(set(ablation_ids)) < len(canonical_ids)

    problems = load_sample_file(ablation_file)
    assert len(problems) == 30

    by_class: dict[str, int] = {}
    for problem in problems:
        assert problem.split == "canonical"
        by_class[problem.problem_class] = by_class.get(problem.problem_class, 0) + 1

    assert len(by_class) == 10
    assert all(count == 3 for count in by_class.values())


def test_constraint_pairs_integrity():
    constraint_file = SAMPLES_DIR / "constraint_pairs_30.json"
    pairs = json.loads(constraint_file.read_text(encoding="utf-8"))
    assert len(pairs) == 30

    constraint_problems = {p.problem_id: p for p in load_split("constraint", data_dir=DATA_DIR)}
    used_augmented_ids: set[str] = set()

    by_class: dict[str, int] = {}
    for idx, pair in enumerate(pairs):
        assert pair["pair_id"] == idx
        assert sorted(pair.keys()) == ["augmented", "original", "pair_id", "pairing", "problem_class"]

        p_class = pair["problem_class"]
        by_class[p_class] = by_class.get(p_class, 0) + 1

        orig_id = pair["original"]
        aug_id = pair["augmented"]
        assert orig_id in constraint_problems
        assert aug_id in constraint_problems

        orig = constraint_problems[orig_id]
        aug = constraint_problems[aug_id]

        assert orig.problem_class == p_class
        assert aug.problem_class == p_class
        assert orig.size == aug.size
        assert orig.meta.get("constraint_type") == "original"
        assert aug.meta.get("constraint_type") == "augmented"

        assert aug_id not in used_augmented_ids
        used_augmented_ids.add(aug_id)

        if p_class == "Inventory":
            assert pair["pairing"] == "class_and_size"
        elif p_class == "Knapsack":
            assert pair["pairing"] == "matched_data"
            assert knapsack_item_key(orig) == knapsack_item_key(aug)
        elif p_class == "TSP":
            assert pair["pairing"] == "matched_data"
            orig_dists = tsp_distance_set(orig)
            aug_dists = tsp_distance_set(aug)
            assert aug_dists.issubset(orig_dists)
            assert len(orig_dists - aug_dists) == 1
        else:
            raise AssertionError(f"Unexpected class {p_class}")

    assert set(by_class.keys()) == {"Inventory", "Knapsack", "TSP"}
    assert all(count == 10 for count in by_class.values())


def test_sample_files_formatting():
    for name in ["canonical_100.json", "ablation_30.json", "linguistic_30.json", "constraint_pairs_30.json"]:
        file_path = SAMPLES_DIR / name
        raw_bytes = file_path.read_bytes().replace(b"\r\n", b"\n")
        assert raw_bytes.endswith(b"\n")
        assert b"\r" not in raw_bytes

        # Verify 2-space indentation and sorted keys
        data = json.loads(raw_bytes.decode("utf-8"))
        formatted = json.dumps(data, indent=2, sort_keys=True) + "\n"
        assert raw_bytes.decode("utf-8") == formatted


def test_sample_generation_determinism_via_hashes(tmp_path):
    generated = generate_samples(output_dir=tmp_path, data_dir=DATA_DIR)

    for name in ["canonical_100.json", "ablation_30.json", "linguistic_30.json", "constraint_pairs_30.json"]:
        checked_in = SAMPLES_DIR / name
        new_file = tmp_path / name

        hash_checked_in = hashlib.sha256(checked_in.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        hash_new = hashlib.sha256(new_file.read_bytes()).hexdigest()

        assert hash_new == hash_checked_in, f"Hash mismatch for {name}: {hash_new} != {hash_checked_in}"
