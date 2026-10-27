"""Experiment runner for E1 to E6 with repeats.

Usage:
    python experiments/run.py <E1..E6> [--repeat N]
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from optverify.data import load_sample_file
from optverify.grading import summarize
from optverify.llm import make_llm, with_temperature
from optverify.run import _endpoint
from optverify.systems import run_baseline, run_pipeline, run_single_agent

from .prompt_version import get_git_commit, get_prompt_version

CONFIGS_DIR = Path(__file__).resolve().parent / "configs"


def _redact_secrets(text: str) -> str:
    """Strip values of sensitive environment variables from text."""
    for key, val in os.environ.items():
        if any(term in key.upper() for term in ("KEY", "SECRET", "TOKEN", "PASSWORD")):
            clean_val = val.strip()
            if len(clean_val) >= 4 and clean_val in text:
                text = text.replace(clean_val, "[REDACTED]")
    return text


def load_experiment_config(exp_name: str) -> dict:
    config_file = CONFIGS_DIR / f"{exp_name.upper()}.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found for experiment: {exp_name}")
    return json.loads(config_file.read_text(encoding="utf-8"))


def run_experiment(
    exp_name: str,
    repeat: int | None = None,
    model: str = "bedrock:openai.gpt-oss-120b-1:0",
    sample_file: Path | str | None = None,
    results_dir: Path | str = "results",
    workers: int = 2,
    env_file: str = ".env",
    llm=None,
    sample_llm=None,
) -> list[Path]:
    """Execute one or all repeats of an experiment."""
    exp_name = exp_name.upper()
    config = load_experiment_config(exp_name)

    if config.get("analysis") or config.get("system") is None:
        message = (
            f"Refusing to run analysis-only experiment {exp_name}. "
            f"Aggregate E1, E2, and E3 instead."
        )
        print(message)
        raise ValueError(message)

    load_dotenv(env_file, override=False)
    if llm is None:
        llm = make_llm(model)

    results_path = Path(results_dir)
    total_repeats = config.get("repeats", 1) or 1
    repeats_to_run = [repeat] if repeat is not None else list(range(total_repeats))

    sample_path = Path(sample_file) if sample_file else Path(config["sample_file"])
    problems = load_sample_file(sample_path)

    system = config["system"]
    k = config.get("paraphrases")
    r = config.get("repairs", 0) or 0
    budget = config.get("budget")
    threshold = config.get("threshold", 0.8)

    out_dirs = []
    for r_idx in repeats_to_run:
        out_dir = results_path / exp_name / str(r_idx)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_dirs.append(out_dir)

        # Decoding settings
        temp = getattr(llm, "temperature", 0.0)
        decoding = {"temperature": temp}
        model_name = getattr(llm, "name", model)
        endpoint = _endpoint(model_name)

        config_data = {
            "experiment": exp_name,
            "system": system,
            "sample_file": str(sample_path),
            "k": k,
            "r": r,
            "budget": budget,
            "repeat": r_idx,
            "seed": r_idx,
            "model": model_name,
            "endpoint": endpoint,
            "temperature": temp,
            "decoding": decoding,
            "prompt_version": get_prompt_version(),
            "git_commit": get_git_commit(),
        }

        config_text = _redact_secrets(json.dumps(config_data, indent=2))
        (out_dir / "config.json").write_text(config_text, encoding="utf-8")

        if sample_llm is None and system == "b2":
            sample_llm = with_temperature(llm, 0.7)

        def solve(problem):
            if system == "baseline":
                return run_baseline(problem, llm, max_repairs=r)
            if system == "b2":
                return run_single_agent(
                    problem,
                    llm,
                    sample_llm,
                    token_budget=budget,
                    max_repairs=r,
                    threshold=threshold,
                )
            # Default to pipeline
            paraphrases = k if k is not None else 2
            return run_pipeline(
                problem,
                llm,
                paraphrases=paraphrases,
                max_repairs=r,
                threshold=threshold,
            )

        records = []
        with ThreadPoolExecutor(max_workers=workers) as pool, (out_dir / "records.jsonl").open("w", encoding="utf-8") as out:
            futures = {pool.submit(solve, problem): problem for problem in problems}
            for done, future in enumerate(as_completed(futures), start=1):
                problem = futures[future]
                try:
                    record = future.result().to_json()
                except Exception as error:
                    print(f"[{done}/{len(problems)}] {problem.problem_id} FAILED: {error}")
                    records.append({"problem_id": problem.problem_id, "failed": str(error)})
                    continue
                records.append(record)
                out.write(json.dumps(record) + "\n")
                out.flush()
                print(f"[{done}/{len(problems)}] {record['problem_id']} {record['problem_class']}: correct={record['correct']}")

        finished = [record for record in records if "failed" not in record]
        summary = {
            "run": f"{exp_name}_repeat_{r_idx}",
            "config": config_data,
            "failed_problems": [record["problem_id"] for record in records if "failed" in record],
            **summarize(finished),
        }
        summary_text = _redact_secrets(json.dumps(summary, indent=2))
        (out_dir / "summary.json").write_text(summary_text, encoding="utf-8")

    return out_dirs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run evaluation experiments E1 to E6.")
    parser.add_argument("experiment", help="Experiment identifier (e.g. E1, E2, E3, E4, E5, E6)")
    parser.add_argument("--repeat", type=int, default=None, help="Specific repeat index (0-based) to run")
    parser.add_argument("--model", default="bedrock:openai.gpt-oss-120b-1:0", help="Model specification")
    parser.add_argument("--sample-file", type=Path, default=None, help="Override path to sample JSON file")
    parser.add_argument("--results-dir", type=Path, default=Path("results"), help="Results output directory")
    parser.add_argument("--workers", type=int, default=2, help="Number of worker threads")
    parser.add_argument("--env-file", default=".env", help="Environment file path")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        run_experiment(
            exp_name=args.experiment,
            repeat=args.repeat,
            model=args.model,
            sample_file=args.sample_file,
            results_dir=args.results_dir,
            workers=args.workers,
            env_file=args.env_file,
        )
    except ValueError as err:
        sys.exit(1)


if __name__ == "__main__":
    main()
