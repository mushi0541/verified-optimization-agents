"""The systems we compare.

- baseline:  base-paper style, one LLM call writes model code, then (optionally) repairs from solver errors.
- pipeline:  proposed five-role system: parser, formalizer, solver-runner, verifier, explainer,
             plus the answer / abstain / escalate decision.
"""

import json
import time

from . import prompts, roles, verifier
from .contracts import Problem, RunRecord, TokenUsage
from .grading import is_correct
from .llm import LLM


def run_baseline(problem: Problem, llm: LLM, max_repairs: int = 0) -> RunRecord:
    start = time.perf_counter()
    usage = TokenUsage()
    first_prompt = prompts.BASELINE_FORMALIZE.format(question=problem.question)
    attempts = roles.formalize_and_solve(first_prompt, problem.question, llm, usage, max_repairs)
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
        usage=usage,
        latency_s=time.perf_counter() - start,
    )


def run_pipeline(
    problem: Problem,
    llm: LLM,
    paraphrases: int = 2,
    max_repairs: int = 1,
    threshold: float = 0.8,
) -> RunRecord:
    start = time.perf_counter()
    usage = TokenUsage()

    spec = roles.parse_problem(problem.question, llm, usage)
    first_prompt = prompts.FORMALIZE_FROM_SPEC.format(question=problem.question, spec=json.dumps(spec, indent=1))
    attempts = roles.formalize_and_solve(first_prompt, problem.question, llm, usage, max_repairs)
    final = attempts[-1]

    other_objectives = []
    if final.solve.status == "optimal":
        for _ in range(paraphrases):
            reworded = roles.paraphrase(problem.question, llm, usage)
            reworded_prompt = prompts.BASELINE_FORMALIZE.format(question=reworded)
            reworded_attempts = roles.formalize_and_solve(reworded_prompt, reworded, llm, usage, max_repairs=0)
            other_objectives.append(reworded_attempts[-1].solve.objective)

    report = verifier.build_report(problem.question, final.code, final.solve.status, final.solve.objective, other_objectives)
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
        usage=usage,
        latency_s=time.perf_counter() - start,
        spec=spec,
        verifier=report,
        decision=decision,
        explanation=roles.explain(decision, report),
    )
