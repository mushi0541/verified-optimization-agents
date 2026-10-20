"""Base abstractions and helpers for OpsOR-Bench problem generators."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from optverify.contracts import Problem


@dataclass
class OpsORInstance:
    """Represents a generated OpsOR problem instance."""

    family: str
    size: int
    seed: int
    question: str
    answer: float
    params: dict = field(default_factory=dict)
    reference_code: str = ""

    def to_problem(self, problem_id: str) -> Problem:
        """Convert to the standard Problem dataclass."""
        return Problem(
            problem_id=problem_id,
            question=self.question,
            answer=self.answer,
            problem_class=self.family,
            size=self.size,
            split="opsor",
            meta={
                "seed": self.seed,
                "family": self.family,
                "params": self.params,
                "reference_code": self.reference_code,
            },
        )


def extract_numbers_from_text(text: str) -> set[float]:
    """Extract all numbers from text for audit and verification."""
    found = set()
    for token in re.findall(r"\b\d+(?:\.\d+)?\b", text):
        try:
            val = float(token)
            found.add(val)
            if val.is_integer():
                found.add(int(val))
        except ValueError:
            pass
    return found


def assert_question_contains_numbers(question: str, numbers: list[float | int]) -> None:
    """Ensure every numerical parameter used by the reference model appears in the question text."""
    found = extract_numbers_from_text(question)
    for num in numbers:
        target = float(num)
        if target not in found and (int(target) if target.is_integer() else None) not in found:
            raise AssertionError(f"Parameter value {num} missing from question text:\n{question}")
