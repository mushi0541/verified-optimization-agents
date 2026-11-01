"""Command line entry point.

Examples:
    python -m optverify.run baseline --model bedrock:openai.gpt-oss-120b-1:0 --split canonical --per-class 5
    python -m optverify.run pipeline --model bedrock:openai.gpt-oss-120b-1:0 --split canonical --per-class 1
    python -m optverify.run b2 --model bedrock:openai.gpt-oss-120b-1:0 --split canonical --per-class 10 --repairs 1 --budget-tokens 24000
"""

import argparse
import json
import os
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from .calibration import check_system, threshold_from_file
from .data import SPLIT_FILES, load_sample_file, load_split, sample_per_class
from .grading import summarize
from .llm import LLM, make_llm, with_temperature
from .systems import PARAPHRASE_TEMPERATURE, run_baseline, run_pipeline, run_single_agent
from .trace import TraceWriter
from .verifier import SIGNALS

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a baseline (B0/B1 or B2) or the proposed pipeline on OPT-Engine or OpsOR-Bench data.")
    parser.add_argument("system", choices=["baseline", "pipeline", "b2"])
    parser.add_argument("--model", required=True, help="e.g. bedrock:openai.gpt-oss-120b-1:0 or openai:openai/gpt-oss-120b")
    parser.add_argument("--split", choices=sorted(SPLIT_FILES), default="canonical")
    parser.add_argument("--sample-file", type=Path, help="path to a fixed evaluation sample JSON file")
    parser.add_argument("--per-class", type=int, default=None, help="problems sampled from each problem class")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--repairs", type=int, default=0, help="solver-feedback repair rounds")
    parser.add_argument("--paraphrases", type=int, default=2, help="pipeline only: reworded runs for the verifier")
    parser.add_argument(
        "--signals",
        type=parse_signals,
        default=SIGNALS,
        help="pipeline only: verifier signals in the score, comma-separated from number,requirement,paraphrase, or "
        "'none' for feasibility alone (default: all; paraphrase runs are skipped without paraphrase)",
    )
    parser.add_argument(
        "--no-parser", action="store_true", help="pipeline only: formalize from the question alone (ablation iv)"
    )
    parser.add_argument("--threshold", type=float, default=0.8, help="pipeline and b2: minimum score to answer")
    parser.add_argument(
        "--calibration", type=Path, help="pipeline and b2: calibration file from scripts/calibrate.py; replaces --threshold (Gap 2)"
    )
    parser.add_argument(
        "--budget-tokens", type=float, help="b2 only: tokens per problem to sample up to (the pipeline's mean tokens at the largest k)"
    )
    parser.add_argument("--max-samples", type=int, default=10, help="b2 only: most samples per problem")
    parser.add_argument("--sample-temperature", type=float, default=0.7, help="b2 only: temperature of samples 2, 3, ...")
    parser.add_argument(
        "--paraphrase-temperature", type=float, default=PARAPHRASE_TEMPERATURE, help="pipeline only: temperature of the paraphraser"
    )
    parser.add_argument(
        "--paraphrase-model",
        help="pipeline only: model that writes the rewordings, e.g. bedrock:deepseek.v3.2 (default: --model); "
        "each rewording is still solved by --model",
    )
    parser.add_argument("--workers", type=int, default=2, help="parallel problems (keep low on free tiers)")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--trace", action="store_true", help="write per-step trace logs to logs/<run_name>/<problem_id>.jsonl")
    parser.add_argument(
        "--resume",
        type=Path,
        help="a results folder of an earlier run with the same settings: run only the problems missing from its "
        "records.jsonl (failed or never started, for example after a network outage) and add them to it",
    )
    return parser


# Settings that may differ when a run is resumed: they do not change any record.
RESUME_FREE_KEYS = {"resume", "workers", "env_file", "trace"}


def parse_signals(text: str) -> tuple[str, ...]:
    """'number,paraphrase' -> ('number', 'paraphrase'), kept in the fixed order of SIGNALS; 'none' -> ()."""
    names = set() if text.strip() == "none" else {name.strip() for name in text.split(",")}
    unknown = names - set(SIGNALS)
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown signal(s) {', '.join(sorted(unknown))}; use {', '.join(SIGNALS)}")
    return tuple(name for name in SIGNALS if name in names)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.system == "b2" and not args.budget_tokens:
        parser.error("b2 needs --budget-tokens")
    if args.sample_file:
        if args.per_class is not None or args.seed is not None:
            parser.error("--sample-file cannot be combined with --per-class or --seed")
    else:
        if args.per_class is None:
            args.per_class = 5
        if args.seed is None:
            args.seed = 0
    args.alpha = None
    if args.calibration:
        calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
        if args.system == "baseline":
            parser.error("--calibration is for pipeline and b2 only")
        try:
            if args.system == "pipeline":  # the record's system name: paraphrase runs are skipped without the signal
                runs = args.paraphrases if "paraphrase" in args.signals else 0
                check_system(calibration, f"pipeline_p{runs}", args.signals, not args.no_parser)
            else:
                check_system(calibration, f"b2_r{args.repairs}")
        except ValueError as error:
            parser.error(str(error))
        args.alpha = calibration["alpha"]
        args.threshold = threshold_from_file(calibration)
    return args


def main() -> None:
    args = parse_args()

    load_dotenv(args.env_file, override=False)
    llm = make_llm(args.model)
    sample_llm = with_temperature(llm, args.sample_temperature)
    paraphrase_llm = paraphrase_client(args, llm)
    if args.sample_file:
        problems = load_sample_file(args.sample_file)
    else:
        problems = sample_per_class(load_split(args.split), args.per_class, args.seed)

    config = run_config(args)
    records, resumes = [], 0
    if args.resume:
        out_dir = args.resume
        records, resumes = resume_state(out_dir, config)
        finished_ids = {record["problem_id"] for record in records}
        problems = [problem for problem in problems if problem.problem_id not in finished_ids]
        print(f"Resuming {out_dir.name}: {len(finished_ids)} problems already finished, {len(problems)} to run")
    else:
        split_tag = args.sample_file.stem if args.sample_file else args.split
        paraphraser_tag = f"_para-{_slug(args.paraphrase_model)}" if args.system == "pipeline" and args.paraphrase_model else ""
        run_name = f"{args.system}_{_slug(args.model)}{paraphraser_tag}_{split_tag}_r{args.repairs}_{datetime.now():%Y%m%d-%H%M}"
        out_dir = RESULTS_DIR / run_name
        out_dir.mkdir(parents=True, exist_ok=True)
    log_dir = LOGS_DIR / out_dir.name if args.trace else None  # a resumed run keeps its log folder

    def solve(problem):
        trace = TraceWriter(log_dir / f"{problem.problem_id}.jsonl") if log_dir else None
        if args.system == "baseline":
            return run_baseline(problem, llm, max_repairs=args.repairs, trace=trace)
        if args.system == "b2":
            return run_single_agent(
                problem, llm, sample_llm, args.budget_tokens, args.repairs, args.threshold, args.max_samples, trace=trace
            )
        return run_pipeline(
            problem,
            llm,
            args.paraphrases,
            args.repairs,
            args.threshold,
            signals=args.signals,
            use_parser=not args.no_parser,
            paraphrase_llm=paraphrase_llm,
            trace=trace,
        )

    mode = "a" if args.resume else "w"
    with ThreadPoolExecutor(max_workers=args.workers) as pool, (out_dir / "records.jsonl").open(mode, encoding="utf-8") as out:
        futures = {pool.submit(solve, problem): problem for problem in problems}
        for done, future in enumerate(as_completed(futures), start=1):
            problem = futures[future]
            try:
                record = future.result().to_json()
            except Exception as error:  # keep the run going; failed problems are listed in the summary
                print(f"[{done}/{len(problems)}] {problem.problem_id} FAILED: {error}")
                records.append({"problem_id": problem.problem_id, "failed": str(error)})
                continue
            records.append(record)
            out.write(json.dumps(record) + "\n")
            out.flush()
            print(f"[{done}/{len(problems)}] {record['problem_id']} {record['problem_class']}: correct={record['correct']}")

    finished = [record for record in records if "failed" not in record]
    summary = {
        "run": out_dir.name,
        "config": config,
        "resumes": resumes + 1 if args.resume else 0,  # how many times the run was continued after failures
        "failed_problems": [record["problem_id"] for record in records if "failed" in record],
        **summarize(finished),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in summary if key != "config"}, indent=2))


def run_config(args: argparse.Namespace) -> dict:
    """The settings saved in summary.json."""
    return {
        **{k: _config_value(v) for k, v in vars(args).items()},
        "endpoint": _endpoint(args.model),
        "paraphrase_endpoint": _endpoint(args.paraphrase_model or args.model),
    }


def resume_state(out_dir: Path, config: dict) -> tuple[list[dict], int]:
    """The finished records of an earlier run, and how often it was resumed; refuses a run with other settings.

    The earlier run's summary.json is needed to check the settings, so a run stopped before writing it cannot be
    resumed this way.
    """
    summary_file, records_file = out_dir / "summary.json", out_dir / "records.jsonl"
    if not summary_file.exists() or not records_file.exists():
        raise SystemExit(f"--resume needs {out_dir} with records.jsonl and summary.json from an earlier run")
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    earlier = summary["config"]
    config = json.loads(json.dumps(config))  # compare as saved: tuples become lists
    different = sorted(
        key for key in (set(earlier) | set(config)) - RESUME_FREE_KEYS if earlier.get(key) != config.get(key)
    )
    if different:
        raise SystemExit(f"--resume: the settings differ from the earlier run in {', '.join(different)}")
    records = [json.loads(line) for line in records_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return records, summary.get("resumes", 0)


def _config_value(value):
    """JSON-safe config values: paths as text, and an infinite threshold (answer nothing) as None."""
    if isinstance(value, Path):
        return str(value)
    if value == float("inf"):
        return None
    return value


def paraphrase_client(args: argparse.Namespace, llm: LLM, make: Callable[[str], LLM] | None = None) -> LLM:
    """The client that writes the rewordings, at the paraphrase temperature: a second model when --paraphrase-model
    is given (so the paraphraser's mistakes are less correlated with the formalizer's), otherwise the main model.
    make builds the second client (make_llm when not given)."""
    base = (make or make_llm)(args.paraphrase_model) if args.paraphrase_model else llm
    return with_temperature(base, args.paraphrase_temperature)


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9.-]+", "-", text).strip("-")


def _endpoint(model: str) -> str:
    """Where the model was served (host name only, never credentials), so runs on different providers are not mixed."""
    if model.startswith("bedrock:"):
        return f"bedrock {os.getenv('AWS_REGION', 'us-east-1')}"
    return urlparse(os.getenv("LLM_BASE_URL", "")).hostname or "unknown"


if __name__ == "__main__":
    main()
