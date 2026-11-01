"""The systems we compare.

- baseline:  base-paper style, one LLM call writes model code, then (optionally) repairs from solver errors.
- pipeline:  proposed five-role system: parser, formalizer, solver-runner, verifier, explainer,
             plus the answer / abstain / escalate decision.
- b2:        single agent at an equal token budget (Gap 3): B1 plus independent samples until the token budget
             is used; answers with the most frequent optimum, scored by the agreement rate among samples.
"""

import json
import time

from . import prompts, roles, verifier
from .contracts import Problem, RunRecord, TokenUsage
from .grading import is_correct, same_optimum
from .llm import LLM


def run_baseline(problem: Problem, llm: LLM, max_repairs: int = 0) -> RunRecord:
    start = time.perf_counter()
    steps = {"formalize": TokenUsage(), "repair": TokenUsage()}
    first_prompt = prompts.BASELINE_FORMALIZE.format(question=problem.question)
    attempts = roles.formalize_and_solve(
        first_prompt, problem.question, llm, steps["formalize"], max_repairs, repair_usage=steps["repair"]
    )
    predicted = attempts[-1].solve.objective
    return RunRecord(
        problem_id=problem.problem_id,
        problem_class=problem.problem_class,
        size=problem.size,
        system=f"baseline_r{max_repairs}",
        model=llm.name,
        reference=problem.answer,
        predicted=predicted,
        correct=is_correct(predicted, problem.answer),
        attempts=attempts,
        usage=TokenUsage.total(steps),
        latency_s=time.perf_counter() - start,
        usage_by_step=steps,
    )


# Report Section 2.7: the paraphraser samples at temperature 0.7, because rewordings at temperature 0 are almost identical.
PARAPHRASE_TEMPERATURE = 0.7


def run_pipeline(
    problem: Problem,
    llm: LLM,
    paraphrases: int = 2,
    max_repairs: int = 1,
    threshold: float = 0.8,
    signals: tuple[str, ...] = verifier.SIGNALS,
    use_parser: bool = True,
    paraphrase_llm: LLM | None = None,
) -> RunRecord:
    """The proposed pipeline.

    paraphrase_llm writes the rewordings (PARAPHRASE_TEMPERATURE in the main runs); without it, llm does. Every other
    call, including the formalizer call on each rewording, uses llm. For ablations, `signals` sets which verifier
    signals count in the score (paraphrase runs are skipped when that signal is off), and use_parser=False formalizes
    from the question alone with the baseline prompt, so no requirements are listed (ablation iv).
    """
    start = time.perf_counter()
    paraphraser = paraphrase_llm or llm
    steps = {"parse": TokenUsage(), "formalize": TokenUsage(), "repair": TokenUsage()}

    if use_parser:
        spec, required = roles.number_requirements(roles.parse_problem(problem.question, llm, steps["parse"]))
        first_prompt = prompts.FORMALIZE_FROM_SPEC.format(question=problem.question, spec=json.dumps(spec, indent=1))
    else:
        spec, required = None, []
        first_prompt = prompts.BASELINE_FORMALIZE.format(question=problem.question)
    if "paraphrase" not in signals:
        paraphrases = 0
    attempts = roles.formalize_and_solve(
        first_prompt, problem.question, llm, steps["formalize"], max_repairs, repair_usage=steps["repair"],
        repair_note=prompts.KEEP_CONSTRAINT_NAMES if required else "",
    )
    final = attempts[-1]

    other_objectives = []
    if final.solve.status == "optimal":
        for run_number in range(1, paraphrases + 1):
            # One step per paraphrase run (paraphraser call plus its formalizer call, and the retry when the first
            # try returns no optimum), so lower k can be read from saved records by dropping the last runs.
            step = steps[f"paraphrase_{run_number}"] = TokenUsage()
            objective = _reworded_optimum(problem.question, llm, paraphraser, step)
            if objective is None:  # retry once, so a failed run is not mistaken for a disagreement
                objective = _reworded_optimum(problem.question, llm, paraphraser, step)
            other_objectives.append(objective)

    report = verifier.build_report(
        problem.question, final.code, final.solve.status, final.solve.objective, other_objectives,
        required, final.solve.requirement_ids, signals,
    )
    decision = verifier.decide(report, final.solve.objective, threshold)
    return RunRecord(
        problem_id=problem.problem_id,
        problem_class=problem.problem_class,
        size=problem.size,
        system=f"pipeline_p{paraphrases}",
        model=llm.name,
        reference=problem.answer,
        predicted=decision.answer,
        correct=is_correct(decision.answer, problem.answer),
        attempts=attempts,
        usage=TokenUsage.total(steps),
        latency_s=time.perf_counter() - start,
        spec=spec,
        verifier=report,
        decision=decision,
        explanation=roles.explain(decision, report, final.solve.variables),
        usage_by_step=steps,
    )


def _reworded_optimum(question: str, llm: LLM, paraphraser: LLM, usage: TokenUsage) -> float | None:
    """Reword the question with paraphraser, then solve it with llm, the baseline prompt and no repair; None if no
    optimum is found."""
    reworded = roles.paraphrase(question, paraphraser, usage)
    reworded_prompt = prompts.BASELINE_FORMALIZE.format(question=reworded)
    attempts = roles.formalize_and_solve(reworded_prompt, reworded, llm, usage, max_repairs=0)
    return attempts[-1].solve.objective


def run_single_agent(
    problem: Problem,
    llm: LLM,
    sample_llm: LLM,
    token_budget: float,
    max_repairs: int = 1,
    threshold: float = 0.8,
    max_samples: int = 10,
) -> RunRecord:
    """B2. Sample 1 is B1 (llm, temperature 0); later samples use sample_llm (temperature 0.7 in the main runs).

    Samples are drawn until their tokens reach token_budget (or max_samples), once per problem; smaller budget
    levels are read from the same record with samples_within_budget. Each sample is one formalizer call with
    up to max_repairs repairs driven by the solver status or error text, as in B1.
    """
    start = time.perf_counter()
    steps: dict[str, TokenUsage] = {}
    samples = []
    first_prompt = prompts.BASELINE_FORMALIZE.format(question=problem.question)
    while len(samples) < max_samples and (not samples or _tokens(TokenUsage.total(steps)) < token_budget):
        step = steps[f"sample_{len(samples) + 1}"] = TokenUsage()
        sampler = llm if not samples else sample_llm
        samples.append(roles.formalize_and_solve(first_prompt, problem.question, sampler, step, max_repairs))

    used = samples_within_budget([_tokens(usage) for usage in steps.values()], token_budget)
    # B2 is charged only for the samples behind its answer; later samples stay in samples and usage_by_step.
    used_steps = {name: steps[name] for name in list(steps)[:used]}
    answer, agreement = majority_vote([attempts[-1].solve.objective for attempts in samples[:used]])
    decision = verifier.decide_by_agreement(answer, agreement, used, threshold)
    return RunRecord(
        problem_id=problem.problem_id,
        problem_class=problem.problem_class,
        size=problem.size,
        system=f"b2_r{max_repairs}",
        model=llm.name,
        reference=problem.answer,
        predicted=decision.answer,
        correct=is_correct(decision.answer, problem.answer),
        attempts=samples[0],
        usage=TokenUsage.total(used_steps),
        latency_s=time.perf_counter() - start,
        decision=decision,
        explanation=" ".join(decision.reasons),
        usage_by_step=steps,
        samples=samples,
        token_budget=token_budget,
        sample_agreement=agreement,
        samples_used=used,
    )


def majority_vote(objectives: list[float | None]) -> tuple[float | None, float]:
    """B2's answer and score: the most frequent optimum among the samples and the share of samples that reach it.

    Optima are compared with the verifier's tolerance, failed samples (None) count as disagreeing, and a tie
    goes to the optimum that was found first.
    """
    best, best_count = None, 0
    for candidate in objectives:
        if candidate is None:
            continue
        count = sum(same_optimum(candidate, other) for other in objectives)
        if count > best_count:
            best, best_count = candidate, count
    return best, (best_count / len(objectives) if objectives else 0.0)


def samples_within_budget(sample_tokens: list[int], budget: float) -> int:
    """How many of the first samples to use so their total tokens is closest to budget (at least one).

    A tie goes to fewer samples.
    """
    best_count, best_gap, spent = 1, float("inf"), 0
    for count, tokens in enumerate(sample_tokens, start=1):
        spent += tokens
        if abs(spent - budget) < best_gap:
            best_count, best_gap = count, abs(spent - budget)
    return best_count


def _tokens(usage: TokenUsage) -> int:
    return usage.input_tokens + usage.output_tokens
