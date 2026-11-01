"""Aggregate experiment repeats and generate summary statistics.

Usage:
    python experiments/aggregate.py <E1..E6>
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def extract_repeat_metrics(repeat_dir: Path) -> dict[str, float]:
    """Extract numeric metrics from a single repeat directory."""
    summary_file = repeat_dir / "summary.json"
    if not summary_file.exists():
        raise ValueError(f"summary.json not found in {repeat_dir}")

    try:
        summary_data = json.loads(summary_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ValueError(f"Corrupt summary file in {repeat_dir}: {err}") from err

    if "sample_size" not in summary_data:
        raise ValueError(f"summary.json missing sample_size in {repeat_dir}")

    total = summary_data["sample_size"]
    if total <= 0:
        return {}

    records_file = repeat_dir / "records.jsonl"
    if not records_file.exists():
        raise FileNotFoundError(f"records.jsonl not found in {repeat_dir}")

    records = []
    with records_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    failed_count = sum(1 for r in records if r.get("failed") is True)
    failed_rate = failed_count / total

    correct_count = sum(1 for r in records if r.get("correct") is True)
    accuracy = correct_count / total

    # Solved rate: solver finished with status "optimal"
    solved_count = sum(
        1 for r in records
        if r.get("attempts") and r.get("attempts")[-1].get("solve", {}).get("status") == "optimal"
    )
    solved_rate = solved_count / total

    # Decisions: answer, escalate, abstain
    decided = [r for r in records if r.get("decision")]
    answer_count = sum(1 for r in decided if r.get("decision", {}).get("action") == "answer")
    escalate_count = sum(1 for r in decided if r.get("decision", {}).get("action") == "escalate")
    abstain_count = sum(1 for r in decided if r.get("decision", {}).get("action") == "abstain")

    answer_rate = answer_count / total
    escalation_rate = escalate_count / total
    abstention_rate = abstain_count / total

    # Token usages and latencies on non-failed records
    finished_records = [r for r in records if not r.get("failed")]
    finished_count = len(finished_records)

    input_tokens = [r.get("usage", {}).get("input_tokens", 0) for r in finished_records]
    output_tokens = [r.get("usage", {}).get("output_tokens", 0) for r in finished_records]
    calls = [r.get("usage", {}).get("calls", 0) for r in finished_records]
    latencies = [r.get("latency_s", 0.0) for r in finished_records]

    mean_input_tokens = sum(input_tokens) / finished_count if finished_count > 0 else 0.0
    mean_output_tokens = sum(output_tokens) / finished_count if finished_count > 0 else 0.0
    mean_total_tokens = mean_input_tokens + mean_output_tokens
    mean_llm_calls = sum(calls) / finished_count if finished_count > 0 else 0.0
    mean_latency_s = sum(latencies) / finished_count if finished_count > 0 else 0.0

    metrics = {
        "accuracy": accuracy,
        "solved_rate": solved_rate,
        "answer_rate": answer_rate,
        "escalation_rate": escalation_rate,
        "abstention_rate": abstention_rate,
        "failed_rate": failed_rate,
        "mean_input_tokens": mean_input_tokens,
        "mean_output_tokens": mean_output_tokens,
        "mean_tokens": mean_total_tokens,
        "mean_llm_calls": mean_llm_calls,
        "mean_latency": mean_latency_s,
    }

    # Selective accuracy and wrong accept rate if answers exist
    if answer_count > 0:
        answered_correct = sum(
            1 for r in decided
            if r.get("decision", {}).get("action") == "answer" and r.get("correct") is True
        )
        metrics["selective_accuracy"] = answered_correct / answer_count
        metrics["wrong_accept_rate"] = 1.0 - (answered_correct / answer_count)

    # Load any extra numeric values from summary_data
    for k, v in summary_data.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k not in metrics:
            if k not in ("sample_size", "repeat"):
                metrics[k] = float(v)

    return metrics


def _aggregate_dir_repeats(exp_name: str, model_name: str, model_dir: Path) -> dict:
    repeat_dirs = []
    for child in model_dir.iterdir():
        if child.is_dir() and (child / "records.jsonl").exists():
            repeat_dirs.append(child)

    if not repeat_dirs:
        raise ValueError(f"No repeat runs found for model {model_name} in {model_dir}")

    def _sort_key(p: Path):
        name = p.name.removeprefix("repeat_")
        try:
            return (0, int(name))
        except ValueError:
            return (1, p.name)

    repeat_dirs.sort(key=_sort_key)

    all_repeat_metrics: list[dict[str, float]] = []
    for r_dir in repeat_dirs:
        all_repeat_metrics.append(extract_repeat_metrics(r_dir))

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
            "std_type": "sample",
        }

    summary_data = {
        "experiment": exp_name,
        "model": model_name,
        "repeats": len(repeat_dirs),
        "metrics": computed_stats,
    }

    # Write summary.json
    (model_dir / "summary.json").write_text(json.dumps(summary_data, indent=2), encoding="utf-8")

    # Write summary.csv
    csv_path = model_dir / "summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "mean", "stdev"])
        for key in sorted(computed_stats):
            mean_val = computed_stats[key]["mean"]
            stdev_val = computed_stats[key]["stdev"]
            writer.writerow([key, mean_val, stdev_val if stdev_val is not None else ""])

    return summary_data


def aggregate_experiment(exp_name: str, results_dir: Path | str = "results") -> dict:
    """Aggregate all repeats for an experiment across models and write summary files."""
    exp_name = exp_name.upper()
    results_path = Path(results_dir)
    exp_dir = results_path / exp_name

    if not exp_dir.exists():
        raise FileNotFoundError(f"Experiment results directory not found: {exp_dir}")

    # Discover model directories containing repeat directories
    model_dirs = []
    for child in exp_dir.iterdir():
        if child.is_dir():
            repeats = [d for d in child.iterdir() if d.is_dir() and (d / "records.jsonl").exists()]
            if repeats:
                model_dirs.append(child)

    # Fallback: if repeat directories are directly under exp_dir
    if not model_dirs:
        direct_repeats = [d for d in exp_dir.iterdir() if d.is_dir() and (d / "records.jsonl").exists()]
        if direct_repeats:
            model_dirs.append(exp_dir)

    if not model_dirs:
        raise ValueError(f"No repeat runs found for experiment {exp_name} in {exp_dir}")

    model_dirs.sort(key=lambda p: p.name)

    summaries = {}
    for m_dir in model_dirs:
        # Determine model name
        m_name = m_dir.name if m_dir != exp_dir else "default"
        # Peek config.json if available to get actual model name
        first_config = next(m_dir.glob("*/config.json"), None)
        if first_config:
            m_name = json.loads(first_config.read_text(encoding="utf-8")).get("model", m_name)
        summaries[m_dir.name] = _aggregate_dir_repeats(exp_name, m_name, m_dir)

    # Update results manifest
    update_manifest(results_path)

    # Return single summary if exactly one model, otherwise all summaries
    if len(summaries) == 1:
        return list(summaries.values())[0]
    return summaries


def update_manifest(results_dir: Path | str = "results") -> list[dict]:
    """Scan results directory and write manifest.json."""
    results_path = Path(results_dir)
    manifest = []

    if results_path.exists():
        for config_file in results_path.glob("*/*/*/config.json"):
            repeat_dir = config_file.parent
            model_dir = repeat_dir.parent
            exp_dir = model_dir.parent
            exp_name = exp_dir.name
            model_slug = model_dir.name
            repeat_name = repeat_dir.name

            config_data = json.loads(config_file.read_text(encoding="utf-8"))

            model = config_data.get("model", model_slug)
            repeat_idx = config_data.get("repeat")
            if repeat_idx is None:
                try:
                    repeat_idx = int(repeat_name.removeprefix("repeat_"))
                except ValueError:
                    repeat_idx = repeat_name

            rel_folder = f"{exp_name}/{model_slug}/{repeat_name}"
            config_bytes = config_file.read_bytes()
            sha256 = hashlib.sha256(config_bytes).hexdigest()

            manifest.append({
                "experiment": exp_name,
                "model": model,
                "repeat": repeat_idx,
                "folder": rel_folder,
                "config_sha256": sha256,
            })

    def _manifest_sort_key(item):
        exp = str(item["experiment"])
        model = str(item["model"])
        rep = item["repeat"]
        rep_val = (0, rep) if isinstance(rep, int) else (1, str(rep))
        return (exp, model, rep_val)

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
    exp_dir = args.results_dir / args.experiment.upper()
    if not exp_dir.exists():
        print(f"Results directory for {args.experiment} not found: {exp_dir}", file=sys.stderr)
        sys.exit(1)
    try:
        summary = aggregate_experiment(args.experiment, args.results_dir)
        print(json.dumps(summary, indent=2))
    except (FileNotFoundError, ValueError) as err:
        print(str(err), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
