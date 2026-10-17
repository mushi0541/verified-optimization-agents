"""Command line entry point.

Examples:
    python -m optverify.run baseline --model openai:openai/gpt-oss-120b --split canonical --per-class 5
    python -m optverify.run pipeline --model openai:openai/gpt-oss-120b --split canonical --per-class 1
"""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .data import SPLIT_FILES, load_split, sample_per_class
from .grading import summarize
from .llm import make_llm
from .systems import run_baseline, run_pipeline

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the baseline or the proposed pipeline on OPT-Engine data.")
    parser.add_argument("system", choices=["baseline", "pipeline"])
    parser.add_argument("--model", required=True, help="e.g. openai:openai/gpt-oss-120b or bedrock:qwen.qwen3-32b-v1:0")
    parser.add_argument("--split", choices=sorted(SPLIT_FILES), default="canonical")
    parser.add_argument("--per-class", type=int, default=5, help="problems sampled from each problem class")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--repairs", type=int, default=0, help="solver-feedback repair rounds")
    parser.add_argument("--paraphrases", type=int, default=2, help="pipeline only: reworded runs for the verifier")
    parser.add_argument("--threshold", type=float, default=0.8, help="pipeline only: minimum verifier score to answer")
    parser.add_argument("--workers", type=int, default=2, help="parallel problems (keep low on free tiers)")
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()

    load_dotenv(args.env_file, override=False)
    llm = make_llm(args.model)
    problems = sample_per_class(load_split(args.split), args.per_class, args.seed)

    def solve(problem):
        if args.system == "baseline":
            return run_baseline(problem, llm, max_repairs=args.repairs)
        return run_pipeline(problem, llm, args.paraphrases, args.repairs, args.threshold)

    run_name = f"{args.system}_{_slug(args.model)}_{args.split}_r{args.repairs}_{datetime.now():%Y%m%d-%H%M}"
    out_dir = RESULTS_DIR / run_name
    out_dir.mkdir(parents=True, exist_ok=True)

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
        "config": vars(args),
        "failed_problems": [record["problem_id"] for record in records if "failed" in record],
        **summarize(finished),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in summary if key != "config"}, indent=2))


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9.-]+", "-", text).strip("-")


if __name__ == "__main__":
    main()
