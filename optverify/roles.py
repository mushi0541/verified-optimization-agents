"""Agent roles: parser, formalizer (with solver-feedback repair), paraphraser and explainer.

Each role takes plain inputs, calls the LLM at most a few times, and adds its token use to the shared counter.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from . import prompts
from .contracts import Attempt, Decision, TokenUsage, VerifierReport
from .llm import LLM
from .solver_tool import extract_code, run_model_code

if TYPE_CHECKING:
    from .trace import TraceWriter


def parse_problem(
    question: str,
    llm: LLM,
    usage: TokenUsage,
    trace: TraceWriter | None = None,
) -> dict | None:
    prompt = prompts.PARSE.format(question=question)
    reply = llm.complete(prompt)
    usage.add(reply.usage)
    if trace is not None:
        trace.record("parser", prompt, reply.text, reply.usage, reply.latency_s)
    return _first_json_object(reply.text)


def formalize_and_solve(
    first_prompt: str,
    question: str,
    llm: LLM,
    usage: TokenUsage,
    max_repairs: int,
    repair_usage: TokenUsage | None = None,
    trace: TraceWriter | None = None,
) -> list[Attempt]:
    """Write model code, run it, and repair it from solver/runtime errors only (never from the reference answer).

    Repair calls are counted in repair_usage when it is given, otherwise in usage."""
    attempts = []
    prompt = first_prompt
    for round_number in range(max_repairs + 1):
        reply = llm.complete(prompt)
        (usage if round_number == 0 or repair_usage is None else repair_usage).add(reply.usage)
        role = "formalizer" if round_number == 0 else "repair"
        if trace is not None:
            trace.record(role, prompt, reply.text, reply.usage, reply.latency_s)
        code = extract_code(reply.text)
        result = run_model_code(code)
        attempts.append(Attempt(code=code or "", solve=result))
        if trace is not None:
            trace.record(
                "solver",
                code or "",
                {"status": result.status, "objective": result.objective, "error": result.error},
                tokens=None,
                latency_s=result.runtime_s,
            )
        if result.status == "optimal":
            break
        problem_text = result.error or f"The solver finished with status '{result.status}'."
        prompt = prompts.REPAIR.format(question=question, code=code or "(no code returned)", error=problem_text)
    return attempts


def paraphrase(
    question: str,
    llm: LLM,
    usage: TokenUsage,
    trace: TraceWriter | None = None,
    role: str = "paraphraser",
) -> str:
    prompt = prompts.PARAPHRASE.format(question=question)
    reply = llm.complete(prompt)
    usage.add(reply.usage)
    if trace is not None:
        trace.record(role, prompt, reply.text, reply.usage, reply.latency_s)
    return reply.text.strip()


def explain(
    decision: Decision,
    report: VerifierReport,
    variables: dict[str, float] | None = None,
) -> str:
    """Plain-language note for the operations user. Deterministic, so it costs no tokens."""
    if decision.action == "answer":
        opening = f"Recommended plan found. Optimal objective value: {decision.answer:g}."
    elif decision.action == "escalate":
        opening = "A plan was found, but the checks did not pass. Please have an analyst review it before use."
    else:
        opening = "The system could not build a working model, so it is not giving an answer."
    checks = f"Checks: number coverage {report.number_coverage:.0%}"
    if report.paraphrase_agreement is not None:
        checks += f", reworded-question agreement {report.paraphrase_agreement:.0%}"
    summary = " ".join([opening, checks + ".", *decision.reasons])
    if decision.action != "answer" or not variables:
        return summary
    lines = [summary]
    for name, value in sorted(variables.items()):
        lines.append(f"{name}: {value:g}")
    return "\n".join(lines)


def _first_json_object(text: str) -> dict | None:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
