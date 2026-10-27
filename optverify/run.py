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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from .data import SPLIT_FILES, load_sample_file, load_split, sample_per_class
from .grading import summarize
from .llm import make_llm, with_temperature
from .systems import run_baseline, run_pipeline, run_single_agent
from .trace import TraceWriter

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


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
    parser.add_argument("--threshold", type=float, default=0.8, help="pipeline and b2: minimum score to answer")
    parser.add_argument(
        "--budget-tokens", type=float, help="b2 only: tokens per problem to sample up to (the pipeline's mean tokens at the largest k)"
    )
    parser.add_argument("--max-samples", type=int, default=10, help="b2 only: most samples per problem")
    parser.add_argument("--sample-temperature", type=float, default=0.7, help="b2 only: temperature of samples 2, 3, ...")
    parser.add_argument("--workers", type=int, default=2, help="parallel problems (keep low on free tiers)")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--trace", action="store_true", help="write per-step trace logs to logs/<run_name>/<problem_id>.jsonl")
    return parser


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
    return args


def main() -> None:
    args = parse_args()

    load_dotenv(args.env_file, override=False)
    llm = make_llm(args.model)
    sample_llm = with_temperature(llm, args.sample_temperature)
    if args.sample_file:
        problems = load_sample_file(args.sample_file)
    else:
        problems = sample_per_class(load_split(args.split), args.per_class, args.seed)

    split_tag = args.sample_file.stem if args.sample_file else args.split
    run_name = f"{args.system}_{_slug(args.model)}_{split_tag}_r{args.repairs}_{datetime.now():%Y%m%d-%H%M}"
    out_dir = RESULTS_DIR / run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir = Path("logs") / run_name if args.trace else None

    def solve(problem):
        trace = TraceWriter(log_dir / f"{problem.problem_id}.jsonl") if log_dir else None
        if args.system == "baseline":
            return run_baseline(problem, llm, max_repairs=args.repairs, trace=trace)
        if args.system == "b2":
            return run_single_agent(
                problem, llm, sample_llm, args.budget_tokens, args.repairs, args.threshold, args.max_samples, trace=trace
            )
        return run_pipeline(problem, llm, args.paraphrases, args.repairs, args.threshold, trace=trace)

    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool, (out_dir / "records.jsonl").open("w", encoding="utf-8") as out:
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
        "run": run_name,
        "config": {**{k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}, "endpoint": _endpoint(args.model)},
        "failed_problems": [record["problem_id"] for record in records if "failed" in record],
        **summarize(finished),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in summary if key != "config"}, indent=2))


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9.-]+", "-", text).strip("-")


def _endpoint(model: str) -> str:
    """Where the model was served (host name only, never credentials), so runs on different providers are not mixed."""
    if model.startswith("bedrock:"):
        return f"bedrock {os.getenv('AWS_REGION', 'us-east-1')}"
    return urlparse(os.getenv("LLM_BASE_URL", "")).hostname or "unknown"


if __name__ == "__main__":
    main()
