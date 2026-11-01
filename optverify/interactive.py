"""Shared helper for interactive optimization problem solving."""

from .contracts import Problem, RunRecord
from .llm import LLM, with_temperature
from .systems import PARAPHRASE_TEMPERATURE, run_pipeline

MAX_QUESTION_LENGTH = 4000


def solve_interactive_problem(
    question: str,
    llm: LLM,
    paraphrases: int = 2,
    max_repairs: int = 1,
    threshold: float = 0.8,
) -> RunRecord:
    """Run the verification pipeline on a single interactive question."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty or whitespace only.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"Question exceeds maximum length of {MAX_QUESTION_LENGTH} characters.")

    problem = Problem(
        problem_id="interactive",
        question=question.strip(),
        answer=None,
        problem_class="interactive",
        size=0,
        split="interactive",
    )
    return run_pipeline(
        problem,
        llm,
        paraphrases=paraphrases,
        max_repairs=max_repairs,
        threshold=threshold,
        paraphrase_llm=with_temperature(llm, PARAPHRASE_TEMPERATURE),
    )
