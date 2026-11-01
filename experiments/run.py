"""Experiment runner for E1 to E6 with repeats.

Usage:
    python experiments/run.py <experiment> [--repeat N] [--sample-file FILE]

<experiment> is a config name in experiments/configs (E1, E2, E3, G3, E5-NOPARSER, E5-R2). E4, E5 and E6 are
analysis-only and say what to run instead.
"""

import argparse
import json
import os
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from optverify.data import load_sample_file
from optverify.grading import summarize
from optverify.calibration import check_system, threshold_from_file
from optverify.llm import make_llm, with_temperature
from optverify.run import _endpoint
from optverify.systems import PARAPHRASE_TEMPERATURE, run_baseline, run_pipeline, run_single_agent
from optverify.verifier import SIGNALS

from experiments.prompt_version import get_git_commit, get_prompt_version

CONFIGS_DIR = Path(__file__).resolve().parent / "configs"


def _redact_secrets(text: str) -> str:
    """Strip values of sensitive environment variables from text."""
    for key, val in os.environ.items():
        if any(term in key.upper() for term in ("KEY", "SECRET", "TOKEN", "PASSWORD")):
            clean_val = val.strip()
            if len(clean_val) >= 4 and clean_val in text:
                text = text.replace(clean_val, "[REDACTED]")
    return text


def model_to_slug(model: str) -> str:
    """Convert a model identifier into a directory slug by replacing ':', '.', and '/' with '-'."""
    slug = model
    for ch in (":", ".", "/"):
        slug = slug.replace(ch, "-")
    return slug


def load_experiment_config(exp_name: str) -> dict:
    config_file = CONFIGS_DIR / f"{exp_name.upper()}.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found for experiment: {exp_name}")
    return json.loads(config_file.read_text(encoding="utf-8"))


def run_experiment(
    exp_name: str,
    repeat: int | None = None,
    model: str | None = None,
    sample_file: Path | str | None = None,
    results_dir: Path | str = "results",
    workers: int = 2,
    env_file: str = ".env",
    llm=None,
    sample_llm=None,
    budget_tokens: float | None = None,
) -> list[Path]:
    """Execute one or all repeats of an experiment across configured or specified models."""
    exp_name = exp_name.upper()
    config = load_experiment_config(exp_name)

    if config.get("analysis") or config.get("system") is None:
        print(f"Refusing to run analysis-only experiment {exp_name}. {config['notes']}", file=sys.stderr)
        sys.exit(1)

    load_dotenv(env_file, override=False)

    if model is not None:
        models_to_run = [model]
    elif llm is not None:
        models_to_run = [getattr(llm, "name", "fake-model")]
    else:
        models_to_run = config.get("models") or ["bedrock:openai.gpt-oss-120b-1:0"]

    results_path = Path(results_dir)
    total_repeats = config.get("repeats", 1) or 1
    repeats_to_run = [repeat] if repeat is not None else list(range(total_repeats))

    sample_path = Path(sample_file) if sample_file else Path(config["sample_file"])
    problems = load_sample_file(sample_path)

    system = config["system"]
    k = config.get("paraphrases")
    r = config.get("repairs", 0) or 0
    budget = budget_tokens if budget_tokens is not None else config.get("budget")
    if system == "b2" and not budget:
        raise ValueError(f"{exp_name} runs B2, which needs a token budget: set \"budget\" or pass --budget-tokens")
    signals = tuple(config.get("signals", SIGNALS))
    if not set(signals) <= set(SIGNALS):
        raise ValueError(f"{exp_name}: unknown signals {sorted(set(signals) - set(SIGNALS))}")
    use_parser = config.get("use_parser", True)
    threshold = config.get("threshold", 0.8)
    alpha = None
    if config.get("calibration"):
        if system == "baseline":
            raise ValueError(f"{exp_name}: calibration is for pipeline and b2 only")
        calibration = json.loads(Path(config["calibration"]).read_text(encoding="utf-8"))
        if system == "pipeline":
            runs = k if "paraphrase" in signals else 0
            check_system(calibration, f"pipeline_p{runs}", signals, use_parser)
        else:
            check_system(calibration, f"b2_r{r}")
        alpha = calibration["alpha"]
        threshold = threshold_from_file(calibration)
    max_samples = config.get("max_samples", 10)
    sample_temp = config.get("sample_temperature", 0.7)

    out_dirs = []
    for m_name in models_to_run:
        m_slug = model_to_slug(m_name)
        m_llm = llm if llm is not None else make_llm(m_name)
        m_sample_llm = sample_llm
        if m_sample_llm is None and system == "b2":
            m_sample_llm = with_temperature(m_llm, sample_temp)
        # Same as optverify/run.py: the rewordings are written at the paraphrase temperature.
        m_paraphrase_llm = with_temperature(m_llm, PARAPHRASE_TEMPERATURE)

        for r_idx in repeats_to_run:
            out_dir = results_path / exp_name / m_slug / f"repeat_{r_idx}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_dirs.append(out_dir)

            # Decoding settings
            temp = getattr(m_llm, "temperature", 0.0)
            decoding = {"temperature": temp}
            model_identifier = getattr(m_llm, "name", m_name)
            endpoint = _endpoint(model_identifier)

            config_data = {
                "experiment": exp_name,
                "system": system,
                "sample_file": str(sample_path),
                "k": k,
                "r": r,
                "budget": budget,
                "threshold": None if threshold == float("inf") else threshold,
                "alpha": alpha,
                "repeat": r_idx,
                "model": model_identifier,
                "endpoint": endpoint,
                "temperature": temp,
                "decoding": decoding,
                "prompt_version": get_prompt_version(),
                "git_commit": get_git_commit(),
                "notes": "Repeats differ only by provider nondeterminism and the paraphrase temperature.",
            }
            if system == "pipeline":
                config_data.update(
                    signals=list(signals), use_parser=use_parser, paraphrase_temperature=PARAPHRASE_TEMPERATURE
                )
            for opt_key in ("budget_from", "max_samples", "sample_temperature", "calibration"):
                if opt_key in config:
                    config_data[opt_key] = config[opt_key]

            config_text = _redact_secrets(json.dumps(config_data, indent=2))
            (out_dir / "config.json").write_text(config_text, encoding="utf-8")

            def solve(problem, active_llm=m_llm, active_sample_llm=m_sample_llm, active_paraphrase_llm=m_paraphrase_llm):
                if system == "baseline":
                    return run_baseline(problem, active_llm, max_repairs=r)
                if system == "b2":
                    return run_single_agent(
                        problem,
                        active_llm,
                        active_sample_llm,
                        token_budget=budget,
                        max_repairs=r,
                        threshold=threshold,
                        max_samples=max_samples,
                    )
                # Default to pipeline
                paraphrases = k if k is not None else 2
                return run_pipeline(
                    problem,
                    active_llm,
                    paraphrases=paraphrases,
                    max_repairs=r,
                    threshold=threshold,
                    signals=signals,
                    use_parser=use_parser,
                    paraphrase_llm=active_paraphrase_llm,
                )

            records = []
            with ThreadPoolExecutor(max_workers=workers) as pool, (out_dir / "records.jsonl").open("w", encoding="utf-8") as out:
                futures = {pool.submit(solve, problem): problem for problem in problems}
                for done, future in enumerate(as_completed(futures), start=1):
                    problem = futures[future]
                    try:
                        record = future.result().to_json()
                        print(f"[{done}/{len(problems)}] {record.get('problem_id')} {record.get('problem_class')}: correct={record.get('correct')}")
                    except Exception as error:
                        print(f"[{done}/{len(problems)}] {problem.problem_id} FAILED: {error}")
                        record = {
                            "problem_id": problem.problem_id,
                            "failed": True,
                            "error": str(error),
                        }
                    records.append(record)
                    out.write(json.dumps(record) + "\n")
                    out.flush()

            finished = [record for record in records if not record.get("failed")]
            failed_problems = [record.get("problem_id") for record in records if record.get("failed")]
            failed_rate = len(failed_problems) / len(problems) if problems else 0.0

            summary = {
                "run": f"{exp_name}_{m_slug}_repeat_{r_idx}",
                "config": config_data,
                "sample_size": len(problems),
                "failed_rate": failed_rate,
                "failed_problems": failed_problems,
                **summarize(finished),
            }
            summary_text = _redact_secrets(json.dumps(summary, indent=2))
            (out_dir / "summary.json").write_text(summary_text, encoding="utf-8")

    return out_dirs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run evaluation experiments E1 to E6.")
    parser.add_argument("experiment", help="Config name in experiments/configs (e.g. E1, E3, G3, E5-NOPARSER)")
    parser.add_argument("--repeat", type=int, default=None, help="Specific repeat index (0-based) to run")
    parser.add_argument("--model", default=None, help="Model specification (overrides config models)")
    parser.add_argument("--sample-file", type=Path, default=None, help="Override path to sample JSON file")
    parser.add_argument("--results-dir", type=Path, default=Path("results"), help="Results output directory")
    parser.add_argument("--workers", type=int, default=2, help="Number of worker threads")
    parser.add_argument("--env-file", default=".env", help="Environment file path")
    parser.add_argument("--budget-tokens", type=float, default=None, help="B2 only: token budget (overrides the config)")
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
            budget_tokens=args.budget_tokens,
        )
    except (FileNotFoundError, ValueError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
