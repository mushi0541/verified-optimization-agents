"""E6: efficiency and reliability of every run, from saved results only (no API calls).

Runs with the same configuration (system with its repairs or k, model, endpoint and problem set) are repeats of one
configuration, so each measure is given as the mean and sample standard deviation over its repeats:
- input and output tokens, LLM calls, solver calls and latency per problem;
- cost per problem in US$, at the price of the run's model in PRICES, stated with the date the price was read;
- reliability: failed-run rate (crashes or rejected requests; report objective D1 asks for under 5%), solver error
  and timeout rates over all solver calls of the main attempts, and the repair success rate (share of problems whose
  first model was not optimal that reached an optimal model after repair);
- tokens per step from usage_by_step, to show where each system spends its budget.

Counting rules, so the numbers match the records:
- tokens, calls, latency and cost cover finished problems only: no usage is saved for a failed problem, so when runs
  fail the cost is a lower bound;
- solver calls are the main attempts, plus one per paraphrase try in the pipeline (each try is one paraphraser and one
  formalizer call, so tries = calls / 2 of each paraphrase_<j> step), and for B2 the attempts of the samples it used;
- B2's tokens are those of the samples it used (its usage), as in the equal-budget comparison;
- a model missing from PRICES gets no cost (an empty cell), never another model's price; when a record stores
  usage_by_model (a second paraphrase model), each model's tokens are priced at that model's price, and a run with
  any unpriced model gets no cost;
- runs with different settings are never repeats of each other: the key includes the paraphrase model and the
  verifier switches (signals, no parser) from the run config, so ablation runs are not averaged with main runs;
- a measure a repeat cannot have (the repair success rate when nothing needed repair) is left out of the mean, and
  the output says how many repeats had a value;
- runs saved before Phase 2 have no endpoint in their config and no per-step tokens, and are labelled as such;
- repeats must come from the same code; pass --runs to choose the runs for a table.

Example:
    python scripts/efficiency.py --out-dir results/e6
    python scripts/efficiency.py --runs results/<run 1> results/<run 2> --out-dir results/e6
"""

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
# US$ per million tokens, with the date the price was read. Amazon Bedrock on-demand prices in us-east-1 (PR #14).
PRICES = {
    "openai.gpt-oss-120b-1:0": {"input": 0.15, "output": 0.60, "date": "2026-10-20"},
    "deepseek.v3.2": {"input": 0.62, "output": 1.85, "date": "2026-11-02"},  # the second paraphrase model (#56)
}
FAILED_RUN_TARGET = 0.05  # report objective D1
DEFAULT_SIGNALS = ("number", "requirement", "paraphrase")  # every Gap 1 signal on, the main configuration
RUN_METRICS = (
    "mean_input_tokens",
    "mean_output_tokens",
    "mean_llm_calls",
    "mean_solver_calls",
    "mean_latency_s",
    "mean_cost_usd",
    "failed_run_rate",
    "solver_error_rate",
    "solver_timeout_rate",
    "repair_success_rate",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="E6: efficiency and reliability from saved runs (no API calls).")
    parser.add_argument("--runs", nargs="+", help="run folders (default: every folder in results/ with a summary.json)")
    parser.add_argument("--out-dir", help="folder for efficiency.csv, tokens_by_step.csv and efficiency.json")
    args = parser.parse_args()

    folders = [Path(folder) for folder in args.runs] if args.runs else sorted(p.parent for p in RESULTS_DIR.glob("*/summary.json"))
    result = efficiency([load_run(folder) for folder in folders])
    if args.out_dir:
        write_tables(result, Path(args.out_dir))
    print(json.dumps({group["configuration"]: group["metrics"] for group in result["configurations"]}, indent=2))


def load_run(folder: Path) -> dict:
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    records_file = folder / "records.jsonl"
    lines = records_file.read_text(encoding="utf-8").splitlines() if records_file.exists() else []
    return {"name": folder.name, "summary": summary, "records": [json.loads(line) for line in lines if line.strip()]}


def run_system(run: dict) -> str:
    """The system with its setting, as records name it (baseline_r1, pipeline_p3, b2_r1). From summary.json when no
    problem finished, so a run where every problem failed still has a configuration."""
    if run["records"]:
        return run["records"][0]["system"]
    config = run["summary"].get("config", {})
    system = config.get("system", "unknown")
    if system == "pipeline":
        return f"pipeline_p{config.get('paraphrases')}"
    return f"{system}_r{config.get('repairs')}" if system in ("baseline", "b2") else system


def run_model(run: dict) -> str:
    """The model name as records store it (no provider prefix), so it matches the keys of PRICES."""
    if run["records"]:
        return run["records"][0]["model"]
    spec = run["summary"].get("config", {}).get("model", "unknown")
    return spec.partition(":")[2] or spec


def configuration(run: dict) -> str:
    """The key that makes runs repeats of each other. It ends with the problem set (the problems attempted, counting
    failed ones, and a short fingerprint of their IDs), so runs on different problems are never averaged together."""
    config = run["summary"].get("config", {})
    endpoint = config.get("endpoint") or "endpoint not recorded"
    attempted = sorted({record["problem_id"] for record in run["records"]} | set(run["summary"].get("failed_problems", [])))
    if config.get("sample_file"):
        problems = Path(str(config["sample_file"]).replace("\\", "/")).stem
    elif config:
        problems = f"{config['split']}, {config['per_class']} per class, seed {config['seed']}"
    else:
        problems = f"{attempted[0].split('-')[0] if attempted else 'unknown'}, sample not recorded"
    fingerprint = hashlib.sha256(" ".join(attempted).encode()).hexdigest()[:6]
    settings = run_settings(config)
    return (
        f"{run_system(run)} | {run_model(run)}{settings} | {endpoint} | {problems} | {len(attempted)} problems [{fingerprint}]"
    )


def run_settings(config: dict) -> str:
    """The settings that change what a pipeline run measures: a second paraphrase model and the verifier switches.
    Empty for the default settings, so older runs keep their key."""
    parts = []
    if config.get("system") == "pipeline" and config.get("paraphrase_model"):
        parts.append(f"paraphraser {config['paraphrase_model'].partition(':')[2] or config['paraphrase_model']}")
    signals = config.get("signals")
    if signals is not None and sorted(signals) != sorted(DEFAULT_SIGNALS):
        parts.append("signals " + ("+".join(signals) if signals else "none"))
    if config.get("no_parser"):
        parts.append("no parser")
    return "".join(f" [{part}]" for part in parts)


def run_metrics(run: dict) -> dict:
    records = run["records"]
    failed = len(run["summary"].get("failed_problems", []))
    solves = [attempt["solve"]["status"] for record in records for attempt in main_attempts(record)]
    started = [record for record in records if first_attempts(record)]
    needed_repair = [record for record in started if first_attempts(record)[0]["solve"]["status"] != "optimal"]
    model = run_model(run)
    input_tokens = [record["usage"]["input_tokens"] for record in records]
    output_tokens = [record["usage"]["output_tokens"] for record in records]
    attempted = len(records) + failed
    return {
        "problems": len(records),
        "failed_runs": failed,
        "mean_input_tokens": _mean(input_tokens),
        "mean_output_tokens": _mean(output_tokens),
        "mean_llm_calls": _mean(record["usage"]["calls"] for record in records),
        "mean_solver_calls": _mean(solver_calls(record) for record in records),
        "mean_latency_s": _mean(record["latency_s"] for record in records),
        "mean_cost_usd": _mean_or_none([record_cost(record, model) for record in records]),
        "failed_run_rate": failed / attempted if attempted else None,
        "solver_error_rate": solves.count("error") / len(solves) if solves else None,
        "solver_timeout_rate": solves.count("timeout") / len(solves) if solves else None,
        "repair_success_rate": (
            _mean(first_attempts(record)[-1]["solve"]["status"] == "optimal" for record in needed_repair)
            if any(len(first_attempts(record)) > 1 for record in needed_repair)
            else None
        ),
        "tokens_by_step": tokens_by_step(records),
    }


def first_attempts(record: dict) -> list[dict]:
    """The first formalize-and-repair round: the record's attempts (for B2 this is sample 1, its B1 run)."""
    return record.get("attempts") or []


def main_attempts(record: dict) -> list[dict]:
    """Every solver call that the record's answer rests on (all used samples for B2)."""
    if record.get("samples"):
        return [attempt for sample in record["samples"][: record.get("samples_used") or len(record["samples"])] for attempt in sample]
    return first_attempts(record)


def solver_calls(record: dict) -> int:
    calls = len(main_attempts(record))
    if record.get("verifier") and not record.get("samples"):  # pipeline: one solve per paraphrase try
        steps = record.get("usage_by_step") or {}
        paraphrase_steps = [usage for name, usage in steps.items() if name.startswith("paraphrase_")]
        if paraphrase_steps:
            calls += sum(usage["calls"] // 2 for usage in paraphrase_steps)
        else:  # records saved before Phase 2: one try per reworded run
            calls += len(record["verifier"]["paraphrase_objectives"])
    return calls


def cost_usd(input_tokens: int, output_tokens: int, price: dict) -> float:
    return (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000


def record_cost(record: dict, run_model_name: str) -> float | None:
    """US$ for one problem: each model's tokens at its own price (usage_by_model), or every token at the run model's
    price for records that do not split them. None when a model that was used has no price."""
    by_model = record.get("usage_by_model") or {run_model_name: record["usage"]}
    total = 0.0
    for model, usage in by_model.items():
        price = PRICES.get(model)
        if price is None:
            return None
        total += cost_usd(usage["input_tokens"], usage["output_tokens"], price)
    return total


def models_used(records: list[dict], run_model_name: str) -> list[str]:
    """Every model whose tokens a run's records hold, the run model first."""
    names = [run_model_name]
    for record in records:
        names += [model for model in record.get("usage_by_model") or {} if model not in names]
    return names


def tokens_by_step(records: list[dict]) -> dict[str, float] | None:
    """Mean tokens per problem for each step; a step a problem did not run counts as 0. B2's unused samples are left out."""
    if not records or not all(record.get("usage_by_step") for record in records):
        return None
    totals: dict[str, int] = {}
    for record in records:
        steps = record["usage_by_step"]
        if record.get("samples"):
            steps = {name: steps[name] for name in list(steps)[: record.get("samples_used") or len(steps)]}
        for name, usage in steps.items():
            totals[name] = totals.get(name, 0) + usage["input_tokens"] + usage["output_tokens"]
    return {name: total / len(records) for name, total in totals.items()}


def efficiency(runs: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for run in runs:
        groups.setdefault(configuration(run), []).append(run)
    configurations = []
    for key, members in groups.items():
        per_run = [run_metrics(run) for run in members]
        total_failed = sum(m["failed_runs"] for m in per_run)
        total_attempted = sum(m["problems"] + m["failed_runs"] for m in per_run)
        models = models_used([record for run in members for record in run["records"]], run_model(members[0]))
        configurations.append(
            {
                "configuration": key,
                "runs": [run["name"] for run in members],
                "problems_per_run": [m["problems"] for m in per_run],
                "metrics": {name: mean_and_sd([m[name] for m in per_run]) for name in RUN_METRICS},
                "price": {"model": models[0], **PRICES[models[0]]} if models[0] in PRICES else None,
                "other_model_prices": [{"model": m, **PRICES[m]} if m in PRICES else {"model": m} for m in models[1:]],
                "meets_failed_run_target": total_attempted > 0 and total_failed / total_attempted < FAILED_RUN_TARGET,
                "tokens_by_step": _mean_steps([m["tokens_by_step"] for m in per_run]),
            }
        )
    return {
        "prices_usd_per_million_tokens": PRICES,
        "price_source": "Amazon Bedrock on-demand, us-east-1",
        "failed_run_target": FAILED_RUN_TARGET,
        "configurations": configurations,
    }


def mean_and_sd(values: list) -> dict:
    """Mean and sample standard deviation (n - 1) over the repeats that have a value. A repeat without the measure
    (for example the repair success rate when nothing needed repair) is left out, and repeats_with_value says how many
    remained. The deviation needs 2 or more of them."""
    present = [value for value in values if value is not None]
    if not present:
        return {"mean": None, "sd": None, "repeats_with_value": 0}
    sd = statistics.stdev(present) if len(present) >= 2 else None
    return {"mean": statistics.mean(present), "sd": sd, "repeats_with_value": len(present)}


def _mean_steps(per_run: list[dict | None]) -> dict[str, float] | None:
    """Mean tokens per step over the repeats that have per-step tokens (a repeat in which every problem failed has
    none); None only when no repeat has them."""
    per_run = [steps for steps in per_run if steps is not None]
    if not per_run:
        return None
    names = list(dict.fromkeys(name for steps in per_run for name in steps))
    return {name: statistics.mean(steps.get(name, 0.0) for steps in per_run) for name in names}


def write_tables(result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "efficiency.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (out_dir / "efficiency.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["configuration", "repeats", "problems per run"]
            + [f"{name} ({part})" for name in RUN_METRICS for part in ("mean", "sd", "repeats with value")]
            + ["failed-run rate under 5%", "price input per million (US$)", "price output per million (US$)", "price date"]
        )
        for group in result["configurations"]:
            cells = [group["configuration"], len(group["runs"]), " ".join(map(str, group["problems_per_run"]))]
            for name in RUN_METRICS:
                metric = group["metrics"][name]
                cells += [metric["mean"], metric["sd"], metric["repeats_with_value"]]
            price = group["price"] or {}
            cells += [group["meets_failed_run_target"], price.get("input"), price.get("output"), price.get("date")]
            writer.writerow(["" if cell is None else cell for cell in cells])
    with (out_dir / "tokens_by_step.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["configuration", "step", "mean tokens per problem", "share of all tokens"])
        for group in result["configurations"]:
            steps = group["tokens_by_step"]
            if not steps:
                continue
            total = sum(steps.values())
            for name, tokens in steps.items():
                writer.writerow([group["configuration"], name, tokens, tokens / total if total else ""])


def _mean_or_none(values: list) -> float | None:
    """Mean of the values, or None when any value is missing (a cost cannot be partly known) or there are none."""
    return None if None in values else _mean(values)


def _mean(values) -> float | None:
    """Mean of the values, or None when there are none (a run in which every problem failed)."""
    values = list(values)
    return sum(values) / len(values) if values else None


if __name__ == "__main__":
    main()
