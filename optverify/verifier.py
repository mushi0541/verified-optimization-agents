"""Verifier signals and the answer / abstain / escalate decision.

Phase 1 status: the signals are implemented; the score weights and the threshold are placeholders.
Phase 2 replaces the fixed threshold with one calibrated to a target wrong-accept rate (Gap 2).
"""

import re

from .contracts import Decision, VerifierReport
from .grading import same_optimum

_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?")


def numbers_in(text: str) -> set[float]:
    """Numeric values in a text. 0 and 1 are skipped because they appear everywhere (indices, binaries)."""
    values = set()
    for token in _NUMBER.findall(text):
        value = float(token.replace(",", ""))
        if value not in (0.0, 1.0):
            values.add(value)
    return values


def number_coverage(question: str, code: str) -> tuple[float, list[str]]:
    """Share of the question's numbers that also appear in the model code (Gap 1, data coverage)."""
    needed = numbers_in(question)
    if not needed:
        return 1.0, []
    present = numbers_in(code)
    missing = sorted(value for value in needed if value not in present)
    return 1 - len(missing) / len(needed), [f"{value:g}" for value in missing]


def paraphrase_agreement(main_objective: float | None, other_objectives: list[float | None]) -> float | None:
    """Share of reworded-question runs that reach the same optimum as the main run (Gap 1)."""
    if not other_objectives:
        return None
    return sum(same_optimum(main_objective, other) for other in other_objectives) / len(other_objectives)


def build_report(
    question: str,
    code: str,
    status: str,
    objective: float | None,
    other_objectives: list[float | None],
) -> VerifierReport:
    feasible = status == "optimal" and objective is not None
    coverage, missing = number_coverage(question, code)
    agreement = paraphrase_agreement(objective, other_objectives)
    signals = [coverage] if agreement is None else [coverage, agreement]
    score = sum(signals) / len(signals) if feasible else 0.0
    return VerifierReport(feasible, coverage, missing, agreement, list(other_objectives), score)


def decide(report: VerifierReport, objective: float | None, threshold: float) -> Decision:
    if not report.feasible:
        return Decision("abstain", None, ["No feasible optimal model was produced after repairs."])

    reasons = []
    if report.missing_numbers:
        reasons.append("Numbers from the question not used in the model: " + ", ".join(report.missing_numbers[:10]) + ".")
    if report.paraphrase_agreement is not None and report.paraphrase_agreement < 1:
        reasons.append("Reworded versions of the question gave different optimal values.")
    return _answer_or_escalate(report.score, objective, threshold, reasons)


def decide_by_agreement(answer: float | None, agreement: float, samples: int, threshold: float) -> Decision:
    """The same decision rule for the single agent B2, with its sample agreement rate as the score (Gap 3)."""
    if answer is None:
        return Decision("abstain", None, ["No sample produced a feasible optimal model after repairs."])
    reasons = []
    if agreement < 1:
        reasons.append(f"Only {round(agreement * samples)} of {samples} independent samples reached this optimal value.")
    return _answer_or_escalate(agreement, answer, threshold, reasons)


def _answer_or_escalate(score: float, objective: float | None, threshold: float, reasons: list[str]) -> Decision:
    if score >= threshold:
        return Decision("answer", objective, reasons)
    return Decision("escalate", objective, reasons or [f"Verifier score {score:.2f} is below {threshold:.2f}."])
