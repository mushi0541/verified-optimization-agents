import hashlib
import json
from pathlib import Path

import pytest

from optverify.data import (
    DATA_DIR,
    knapsack_item_key,
    load_sample_file,
    load_split,
    tsp_distance_set,
)
from scripts.make_samples import generate_samples

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
SAMPLE_FILES = [
    "canonical_100.json", "canonical_200.json", "ablation_30.json", "ablation_50.json", "linguistic_30.json",
    "linguistic_60.json", "constraint_pairs_30.json", "constraint_pairs_60.json", "dev_30.json",
    "canonical_587.json", "dev_93.json",
]


def _ids(name: str) -> list:
    return json.loads((SAMPLES_DIR / name).read_text(encoding="utf-8"))


def _pair_ids(name: str) -> set[str]:
    return {pair[key] for pair in _ids(name) for key in ("original", "augmented")}


@pytest.mark.parametrize("name, per_class", [("canonical_100.json", 10), ("canonical_200.json", 20)])
def test_canonical_sample_integrity(name, per_class):
    canonical_file = SAMPLES_DIR / name
    ids = json.loads(canonical_file.read_text(encoding="utf-8"))
    assert len(ids) == 10 * per_class
    assert len(set(ids)) == 10 * per_class

    problems = load_sample_file(canonical_file)
    assert len(problems) == 10 * per_class

    by_class: dict[str, int] = {}
    for problem in problems:
        assert problem.split == "canonical"
        assert problem.question.strip()
        by_class[problem.problem_class] = by_class.get(problem.problem_class, 0) + 1

    assert len(by_class) == 10
    assert all(count == per_class for count in by_class.values())


@pytest.mark.parametrize("name, per_class", [("linguistic_30.json", 10), ("linguistic_60.json", 20)])
def test_linguistic_sample_integrity(name, per_class):
    linguistic_file = SAMPLES_DIR / name
    ids = json.loads(linguistic_file.read_text(encoding="utf-8"))
    assert len(ids) == 3 * per_class
    assert len(set(ids)) == 3 * per_class

    problems = load_sample_file(linguistic_file)
    assert len(problems) == 3 * per_class

    by_class: dict[str, int] = {}
    for problem in problems:
        assert problem.split == "linguistic"
        assert problem.question.strip()
        by_class[problem.problem_class] = by_class.get(problem.problem_class, 0) + 1

    assert set(by_class.keys()) == {"Inventory", "Knapsack", "TSP"}
    assert all(count == per_class for count in by_class.values())


@pytest.mark.parametrize("name, per_class", [("ablation_30.json", 3), ("ablation_50.json", 5)])
def test_ablation_sample_integrity(name, per_class):
    canonical_file = SAMPLES_DIR / "canonical_100.json"
    ablation_file = SAMPLES_DIR / name

    canonical_ids = set(json.loads(canonical_file.read_text(encoding="utf-8")))
    ablation_ids = json.loads(ablation_file.read_text(encoding="utf-8"))

    assert len(ablation_ids) == 10 * per_class
    assert len(set(ablation_ids)) == 10 * per_class
    assert set(ablation_ids).issubset(canonical_ids)
    assert len(set(ablation_ids)) < len(canonical_ids)

    problems = load_sample_file(ablation_file)
    assert len(problems) == 10 * per_class

    by_class: dict[str, int] = {}
    for problem in problems:
        assert problem.split == "canonical"
        by_class[problem.problem_class] = by_class.get(problem.problem_class, 0) + 1

    assert len(by_class) == 10
    assert all(count == per_class for count in by_class.values())


@pytest.mark.parametrize("name, per_class", [("constraint_pairs_30.json", 10), ("constraint_pairs_60.json", 20)])
def test_constraint_pairs_integrity(name, per_class):
    constraint_file = SAMPLES_DIR / name
    pairs = json.loads(constraint_file.read_text(encoding="utf-8"))
    assert len(pairs) == 3 * per_class

    constraint_problems = {p.problem_id: p for p in load_split("constraint", data_dir=DATA_DIR)}
    used_augmented_ids: set[str] = set()
    used_original_ids: set[str] = set()

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
        assert orig_id not in used_original_ids
        used_augmented_ids.add(aug_id)
        used_original_ids.add(orig_id)

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
    assert all(count == per_class for count in by_class.values())


@pytest.mark.parametrize(
    "small, large", [
        ("canonical_100.json", "canonical_200.json"),
        ("ablation_30.json", "ablation_50.json"),
        ("linguistic_30.json", "linguistic_60.json"),
        ("constraint_pairs_30.json", "constraint_pairs_60.json"),
        ("canonical_200.json", "canonical_587.json"),
        ("dev_30.json", "dev_93.json"),
    ],
)
def test_larger_samples_start_with_the_smaller_ones(small, large):
    # Results already run on the Phase 1 samples stay valid: each larger file begins with the smaller one.
    small_items, large_items = _ids(small), _ids(large)
    assert large_items[: len(small_items)] == small_items


def test_dev_sample_integrity():
    dev_file = SAMPLES_DIR / "dev_30.json"
    ids = json.loads(dev_file.read_text(encoding="utf-8"))
    assert len(ids) == 30
    assert len(set(ids)) == 30

    problems = load_sample_file(dev_file)
    assert len(problems) == 30

    canonical_problems = {p.problem_id: p for p in load_split("canonical", data_dir=DATA_DIR)}
    for pid in ids:
        assert pid in canonical_problems

    by_class: dict[str, int] = {}
    for problem in problems:
        assert problem.split == "canonical"
        assert problem.question.strip()
        by_class[problem.problem_class] = by_class.get(problem.problem_class, 0) + 1

    assert len(by_class) == 10
    assert all(count == 3 for count in by_class.values())

    dev_set = set(ids)
    for name in SAMPLE_FILES:
        if name.startswith("constraint_pairs"):
            assert dev_set.isdisjoint(_pair_ids(name)), name
        elif name not in ("dev_30.json", "dev_93.json"):
            assert dev_set.isdisjoint(_ids(name)), name


def test_dev_sample_regeneration_is_identical(tmp_path):
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"
    generate_samples(output_dir=dir1, data_dir=DATA_DIR)
    generate_samples(output_dir=dir2, data_dir=DATA_DIR)

    hash1 = hashlib.sha256((dir1 / "dev_30.json").read_bytes()).hexdigest()
    hash2 = hashlib.sha256((dir2 / "dev_30.json").read_bytes()).hexdigest()
    assert hash1 == hash2

    checked_in_hash = hashlib.sha256((SAMPLES_DIR / "dev_30.json").read_bytes()).hexdigest()
    assert hash1 == checked_in_hash


def test_sample_files_formatting():
    for name in SAMPLE_FILES:
        file_path = SAMPLES_DIR / name
        raw_bytes = file_path.read_bytes()
        assert raw_bytes.endswith(b"\n")
        assert b"\r" not in raw_bytes

        # Verify 2-space indentation and sorted keys
        data = json.loads(raw_bytes.decode("utf-8"))
        formatted = json.dumps(data, indent=2, sort_keys=True) + "\n"
        assert raw_bytes.decode("utf-8") == formatted


def test_sample_generation_determinism_via_hashes(tmp_path):
    generated = generate_samples(output_dir=tmp_path, data_dir=DATA_DIR)

    assert sorted(path.name for path in generated.values()) == sorted(SAMPLE_FILES)
    for name in SAMPLE_FILES:
        checked_in = SAMPLES_DIR / name
        new_file = tmp_path / name

        hash_checked_in = hashlib.sha256(checked_in.read_bytes()).hexdigest()
        hash_new = hashlib.sha256(new_file.read_bytes()).hexdigest()

        assert hash_new == hash_checked_in, f"Hash mismatch for {name}: {hash_new} != {hash_checked_in}"


def test_canonical_587_and_dev_93():
    # 60 per class, except NetworkFlow: the benchmark has only 50, and 3 are in dev_30.
    classes = {p.problem_id: p.problem_class for p in load_split("canonical", data_dir=DATA_DIR)}
    large, dev = _ids("canonical_587.json"), _ids("dev_93.json")
    assert len(set(large)) == 587 and len(set(dev)) == 93
    large_counts = {c: sum(classes[i] == c for i in large) for c in set(classes.values())}
    assert large_counts.pop("NetworkFlow") == 47 and set(large_counts.values()) == {60}
    dev_counts = {c: sum(classes[i] == c for i in dev) for c in set(classes.values())}
    assert dev_counts.pop("NetworkFlow") == 3 and set(dev_counts.values()) == {10}
    # The development split shares no problem with any test sample.
    for name in SAMPLE_FILES:
        if name.startswith("constraint_pairs"):
            assert set(dev).isdisjoint(_pair_ids(name)), name
        elif not name.startswith("dev_"):
            assert set(dev).isdisjoint(_ids(name)), name
