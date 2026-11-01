"""Shared data contracts.

Every stage of the baseline and of the proposed pipeline reads and writes these
records, so each run can be saved as JSON and compared later.
"""

from dataclasses import asdict, dataclass, field


@dataclass
class Problem:
    problem_id: str
    question: str
    answer: float | None  # reference optimum from the benchmark
    problem_class: str
    size: int
    split: str
    meta: dict = field(default_factory=dict)


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0

    def add(self, other: "TokenUsage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.calls += other.calls

    @staticmethod
    def total(steps: dict[str, "TokenUsage"]) -> "TokenUsage":
        """Sum of the token use of several steps."""
        total = TokenUsage()
        for usage in steps.values():
            total.add(usage)
        return total


@dataclass
class LLMReply:
    text: str
    usage: TokenUsage
    latency_s: float


@dataclass
class SolveResult:
    # status is one of: optimal, infeasible, unbounded, not_solved, error, timeout, no_code
    status: str
    objective: float | None
    stdout: str = ""
    error: str = ""
    runtime_s: float = 0.0
    variables: dict[str, float] = field(default_factory=dict)
    # Requirement IDs (R1, R2, ...) found in the constraint names of the model, sorted (Gap 1, requirement coverage).
    requirement_ids: list[str] = field(default_factory=list)


@dataclass
class Attempt:
    """One formalize-then-solve round (the first try or a repair)."""

    code: str
    solve: SolveResult


@dataclass
class VerifierReport:
    feasible: bool
    number_coverage: float  # share of the question's numbers that appear in the model code
    missing_numbers: list[str]
    paraphrase_agreement: float | None  # share of reworded runs that reach the same optimum
    paraphrase_objectives: list[float | None]
    score: float
    # Share of the parser's requirements linked to a named constraint; None when the parser listed no requirements
    # (and in records saved before Phase 2).
    requirement_coverage: float | None = None
    missing_requirements: list[str] = field(default_factory=list)


@dataclass
class Decision:
    action: str  # answer, abstain or escalate
    answer: float | None
    reasons: list[str]


@dataclass
class RunRecord:
    problem_id: str
    problem_class: str
    size: int
    system: str
    model: str
    reference: float | None
    predicted: float | None
    correct: bool
    attempts: list[Attempt]
    usage: TokenUsage
    latency_s: float
    spec: dict | None = None
    verifier: VerifierReport | None = None
    decision: Decision | None = None
    explanation: str = ""
    # Token use of each step (parse, formalize, repair, paraphrase_1 ... paraphrase_k); the steps add up to usage.
    # Empty in records saved before Phase 2.
    usage_by_step: dict[str, TokenUsage] = field(default_factory=dict)
    # Single agent B2 only. samples[i] holds the attempts of sample i + 1 (its tokens are usage_by_step["sample_<i + 1>"]);
    # samples[0] is the B1 run at temperature 0 and is also stored in attempts.
    samples: list[list[Attempt]] = field(default_factory=list)
    token_budget: float | None = None  # tokens per problem the samples were drawn up to
    sample_agreement: float | None = None  # B2's score: share of the used samples that reach its answer
    samples_used: int | None = None  # B2's answer and usage come from samples[:samples_used] only
    # Token use per model, filled only when a second model wrote the rewordings (--paraphrase-model), so each model's
    # tokens can be priced on their own; the models add up to usage. Empty when one model made every call.
    usage_by_model: dict[str, TokenUsage] = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)
