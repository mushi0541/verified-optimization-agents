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

from optverify.calibration import fixed_threshold, leave_one_class_out
from optverify.rescore import rescore
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


def load_and_filter_records(records_path: Path, ablation_ids: set[str]) -> list[dict]:
    """Load records.jsonl and restrict strictly to the ablation problem IDs."""
    if not records_path.exists():
        print(f"Records file not found: {records_path}", file=sys.stderr)
        sys.exit(1)

    records = []
    with records_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("problem_id") in ablation_ids:
                records.append(rec)

    return records


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


def evaluate_records(rescored: list[dict], threshold: float = 0.8, alpha: float | None = None) -> dict:
    """Compute standard metrics on rescored records."""
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
        dec = leave_one_class_out(rescored, alpha=alpha)
        pooled = dec["pooled"]
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
    ("(vi) Calibrated threshold (alpha = 0.10)", "rescore", {"signals": SIGNALS, "k": 3, "repairs": True, "alpha": 0.10}),
    ("(vii) r = 0 repairs", "rescore", {"signals": SIGNALS, "k": 3, "repairs": False, "threshold": 0.8}),
    ("(vii) r = 2 repairs", "external", "r2"),
]


def generate_ablation_table(
    record_paths: list[Path],
    sample_file: Path,
    out_file: Path | None = None,
    threshold: float = 0.8,
    alpha: float = 0.10,
    no_parser_records: Path | None = None,
    r2_records: Path | None = None,
) -> tuple[list[str], list[list]]:
    """Generate rows and columns of ablations.csv."""
    if not sample_file.exists():
        print(f"Sample file not found: {sample_file}", file=sys.stderr)
        sys.exit(1)
    sample_text = sample_file.read_text(encoding="utf-8")
    ablation_ids = set(json.loads(sample_text))
    expected_count = len(ablation_ids)

    # Load and filter repeats
    repeats_records = []
    for p in record_paths:
        filtered = load_and_filter_records(p, ablation_ids)
        print(f"Matched {len(filtered)}/{expected_count} ablation problem IDs in {p}")
        verify_k_in_records(filtered, str(p))
        repeats_records.append(filtered)

    n_repeats = len(repeats_records)

    # External records for (iv) and (vii) r=2 if available
    external_records = {}
    if no_parser_records and no_parser_records.exists():
        external_records["no_parser"] = load_and_filter_records(no_parser_records, ablation_ids)
    if r2_records and r2_records.exists():
        external_records["r2"] = load_and_filter_records(r2_records, ablation_ids)

    metric_keys = ["accuracy", "coverage", "wrong_accept_rate", "auroc", "mean_tokens", "mean_calls"]

    include_std = n_repeats > 1
    if include_std:
        header = [
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
    else:
        header = [
            "ablation",
            "accuracy",
            "coverage",
            "wrong_accept_rate",
            "auroc",
            "mean_tokens",
            "mean_calls",
            "repeats",
        ]

    rows = []
    for label, kind, cfg in ROW_SPECS:
        if kind == "rescore":
            sig = cfg.get("signals", SIGNALS)
            k_val = cfg.get("k")
            rep = cfg.get("repairs", True)
            th = cfg.get("threshold", threshold)
            a_val = cfg.get("alpha")
            if a_val is not None:
                a_val = alpha  # Use parameter alpha

            repeat_metrics = []
            for recs in repeats_records:
                rescored = rescore_records(recs, signals=sig, k=k_val, repairs=rep)
                m = evaluate_records(rescored, threshold=th, alpha=a_val)
                repeat_metrics.append(m)

            # Compute mean and optional std
            means = {}
            stds = {}
            for k in metric_keys:
                vals = [m[k] for m in repeat_metrics if m[k] is not None]
                if vals:
                    means[k] = statistics.mean(vals)
                    stds[k] = statistics.stdev(vals) if len(vals) > 1 else None
                else:
                    means[k] = None
                    stds[k] = None

            row = [
                label,
                means["accuracy"],
                means["coverage"],
                means["wrong_accept_rate"],
                means["auroc"],
                means["mean_tokens"],
                means["mean_calls"],
                n_repeats,
            ]
            if include_std:
                row.extend([
                    stds["accuracy"],
                    stds["coverage"],
                    stds["wrong_accept_rate"],
                    stds["auroc"],
                    stds["mean_tokens"],
                    stds["mean_calls"],
                ])
            rows.append(row)

        elif kind == "external":
            ext_key = cfg
            if ext_key in external_records:
                ext_recs = external_records[ext_key]
                m = evaluate_records(ext_recs, threshold=threshold)
                row = [
                    label,
                    m["accuracy"],
                    m["coverage"],
                    m["wrong_accept_rate"],
                    m["auroc"],
                    m["mean_tokens"],
                    m["mean_calls"],
                    1,
                ]
                if include_std:
                    row.extend(["", "", "", "", "", ""])
                rows.append(row)
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
    parser.add_argument("--no-parser-records", type=Path, default=None, help="Records from a --no-parser run (if available)")
    parser.add_argument("--r2-records", type=Path, default=None, help="Records from a --repairs 2 run (if available)")
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

