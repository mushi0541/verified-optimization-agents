"""E5 ablation table: read saved pipeline records and output ablations.csv (no API calls).

Usage:
    python scripts/ablation_table.py [--records RECORDS [RECORDS ...]]
                                     [--sample-file SAMPLES/ABLATION_50.JSON]
                                     [--out RESULTS/ABLATIONS/ABLATIONS.CSV]
                                     [--threshold 0.8] [--alpha 0.10]
                                     [--no-parser-records PATH] [--r2-records PATH]
"""

import argparse
import csv
import json
from pathlib import Path
import statistics
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from optverify.calibration import calibrate_threshold, fixed_threshold, rates, scored_answers
from optverify.verifier import SIGNALS
from scripts.rescore import rescore_records


def compute_auroc(scored: list[tuple[float, bool]]) -> float | None:
    """Mann-Whitney U statistic / concordance index for (score, correct) pairs."""
    pos = [s for s, c in scored if c]
    neg = [s for s, c in scored if not c]
    if not pos or not neg:
        return None
    pairs = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                pairs += 1.0
            elif p == n:
                pairs += 0.5
    return pairs / (len(pos) * len(neg))


def load_records(records_path: Path) -> list[dict]:
    """Every record of one run."""
    if not records_path.exists():
        print(f"Records file not found: {records_path}", file=sys.stderr)
        sys.exit(1)
    with records_path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def ablation_subset(records: list[dict], ablation_ids: set[str], source_label: str) -> list[dict]:
    """The records of the ablation problems; every ablation problem must be there, so rows compare the same set."""
    subset = [r for r in records if r.get("problem_id") in ablation_ids]
    found = {r["problem_id"] for r in subset}
    print(f"Matched {len(found)}/{len(ablation_ids)} ablation problem IDs in {source_label}")
    if found != ablation_ids:
        print(
            f"{source_label} is missing {len(ablation_ids - found)} of the {len(ablation_ids)} ablation problems; "
            "every row must use the same problems.",
            file=sys.stderr,
        )
        sys.exit(1)
    return subset


def held_out_rates(subset: list[dict], calibration_records: list[dict], alpha: float) -> dict:
    """Ablation (vi): each class's threshold is calibrated on the other classes of the whole run, then applied to that
    class's ablation problems. The 50 ablation problems alone are too few: with 45 per fold the exact bound can
    hardly be met, so almost nothing would be answered."""
    calibration = [r for r in calibration_records if "failed" not in r]
    test = [r for r in subset if "failed" not in r]
    answered, wrong = 0, 0
    for held_out in sorted({r["problem_class"] for r in test}):
        threshold = calibrate_threshold(scored_answers([r for r in calibration if r["problem_class"] != held_out]), alpha)
        if threshold is None:
            continue
        hits = [ok for score, ok in scored_answers([r for r in test if r["problem_class"] == held_out]) if score >= threshold]
        answered += len(hits)
        wrong += sum(not ok for ok in hits)
    return rates(answered, wrong, len(test))


def verify_k_in_records(records: list[dict], source_label: str) -> None:
    """Verify that records were run with k >= 3 paraphrase runs."""
    for r in records:
        if "failed" in r:
            continue
        report = r.get("verifier", {})
        if report.get("feasible") and r.get("attempts", [{}])[-1].get("solve", {}).get("status") == "optimal":
            others = report.get("paraphrase_objectives", [])
            if len(others) < 3:
                print(
                    f"Reference records in {source_label} have k = {len(others)} < 3 "
                    f"for problem {r.get('problem_id')}. k = 3 reference is required to compute "
                    "ablation table rows.",
                    file=sys.stderr,
                )
                sys.exit(1)


def evaluate_records(
    rescored: list[dict], threshold: float = 0.8, alpha: float | None = None, calibration_records: list[dict] | None = None
) -> dict:
    """Compute standard metrics on rescored records; with alpha, thresholds come from calibration_records."""
    finished = [r for r in rescored if "failed" not in r]
    total_finished = len(finished)
    if total_finished == 0:
        return {
            "accuracy": 0.0,
            "coverage": 0.0,
            "wrong_accept_rate": None,
            "auroc": None,
            "mean_tokens": 0.0,
            "mean_calls": 0.0,
        }

    correct_count = sum(1 for r in finished if r.get("correct") is True)
    accuracy = correct_count / total_finished

    if alpha is not None:
        pooled = held_out_rates(rescored, calibration_records if calibration_records is not None else rescored, alpha)
        coverage = pooled["coverage"]
        wrong_accept_rate = pooled["wrong_accept_rate"]
    else:
        dec = fixed_threshold(rescored, threshold=threshold)
        coverage = dec["coverage"]
        wrong_accept_rate = dec["wrong_accept_rate"]

    scored_pairs = [(r["score"], bool(r["correct"])) for r in finished]
    auroc = compute_auroc(scored_pairs)

    mean_tokens = sum(r.get("tokens", 0) for r in finished) / total_finished
    mean_calls = sum(r.get("calls", 0) for r in finished) / total_finished

    return {
        "accuracy": accuracy,
        "coverage": coverage,
        "wrong_accept_rate": wrong_accept_rate,
        "auroc": auroc,
        "mean_tokens": mean_tokens,
        "mean_calls": mean_calls,
    }


ROW_SPECS = [
    ("Reference (main pipeline: k=3, r=1, all signals)", "rescore", {"signals": SIGNALS, "k": 3, "repairs": True, "threshold": 0.8}),
    ("(i) Without number coverage", "rescore", {"signals": ("requirement", "paraphrase"), "k": 3, "repairs": True, "threshold": 0.8}),
    ("(ii) Without requirement coverage", "rescore", {"signals": ("number", "paraphrase"), "k": 3, "repairs": True, "threshold": 0.8}),
    ("(iii) Without paraphrase agreement", "rescore", {"signals": ("number", "requirement"), "k": 0, "repairs": True, "threshold": 0.8}),
    ("(iv) Without the parser", "external", "no_parser"),
    ("(v) k = 1 paraphrase", "rescore", {"signals": SIGNALS, "k": 1, "repairs": True, "threshold": 0.8}),
    ("(v) k = 2 paraphrases", "rescore", {"signals": SIGNALS, "k": 2, "repairs": True, "threshold": 0.8}),
    ("(vi) Calibrated threshold (alpha = 0.10, thresholds from the whole run)", "rescore", {"signals": SIGNALS, "k": 3, "repairs": True, "alpha": 0.10}),
    ("(vii) r = 0 repairs", "rescore", {"signals": SIGNALS, "k": 3, "repairs": False, "threshold": 0.8}),
    ("(vii) r = 2 repairs", "external", "r2"),
]


def generate_ablation_table(
    record_paths: list[Path],
    sample_file: Path,
    out_file: Path | None = None,
    threshold: float = 0.8,
    alpha: float = 0.10,
    no_parser_records: list[Path] | None = None,
    r2_records: list[Path] | None = None,
) -> tuple[list[str], list[list]]:
    """Generate rows and columns of ablations.csv."""
    if not sample_file.exists():
        print(f"Sample file not found: {sample_file}", file=sys.stderr)
        sys.exit(1)
    ablation_ids = set(json.loads(sample_file.read_text(encoding="utf-8")))

    # Each repeat: the whole run (to calibrate row (vi)) and its ablation problems (for every row).
    repeats = []
    for p in record_paths:
        records = load_records(p)
        verify_k_in_records(records, str(p))
        repeats.append((records, ablation_subset(records, ablation_ids, str(p))))
    n_repeats = len(repeats)

    # (iv) and (vii) r = 2 come from their own runs (one or more repeats), scored like the reference row.
    external_records = {}
    for key, paths in (("no_parser", no_parser_records), ("r2", r2_records)):
        if paths:
            external_records[key] = [ablation_subset(load_records(p), ablation_ids, str(p)) for p in paths]

    metric_keys = ["accuracy", "coverage", "wrong_accept_rate", "auroc", "mean_tokens", "mean_calls"]
    include_std = n_repeats > 1
    header = ["ablation", *metric_keys, "repeats"] + ([f"{key}_std" for key in metric_keys] if include_std else [])

    def metrics_row(label: str, repeat_metrics: list[dict]) -> list:
        """Mean over repeats, and the sample standard deviation when the table has repeats."""
        row = [label]
        stds = []
        for key in metric_keys:
            values = [m[key] for m in repeat_metrics if m[key] is not None]
            row.append(statistics.mean(values) if values else None)
            stds.append(statistics.stdev(values) if len(values) > 1 else None)
        row.append(len(repeat_metrics))
        return row + (stds if include_std else [])

    rows = []
    for label, kind, cfg in ROW_SPECS:
        if kind == "rescore":
            sig = cfg.get("signals", SIGNALS)
            k_val = cfg.get("k")
            rep = cfg.get("repairs", True)
            th = cfg.get("threshold", threshold)
            a_val = alpha if "alpha" in cfg else None
            repeat_metrics = []
            for records, subset in repeats:
                rescored = rescore_records(subset, signals=sig, k=k_val, repairs=rep)
                calibration = rescore_records(records, signals=sig, k=k_val, repairs=rep) if a_val is not None else None
                repeat_metrics.append(evaluate_records(rescored, threshold=th, alpha=a_val, calibration_records=calibration))
            rows.append(metrics_row(label, repeat_metrics))

        elif kind == "external":
            if cfg in external_records:
                repeat_metrics = [
                    evaluate_records(rescore_records(subset), threshold=threshold) for subset in external_records[cfg]
                ]
                rows.append(metrics_row(label, repeat_metrics))
            else:
                # Missing run: empty cells with word "not run"
                row = [label, "not run", "", "", "", "", "", 0]
                if include_std:
                    row.extend(["", "", "", "", "", ""])
                rows.append(row)

    if out_file:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with out_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for r in rows:
                formatted = []
                for val in r:
                    if val is None or val == "":
                        formatted.append("")
                    elif isinstance(val, float):
                        formatted.append(f"{val:.4f}")
                    else:
                        formatted.append(str(val))
                writer.writerow(formatted)

    return header, rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate E5 ablation table (no API calls).")
    parser.add_argument(
        "--records",
        type=Path,
        nargs="+",
        required=True,
        help="records.jsonl of pipeline runs (k >= 3)",
    )
    parser.add_argument(
        "--sample-file",
        type=Path,
        default=REPO_ROOT / "samples" / "ablation_50.json",
        help="Path to ablation sample IDs file (default: samples/ablation_50.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "results" / "ablations" / "ablations.csv",
        help="Output CSV path (default: results/ablations/ablations.csv)",
    )
    parser.add_argument("--threshold", type=float, default=0.8, help="Fixed threshold (default: 0.8)")
    parser.add_argument("--alpha", type=float, default=0.10, help="Target alpha for calibrated threshold (default: 0.10)")
    parser.add_argument(
        "--no-parser-records", type=Path, nargs="+", default=None, help="records.jsonl of --no-parser runs (one per repeat)"
    )
    parser.add_argument(
        "--r2-records", type=Path, nargs="+", default=None, help="records.jsonl of --repairs 2 runs (one per repeat)"
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    header, rows = generate_ablation_table(
        record_paths=args.records,
        sample_file=args.sample_file,
        out_file=args.out,
        threshold=args.threshold,
        alpha=args.alpha,
        no_parser_records=args.no_parser_records,
        r2_records=args.r2_records,
    )
    print(f"Ablation table written to {args.out}")


if __name__ == "__main__":
    main()

