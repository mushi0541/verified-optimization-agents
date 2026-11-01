"""Tests for scripts/ablation_table.py (offline, synthetic records)."""

import csv
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.ablation_table import ROW_SPECS, compute_auroc, generate_ablation_table


def _usage(tokens: int, calls: int) -> dict:
    return {"input_tokens": tokens, "output_tokens": 0, "calls": calls}


def _record(pid: str, cls: str, first_status: str, objective: float, reference: float,
            number: float, requirement: float, others: list[float]):
    attempts = [{"code": "", "solve": {"status": first_status, "objective": objective if first_status == "optimal" else None}}]
    steps = {"parse": _usage(100, 1), "formalize": _usage(200, 1), "repair": _usage(0, 0)}
    if first_status != "optimal":
        attempts.append({"code": "", "solve": {"status": "optimal", "objective": objective}})
        steps["repair"] = _usage(50, 1)

    for j in range(1, len(others) + 1):
        steps[f"paraphrase_{j}"] = _usage(100, 2)

    total_tokens = sum(s["input_tokens"] for s in steps.values())
    total_calls = sum(s["calls"] for s in steps.values())

    return {
        "problem_id": pid,
        "problem_class": cls,
        "reference": reference,
        "correct": objective == reference if first_status == "optimal" or len(attempts) > 1 else False,
        "attempts": attempts,
        "usage": _usage(total_tokens, total_calls),
        "usage_by_step": steps,
        "verifier": {
            "feasible": True,
            "number_coverage": number,
            "requirement_coverage": requirement,
            "paraphrase_agreement": sum(1 for o in others if o == objective) / len(others) if others else 0.0,
            "paraphrase_objectives": list(others),
            "score": 0.0,
        },
    }


@pytest.fixture
def synthetic_records_file(tmp_path):
    records = [
        # p1: class A, correct True, all agree
        _record("p1", "A", "optimal", 100.0, 100.0, 1.0, 1.0, [100.0, 100.0, 100.0]),
        # p2: class A, correct False (obj 80 != ref 100)
        _record("p2", "A", "optimal", 80.0, 100.0, 0.6, 0.0, [100.0, 90.0, 70.0]),
        # p3: class B, repaired, correct True
        _record("p3", "B", "error", 100.0, 100.0, 0.8, 1.0, [100.0, 100.0, 90.0]),
        # p4: class B, correct False (obj 50 != ref 100)
        _record("p4", "B", "optimal", 50.0, 100.0, 0.5, 0.5, [90.0, 80.0, 70.0]),
        # p_extra: not in sample file, must be excluded
        _record("p_extra", "C", "optimal", 100.0, 100.0, 1.0, 1.0, [100.0, 100.0, 100.0]),
    ]

    records_path = tmp_path / "records.jsonl"
    with records_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    sample_file = tmp_path / "ablation_sample.json"
    sample_file.write_text(json.dumps(["p1", "p2", "p3", "p4"]), encoding="utf-8")

    return records_path, sample_file


def test_auroc_metric():
    # Perfect separation
    assert compute_auroc([(1.0, True), (0.2, False)]) == 1.0
    # Perfect inversion
    assert compute_auroc([(0.2, True), (1.0, False)]) == 0.0
    # Ties get 0.5
    assert compute_auroc([(0.5, True), (0.5, False)]) == 0.5
    # Empty positive or negative returns None
    assert compute_auroc([(0.5, True)]) is None
    assert compute_auroc([(0.5, False)]) is None


def test_ablation_table_hand_computed_values(synthetic_records_file, tmp_path):
    records_file, sample_file = synthetic_records_file
    out_csv = tmp_path / "ablations.csv"

    header, rows = generate_ablation_table(
        record_paths=[records_file],
        sample_file=sample_file,
        out_file=out_csv,
        threshold=0.8,
        alpha=0.10,
    )

    # Convert rows to dict by ablation name
    row_dict = {r[0]: r for r in rows}

    # 1. Reference row: acc = 2/4 = 0.5, cov = 2/4 = 0.5, wrong_accept = 0.0, auroc = 1.0, tokens = 612.5, calls = 7.25
    ref_row = row_dict["Reference (main pipeline: k=3, r=1, all signals)"]
    assert math.isclose(ref_row[1], 0.5)
    assert math.isclose(ref_row[2], 0.5)
    assert math.isclose(ref_row[3], 0.0)
    assert math.isclose(ref_row[4], 1.0)
    assert math.isclose(ref_row[5], 612.5)
    assert math.isclose(ref_row[6], 8.25)
    assert ref_row[7] == 1  # 1 repeat

    # 2. Row (i) Without number coverage
    r_i = row_dict["(i) Without number coverage"]
    assert math.isclose(r_i[1], 0.5)
    assert math.isclose(r_i[2], 0.5)
    assert math.isclose(r_i[3], 0.0)
    assert math.isclose(r_i[4], 1.0)
    assert math.isclose(r_i[5], 612.5)

    # 3. Row (iii) Without paraphrase agreement: tokens drop by 300, calls by 6
    r_iii = row_dict["(iii) Without paraphrase agreement"]
    assert math.isclose(r_iii[1], 0.5)
    assert math.isclose(r_iii[2], 0.5)
    assert math.isclose(r_iii[3], 0.0)
    assert math.isclose(r_iii[5], 312.5)
    assert math.isclose(r_iii[6], 2.25)

    # 4. Row (v) k = 1: tokens drop by 200, calls by 4
    r_v_k1 = row_dict["(v) k = 1 paraphrase"]
    assert math.isclose(r_v_k1[1], 0.5)
    assert math.isclose(r_v_k1[2], 0.5)
    assert math.isclose(r_v_k1[5], 412.5)
    assert math.isclose(r_v_k1[6], 4.25)

    # 5. Row (vii) r = 0 repairs: p3 fails first attempt so acc = 1/4 = 0.25, tokens = 525.0, calls = 6.5
    r_vii_r0 = row_dict["(vii) r = 0 repairs"]
    assert math.isclose(r_vii_r0[1], 0.25)
    assert math.isclose(r_vii_r0[2], 0.25)
    assert math.isclose(r_vii_r0[3], 0.0)
    assert math.isclose(r_vii_r0[4], 1.0)
    assert math.isclose(r_vii_r0[5], 525.0)
    assert math.isclose(r_vii_r0[6], 6.5)

    # 6. Missing rows: (iv) and (vii) r = 2 must produce "not run" cells and 0 repeats
    r_iv = row_dict["(iv) Without the parser"]
    assert r_iv[1] == "not run"
    assert r_iv[2] == ""
    assert r_iv[7] == 0

    r_vii_r2 = row_dict["(vii) r = 2 repairs"]
    assert r_vii_r2[1] == "not run"
    assert r_vii_r2[2] == ""
    assert r_vii_r2[7] == 0


def test_ablation_csv_header_and_row_order(synthetic_records_file, tmp_path):
    records_file, sample_file = synthetic_records_file
    out_csv = tmp_path / "ablations.csv"

    header, rows = generate_ablation_table(
        record_paths=[records_file],
        sample_file=sample_file,
        out_file=out_csv,
    )

    expected_header = [
        "ablation",
        "accuracy",
        "coverage",
        "wrong_accept_rate",
        "auroc",
        "mean_tokens",
        "mean_calls",
        "repeats",
    ]
    assert header == expected_header

    # Check written file contents and row order
    with out_csv.open("r", encoding="utf-8") as f:
        reader = list(csv.reader(f))

    assert reader[0] == expected_header
    assert len(reader) == 11  # 1 header + 10 rows

    expected_row_names = [spec[0] for spec in ROW_SPECS]
    actual_row_names = [row[0] for row in reader[1:]]
    assert actual_row_names == expected_row_names


def test_multi_repeat_standard_deviation(synthetic_records_file, tmp_path):
    records_file, sample_file = synthetic_records_file
    out_csv = tmp_path / "ablations_multi.csv"

    # Pass the same records file twice to simulate two identical repeats
    header, rows = generate_ablation_table(
        record_paths=[records_file, records_file],
        sample_file=sample_file,
        out_file=out_csv,
    )

    expected_header = [
        "ablation",
        "accuracy",
        "coverage",
        "wrong_accept_rate",
        "auroc",
        "mean_tokens",
        "mean_calls",
        "repeats",
        "accuracy_std",
        "coverage_std",
        "wrong_accept_rate_std",
        "auroc_std",
        "mean_tokens_std",
        "mean_calls_std",
    ]
    assert header == expected_header

    ref_row = [r for r in rows if "Reference" in r[0]][0]
    assert ref_row[7] == 2  # 2 repeats
    # Identical repeats have std == 0.0
    assert math.isclose(ref_row[8], 0.0)
    assert math.isclose(ref_row[9], 0.0)


def test_missing_k3_reference_exits(tmp_path, capsys):
    # Construct record with only k = 2 paraphrase objectives
    rec = _record("p1", "A", "optimal", 100.0, 100.0, 1.0, 1.0, [100.0, 100.0])
    records_file = tmp_path / "records_k2.jsonl"
    records_file.write_text(json.dumps(rec) + "\n", encoding="utf-8")

    sample_file = tmp_path / "sample.json"
    sample_file.write_text(json.dumps(["p1"]), encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        generate_ablation_table(
            record_paths=[records_file],
            sample_file=sample_file,
        )
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "k = 2 < 3" in captured.err
    assert "Traceback" not in captured.err


def test_cli_k2_synthetic_record_exits_without_traceback(tmp_path):
    rec = _record("p1", "A", "optimal", 100.0, 100.0, 1.0, 1.0, [100.0, 100.0])
    records_file = tmp_path / "records_k2.jsonl"
    records_file.write_text(json.dumps(rec) + "\n", encoding="utf-8")

    sample_file = tmp_path / "sample.json"
    sample_file.write_text(json.dumps(["p1"]), encoding="utf-8")

    res = subprocess.run(
        [
            sys.executable,
            "scripts/ablation_table.py",
            "--records",
            str(records_file),
            "--sample-file",
            str(sample_file),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "Traceback" not in res.stderr
    assert "k = 2 < 3" in res.stderr


def test_cli_missing_records_file_exits_without_traceback(tmp_path):
    sample_file = tmp_path / "sample.json"
    sample_file.write_text(json.dumps(["p1"]), encoding="utf-8")

    res = subprocess.run(
        [
            sys.executable,
            "scripts/ablation_table.py",
            "--records",
            str(tmp_path / "non_existent.jsonl"),
            "--sample-file",
            str(sample_file),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "Traceback" not in res.stderr
    assert "Records file not found" in res.stderr


def test_cli_execution_via_subprocess(synthetic_records_file, tmp_path):
    records_file, sample_file = synthetic_records_file
    out_csv = tmp_path / "sub_ablations.csv"

    res = subprocess.run(
        [
            sys.executable,
            "scripts/ablation_table.py",
            "--records",
            str(records_file),
            "--sample-file",
            str(sample_file),
            "--out",
            str(out_csv),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Ablation table written to" in res.stdout
    assert out_csv.exists()
