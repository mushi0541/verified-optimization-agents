"""Aggregate experiment repeats and generate summary statistics.

Usage:
    python experiments/aggregate.py <E1..E6>
"""

import argparse
import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path


def extract_repeat_metrics(repeat_dir: Path) -> dict[str, float]:
    """Extract numeric metrics from a single repeat directory."""
    records_file = repeat_dir / "records.jsonl"
    if not records_file.exists():
        raise FileNotFoundError(f"records.jsonl not found in {repeat_dir}")

    records = []
    with records_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if not records:
        return {}

    total = len(records)
    finished = [r for r in records if "failed" not in r]

    correct_count = sum(1 for r in records if r.get("correct") is True)
    accuracy = correct_count / total

    # Solved rate: solver finished with status "optimal"
    solved_count = sum(
        1 for r in records
        if r.get("attempts") and r["attempts"][-1].get("solve", {}).get("status") == "optimal"
    )
    solved_rate = solved_count / total

    # Decisions: answer, escalate, abstain
    decided = [r for r in records if r.get("decision")]
    answer_count = sum(1 for r in decided if r.get("decision", {}).get("action") == "answer")
    escalate_count = sum(1 for r in decided if r.get("decision", {}).get("action") == "escalate")
    abstain_count = sum(1 for r in decided if r.get("decision", {}).get("action") == "abstain")

    answer_rate = answer_count / total if total > 0 else 0.0
    escalation_rate = escalate_count / total if total > 0 else 0.0
    abstention_rate = abstain_count / total if total > 0 else 0.0

    # Token usages and latencies
    input_tokens = [r.get("usage", {}).get("input_tokens", 0) for r in records]
    output_tokens = [r.get("usage", {}).get("output_tokens", 0) for r in records]
    calls = [r.get("usage", {}).get("calls", 0) for r in records]
    latencies = [r.get("latency_s", 0.0) for r in records]

    mean_input_tokens = sum(input_tokens) / total
    mean_output_tokens = sum(output_tokens) / total
    mean_total_tokens = mean_input_tokens + mean_output_tokens
    mean_llm_calls = sum(calls) / total
    mean_latency_s = sum(latencies) / total

    metrics = {
        "accuracy": accuracy,
        "solved_rate": solved_rate,
        "answer_rate": answer_rate,
        "escalation_rate": escalation_rate,
        "abstention_rate": abstention_rate,
        "mean_input_tokens": mean_input_tokens,
        "mean_output_tokens": mean_output_tokens,
        "mean_tokens": mean_total_tokens,
        "mean_total_tokens": mean_total_tokens,
        "mean_llm_calls": mean_llm_calls,
        "mean_latency": mean_latency_s,
        "mean_latency_s": mean_latency_s,
    }

    # Selective accuracy and wrong accept rate if answers exist
    if answer_count > 0:
        answered_correct = sum(1 for r in decided if r.get("decision", {}).get("action") == "answer" and r.get("correct") is True)
        metrics["selective_accuracy"] = answered_correct / answer_count
        metrics["wrong_accept_rate"] = 1.0 - (answered_correct / answer_count)

    # If repeat summary.json exists, load any other numeric values
    summary_file = repeat_dir / "summary.json"
    if summary_file.exists():
        try:
            summary_data = json.loads(summary_file.read_text(encoding="utf-8"))
            for k, v in summary_data.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) and k not in metrics:
                    metrics[k] = float(v)
        except Exception:
            pass

    return metrics


def aggregate_experiment(exp_name: str, results_dir: Path | str = "results") -> dict:
    """Aggregate all repeats for an experiment and write summary files."""
    exp_name = exp_name.upper()
    results_path = Path(results_dir)
    exp_dir = results_path / exp_name

    if not exp_dir.exists():
        raise FileNotFoundError(f"Experiment results directory not found: {exp_dir}")

    # Discover repeat directories
    repeat_dirs = []
    for child in exp_dir.iterdir():
        if child.is_dir() and (child / "records.jsonl").exists():
            repeat_dirs.append(child)

    if not repeat_dirs:
        raise ValueError(f"No repeat runs found for experiment {exp_name} in {exp_dir}")

    # Sort repeats numerically if folder names are ints
    def _sort_key(p: Path):
        try:
            return (0, int(p.name))
        except ValueError:
            return (1, p.name)

    repeat_dirs.sort(key=_sort_key)

    all_repeat_metrics: list[dict[str, float]] = []
    for r_dir in repeat_dirs:
        all_repeat_metrics.append(extract_repeat_metrics(r_dir))

    # Collect all metric keys
    all_keys = sorted({k for m in all_repeat_metrics for k in m})

    computed_stats = {}
    for key in all_keys:
        values = [m[key] for m in all_repeat_metrics if key in m and m[key] is not None]
        if not values:
            continue
        mean_val = statistics.mean(values)
        stdev_val = statistics.stdev(values) if len(values) > 1 else None
        computed_stats[key] = {
            "mean": mean_val,
            "stdev": stdev_val,
        }

    summary_data = {
        "experiment": exp_name,
        "repeats": len(repeat_dirs),
        "metrics": computed_stats,
    }
    # Also expose metrics at the top level
    for key, val in computed_stats.items():
        summary_data[key] = val

    # Write summary.json
    (exp_dir / "summary.json").write_text(json.dumps(summary_data, indent=2), encoding="utf-8")

    # Write summary.csv
    csv_path = exp_dir / "summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "mean", "stdev"])
        for key in sorted(computed_stats):
            mean_val = computed_stats[key]["mean"]
            stdev_val = computed_stats[key]["stdev"]
            writer.writerow([key, mean_val, stdev_val if stdev_val is not None else ""])

    # Update results manifest
    update_manifest(results_path)

    return summary_data


def update_manifest(results_dir: Path | str = "results") -> list[dict]:
    """Scan results directory and write manifest.json."""
    results_path = Path(results_dir)
    manifest = []

    if results_path.exists():
        for config_file in results_path.glob("*/*/config.json"):
            repeat_dir = config_file.parent
            exp_dir = repeat_dir.parent
            exp_name = exp_dir.name
            repeat_name = repeat_dir.name
            try:
                repeat_idx = int(repeat_name)
            except ValueError:
                repeat_idx = repeat_name

            rel_folder = f"{exp_name}/{repeat_name}"
            config_bytes = config_file.read_bytes()
            sha256 = hashlib.sha256(config_bytes).hexdigest()

            manifest.append({
                "experiment": exp_name,
                "repeat": repeat_idx,
                "folder": rel_folder,
                "config_sha256": sha256,
            })

    def _manifest_sort_key(item):
        exp = str(item["experiment"])
        rep = item["repeat"]
        rep_val = (0, rep) if isinstance(rep, int) else (1, str(rep))
        return (exp, rep_val)

    manifest.sort(key=_manifest_sort_key)

    manifest_path = results_path / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(manifest, indent=2) + "\n"
    manifest_path.write_bytes(json_text.encode("utf-8"))

    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate experiment repeats.")
    parser.add_argument("experiment", help="Experiment identifier (e.g. E1, E2, E3, E4, E5, E6)")
    parser.add_argument("--results-dir", type=Path, default=Path("results"), help="Results directory")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    summary = aggregate_experiment(args.experiment, args.results_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
