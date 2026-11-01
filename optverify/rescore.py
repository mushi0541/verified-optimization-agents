"""Rescore a saved pipeline record for an ablation, with no LLM calls.

A record stores every signal, the optimum of every paraphrase run and the tokens of every step, so a smaller
configuration can be read from a full one:
- signals: only the enabled signals count in the score (ablations i to iii); without the paraphrase signal the
  paraphrase runs and their tokens are dropped, as a run with that switch would not make them;
- k: only the first k paraphrase runs and their tokens are kept (ablation v);
- no repair: the first attempt is the final model (ablation vii, r = 0 from an r = 1 run). A first attempt that is
  optimal never ran a repair; one that is not means the pipeline abstains and makes no paraphrase runs.
"""

from .grading import is_correct
from .verifier import SIGNALS, combined_score, paraphrase_agreement


def rescore(record: dict, signals: tuple[str, ...] = SIGNALS, k: int | None = None, repairs: bool = True) -> dict:
    """The outcome of one saved pipeline record under a smaller configuration.

    Returns the answer (None when the pipeline abstains), the score, whether the answer is correct, and the tokens
    and LLM calls the smaller configuration would have used.
    """
    report = record["verifier"]
    attempt = record["attempts"][-1] if repairs else record["attempts"][0]
    feasible = report["feasible"] and attempt["solve"]["status"] == "optimal"
    others = report["paraphrase_objectives"]
    k = len(others) if k is None else k
    if feasible and len(others) < k:
        raise ValueError(f"{record['problem_id']} has {len(others)} paraphrase runs, fewer than k = {k}")
    if "paraphrase" not in signals or not feasible:
        k = 0

    objective = attempt["solve"]["objective"] if feasible else None
    agreement = paraphrase_agreement(objective, others[:k]) if k else None
    dropped = [f"paraphrase_{j}" for j in range(k + 1, len(others) + 1)] + ([] if repairs else ["repair"])
    score = combined_score(feasible, report["number_coverage"], agreement, report.get("requirement_coverage"), signals)
    return {
        "problem_id": record["problem_id"],
        "problem_class": record.get("problem_class"),
        "answer": objective,
        "feasible": feasible,
        "score": score,
        "correct": is_correct(objective, record["reference"]),
        **usage_without(record, dropped),
    }


def usage_without(record: dict, dropped_steps: list[str]) -> dict:
    """Tokens and calls of a record without some of its steps (usage_by_step must hold them)."""
    total = record["usage"]
    tokens, calls = total["input_tokens"] + total["output_tokens"], total["calls"]
    steps = record.get("usage_by_step") or {}
    for name in dropped_steps:
        if name not in steps:
            if not steps:
                raise ValueError(f"{record['problem_id']} has no usage_by_step; rescoring needs records saved in Phase 2")
            continue  # the step never ran (no repair was needed, or no paraphrase run was made)
        tokens -= steps[name]["input_tokens"] + steps[name]["output_tokens"]
        calls -= steps[name]["calls"]
    return {"tokens": tokens, "calls": calls}
