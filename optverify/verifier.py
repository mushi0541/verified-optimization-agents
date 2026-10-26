"""Verifier signals and the answer / abstain / escalate decision.

Phase 1 status: the signals are implemented; the score weights and the threshold are placeholders.
Phase 2 replaces the fixed threshold with one calibrated to a target wrong-accept rate (Gap 2).
"""

import re

from .contracts import Decision, VerifierReport
from .grading import same_optimum

_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?")
_CODE_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:_\d{3})*(?:\.\d+)?")
_LABELLED_NUMBER = re.compile(r"\b([A-Z][a-z]+) (\d+)\b(?![.,]\d)")
_PERCENT = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s?%")


def numbers_in(text: str, in_code: bool = False) -> set[float]:
    """Numeric values in a text. 0 and 1 are skipped because they appear everywhere (indices, binaries).

    In code a comma always separates values, as in (3,14,100.2), so only text reads "1,200" as one number;
    code may group digits with underscores instead (1_200).
    """
    values = set()
    for token in (_CODE_NUMBER if in_code else _NUMBER).findall(text):
        value = float(token.replace(",", "").replace("_", ""))
        if value not in (0.0, 1.0):
            values.add(value)
    return values


def without_index_numbers(text: str) -> str:
    """Remove item labels such as "Package 3" or "Leg 2", which name items instead of giving data.

    A capitalized word counts as a label when the integers after it in the text form an unbroken run of at least two
    (1, 2, 3 or 4, 5, 6, 7). A repeated word with other numbers, such as "Each 30 ... Each 45", keeps them as data.
    """
    numbers_per_word: dict[str, set[int]] = {}
    for word, number in _LABELLED_NUMBER.findall(text):
        numbers_per_word.setdefault(word, set()).add(int(number))
    labels = {word for word, numbers in numbers_per_word.items() if _is_unbroken_run(numbers)}
    return _LABELLED_NUMBER.sub(lambda match: f"{match[1]} #" if match[1] in labels else match[0], text)


def _is_unbroken_run(numbers: set[int]) -> bool:
    return len(numbers) >= 2 and max(numbers) - min(numbers) == len(numbers) - 1


def number_coverage(question: str, code: str) -> tuple[float, list[str]]:
    """Share of the question's data numbers that also appear in the model code (Gap 1, data coverage).

    Item labels are ignored, and a percentage also counts as present when the code uses it as a fraction (24% as 0.24).
    """
    needed = numbers_in(without_index_numbers(question))
    if not needed:
        return 1.0, []
    present = numbers_in(code, in_code=True)
    present_rounded = {round(value, 9) for value in present}
    percents = {float(token) for token in _PERCENT.findall(question)}

    def is_used(value: float) -> bool:
        return value in present or (value in percents and round(value / 100, 9) in present_rounded)

    missing = sorted(value for value in needed if not is_used(value))
    return 1 - len(missing) / len(needed), [f"{value:g}" for value in missing]


def paraphrase_agreement(main_objective: float | None, other_objectives: list[float | None]) -> float | None:
    """Share of reworded-question runs that reach the same optimum as the main run (Gap 1).

    Runs that returned no optimum are left out: a failed run is not evidence of a different answer.
    A value and its negative count as the same optimum, because a maximization written as minimizing the negative
    reports the optimum with the opposite sign (Phase 1: -1908.17 for 1908.17).
    """
    solved = [other for other in other_objectives if other is not None]
    if not solved:
        return None
    return sum(_same_up_to_sign(main_objective, other) for other in solved) / len(solved)


def _same_up_to_sign(a: float | None, b: float | None) -> bool:
    return same_optimum(a, b) or (b is not None and same_optimum(a, -b))


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
    score = combined_score(feasible, coverage, agreement)
    return VerifierReport(feasible, coverage, missing, agreement, list(other_objectives), score)


def combined_score(feasible: bool, coverage: float, agreement: float | None) -> float:
    """Mean of the available signals, and 0 when no feasible model exists. Also used to rescore saved records."""
    signals = [coverage] if agreement is None else [coverage, agreement]
    return sum(signals) / len(signals) if feasible else 0.0


def decide(report: VerifierReport, objective: float | None, threshold: float) -> Decision:
    if not report.feasible:
        return Decision("abstain", None, ["No feasible optimal model was produced after repairs."])

    reasons = []
    if report.missing_numbers:
        reasons.append("Numbers from the question not used in the model: " + ", ".join(report.missing_numbers[:10]) + ".")
    if report.paraphrase_agreement is not None and report.paraphrase_agreement < 1:
        reasons.append("Reworded versions of the question gave different optimal values.")
    failed_runs = report.paraphrase_objectives.count(None)
    if failed_runs:
        reasons.append(f"{failed_runs} reworded run(s) returned no optimum after a retry and were not counted.")
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
