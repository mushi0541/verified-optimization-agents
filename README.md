# Verified Optimization Agents

AI4015 Agentic AI, Fall 2026, semester project **G1-01**: LLM agents that translate natural-language
operations questions into optimization models, verify those models, and answer, abstain or escalate to a human.

- Base paper: OPT-Engine (Chen et al., ICML 2026), benchmark C^3-Bench.
- Architecture, gap mapping and data contracts: [docs/architecture.md](docs/architecture.md)
- Phase 1 report (submitted): [docs/phase1/Phase1_G1-01_23I-0541.pdf](docs/phase1/Phase1_G1-01_23I-0541.pdf), LaTeX source in `docs/phase1/latex/`

## What is in Phase 1

| Requirement | Where |
|---|---|
| System architecture | [docs/architecture.md](docs/architecture.md) |
| Data pipeline | `scripts/download_data.py`, `optverify/data.py` (OPT-Engine C^3-Bench, pinned commit) |
| Baseline | `optverify/systems.py` `run_baseline`: base-paper zero-shot prompt, PuLP + HiGHS, optional solver-error repair |
| Model and provider setup | `optverify/llm.py`: Amazon Bedrock (main provider), or OpenAI-compatible endpoints (Groq, OpenRouter, Google AI Studio, Ollama) |
| Tool interface | `optverify/solver_tool.py`: runs generated model code in a separate process with a time limit |
| State and contracts | `optverify/contracts.py` |
| Evaluation set and grading | 1,810 canonical + 3,760 perturbed problems; `optverify/grading.py` uses the base paper's 0.2% rule |
| End-to-end proposed workflow | `optverify/systems.py` `run_pipeline`: parser, formalizer, solver-runner, verifier, decision, explainer |
| Tests (offline, no API key) | `tests/`; run on every pull request by `.github/workflows/tests.yml`, and a pull request can merge only when they pass |

## Phase 2 progress

| Part | Gap | Where | Status |
|---|---|---|---|
| Token use per step (`parse`, `formalize`, `repair`, `paraphrase_<j>`, `sample_<i>`) | Gap 3 | `RunRecord.usage_by_step` in `optverify/contracts.py` | Done |
| Single agent B2 at an equal token budget | Gap 3 | `optverify/systems.py` `run_single_agent`, `python -m optverify.run b2` | Done; runs pending |
| E3 analysis: pipeline against B2 at k = 1, 2, 3 | Gap 3 | `scripts/analyze_e3.py` | Done; needs the k = 3 pipeline and B2 runs |
| B0 and B1 per class, and the base-paper comparison | Baselines | `scripts/compare_baselines.py`, paper values in `docs/paper_sir.json` | Done; B1 on the 100-problem sample: B0 78.0%, B1 80.0% (`results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_100_r1_20261020-1622/`) |
| E3 plots: accuracy-cost and risk-coverage curves | Gap 3 | `scripts/plot_e3.py` | Done; needs the k = 3 pipeline and B2 runs |
| Offline tests for the deterministic parts, run on every pull request | All | `tests/`, `.github/workflows/tests.yml` | Done |
| Output cap fitted to the per-minute token limit (a rejected request is sent once more) | All | `optverify/llm.py` `fitted_output_cap` | Done |
| Failed paraphrase runs retried once and left out of the agreement; number coverage ignores item labels, accepts percentages written as fractions and reads commas in code as separators between values | Gap 1 | `optverify/systems.py`, `optverify/verifier.py` | Done; checked on the 10 Phase 1 problems (see below) |
| Main provider switched to Amazon Bedrock (same model) | All | `optverify/llm.py` `BedrockLLM` | Done; all Phase 1 results rerun on Bedrock |
| Generated code runs in UTF-8 mode, so printed symbols such as `≤` no longer crash it on Windows | All | `optverify/solver_tool.py` | Done; Phase 1 Run A and pipeline rerun |
| Paraphrase agreement treats a value and its negative as the same optimum | Gap 1 | | Planned (false alarm in the Phase 1 pipeline run) |
| Fixed evaluation samples | All | samples/, scripts/make_samples.py | Done |
| OpsOR-Bench: 36 problems in three families (gate assignment, ground-crew rostering, equipment dispatch) | Gap 2 | `optverify/opsor/`, `data/opsor/opsor_bench.jsonl`, `scripts/make_opsor.py` | Done |
| Interactive interface | All | `optverify/web.py`, `optverify/static/index.html` | Done |
| Requirement coverage: the parser's requirements get IDs (R1, R2, ...), the formalizer names each constraint after its requirement, and the verifier scores the share of requirements linked to a constraint | Gap 1 | `optverify/roles.py` `number_requirements`, `optverify/prompts.py`, `optverify/solver_tool.py`, `optverify/verifier.py` `requirement_coverage` | Done; checked on the dev split (see below) |
| Calibrated threshold for a target wrong-accept rate alpha, with the leave-one-class-out test | Gap 2 | `optverify/calibration.py`, `scripts/calibrate.py`, `--calibration` in `run.py` and `web.py` | Done; runs in #36 |

## Setup

Python 3.12 is recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_data.py          # downloads ~11 MB into data/optengine/
python -m pytest -q                       # offline tests, no API key needed
```

## Models

The main model is `gpt-oss-120b`, an open-weight model, on **Amazon Bedrock**. We first used the Groq free plan, but
Groq did not let some members create an API key, and its limits (200K tokens per day, 8,000 tokens per minute) are too
small for the planned runs. Bedrock serves the same model with no daily limit at our scale. It is billed per token
(US$0.15 per million input and US$0.60 per million output tokens in us-east-1, about US$4 for all planned runs), and
each member pays from the free credits AWS gives a new account, so the project still costs us nothing.

Copy `.env.example` to `.env` and fill in one provider. Each member uses their own key. Never commit `.env`.

```
AWS_BEARER_TOKEN_BEDROCK=<your Bedrock API key>
AWS_REGION=us-east-1
```

| Variable | Meaning |
|---|---|
| `AWS_BEARER_TOKEN_BEDROCK` | Your own Bedrock API key (Bedrock console, API keys, Long-term API keys); set a budget alert in AWS Billing |
| `AWS_REGION` | The AWS region where gpt-oss-120b is available (us-east-1) |
| `AWS_PROFILE` | Instead of a key: a profile set up with the AWS CLI (`aws configure`) |

Model flag for each provider:

| Provider | Model flag | Notes |
|---|---|---|
| Amazon Bedrock (main) | `--model bedrock:openai.gpt-oss-120b-1:0` | Billed per token, covered by new-account credits |
| Groq free plan | `--model openai:openai/gpt-oss-120b` | Same model; 200K tokens per day; set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MAX_RPM=2` as in `.env.example` |
| OpenRouter free | `--model openai:google/gemma-4-31b-it:free` | 50 requests per day without credits |
| Local Ollama | `--model openai:qwen2.5:7b` | Free, slow without a GPU |

## Run

```bash
# Baseline (base paper style), 3 problems from each of the 10 classes
python -m optverify.run baseline --model bedrock:openai.gpt-oss-120b-1:0 --split canonical --per-class 3

# Same, with up to 2 repair rounds driven by solver error messages
python -m optverify.run baseline --model bedrock:openai.gpt-oss-120b-1:0 --split canonical --per-class 3 --repairs 2

# Proposed pipeline with 2 reworded runs for the verifier
python -m optverify.run pipeline --model bedrock:openai.gpt-oss-120b-1:0 --split canonical --per-class 1 --paraphrases 2 --repairs 1

# Single agent B2 (Gap 3): B1, then new samples at temperature 0.7 until the problem has used about
# --budget-tokens tokens (set it to the pipeline's mean tokens per problem at the largest k)
python -m optverify.run b2 --model bedrock:openai.gpt-oss-120b-1:0 --split canonical --per-class 10 --repairs 1 --budget-tokens 24000

# Interactive web interface (serves at http://127.0.0.1:8000)
python -m optverify.web
```

B2 answers with the most frequent optimum among its samples and uses their agreement rate as its score, in the
same answer / abstain / escalate rule as the pipeline. Each sample's tokens are saved (`usage_by_step["sample_<i>"]`),
so smaller budgets are read from the same records by keeping the first samples.

Each run writes `results/<run name>/records.jsonl` (one record per problem: code, solver status, tokens,
verifier report, decision) and `results/<run name>/summary.json` (accuracy, solved rate, tokens, latency,
accuracy per class, and for the pipeline: coverage, selective accuracy and wrong-accept rate).

### Fixed evaluation samples

The fixed problem sets are stored as ID lists in `samples/`. To run on one, pass `--sample-file`:

    python -m optverify.run baseline --model <model> --sample-file samples/canonical_100.json

`--sample-file` cannot be combined with `--per-class` or `--seed`.

To regenerate the sample files (needs the downloaded data):

    python scripts/make_samples.py

To run on the OpsOR-Bench operations research problems:

    python -m optverify.run baseline --model <model> --split opsor

To regenerate the OpsOR-Bench problem file:

    python scripts/make_opsor.py

## Calibrated threshold (Gap 2, no API calls)

Instead of the fixed threshold 0.8, the decision layer can use a threshold calibrated to a target wrong-accept rate
alpha. Thresholds are scanned from strict to lenient; only thresholds that accept at least 29 problems are tried
(fewer cannot give a bound below 10%), and the scan stops before the first threshold whose one-sided exact 95%
(Clopper-Pearson) upper bound on the wrong-accept rate exceeds alpha. If none passes, nothing is answered.

```bash
python scripts/calibrate.py --records results/<pipeline run>/records.jsonl --alpha 0.10 --out results/calibration/<name>.json
```

The file holds the leave-one-class-out test (calibrate on nine classes, test on the tenth; the pooled held-out
wrong-accept rate with its exact 95% interval, coverage and the per-fold thresholds), the same numbers for the fixed
threshold (ablation vi), and one threshold calibrated on every class. That threshold is used by:

```bash
python -m optverify.run pipeline --model <model> --sample-file <sample> --repairs 1 --calibration results/calibration/<name>.json
python -m optverify.web --calibration results/calibration/<name>.json
```

The web page then shows alpha and the calibrated threshold instead of the threshold field.

## Requirement coverage (Gap 1)

The parser's requirements are numbered R1, R2, ... and the formalizer names every constraint after the requirement it
implements (`model += x + y <= 10, "R3_capacity"`). The solver-runner reads the IDs from the constraint names of the
final model, and requirement coverage is the share of requirements linked to at least one constraint. It is added
to the score as the mean of the available signals; with no requirement list it is left out. Uncovered requirements
are given as a reason when a case is escalated.

**Development check** (development split only, `samples/dev_30.json`, gpt-oss-120b, k = 2, r = 1, threshold 0.8;
runs in `results/dev_requirement_coverage/`):

| Run | Parser failures | Correct optimum | Answered | Wrong accepted | AUROC of the score |
|---|---|---|---|---|---|
| 0: Phase 1 prompts (no requirement IDs) | 5 | 23 / 30 | 25 | 2 | 0.85 |
| 1: requirement IDs in the formalizer prompt | 1 | 23 / 30 | 23 | 1 | 0.96 |
| 2: + the parser leaves out variable types, repairs keep the names | 4 | 24 / 30 | 26 | 2 | 0.78 |
| 3: + parser output cap 12,000 tokens and one retry | 0 | 25 / 30 | 24 | 0 | 0.99 |

- Run 1 showed two causes of false misses: the parser lists variable types ("all variables are binary") as
  requirements, and a repair round dropped the constraint names.
- Run 2 showed that most parser failures are cut-off JSON: the parser lists every number, and on large instances its
  reply did not fit in 4,096 output tokens (9 of 24 repeated calls, with the old prompt too). The rest were invalid
  JSON that a second call fixes. Every parser failure removes the requirement signal; in run 2 two wrong answers
  were accepted this way.
- In run 3 requirement coverage alone has an AUROC of 0.78. It still flags some correct models, mostly when the
  parser lists a variable type or a requirement that other constraints already imply: 5 of the 25 correct models
  are below 100%, against 4 of the 5 wrong ones.

These are 30 problems with 5 to 7 wrong answers, so the numbers move a lot between runs (compare runs 1 and 2). They
were used only to fix the prompts; the signal is evaluated on the test samples in E4 (#35).

## E3 analysis (Gap 3, no API calls)

Compares the pipeline and B2 at k = 1, 2, 3 from saved records. The pipeline records must come from a run with
`--paraphrases 3`; lower k are read from them by dropping the last paraphrase runs.

```bash
python scripts/analyze_e3.py --pipeline results/<pipeline run>/records.jsonl --b2 results/<b2 run>/records.jsonl \
    --baseline results/<baseline r1 run>/records.jsonl --out results/e3
```

It reports accuracy, wrong-accept rate at 50% coverage (ties broken at random, 1,000 draws), tokens and calls per
problem, whether B2 is within 10% of the pipeline's mean tokens, McNemar tests, bootstrap 95% intervals of the paired
differences, and whether H3 holds at k = 3. Several record files per system (one per member) can be passed.
Seeds are fixed, so a rerun gives the same numbers. `--out` writes `e3.json` and `accuracy_cost.csv` (points for the
accuracy-cost curves).

The plots are drawn from the same files (PDF for the report, PNG for this README):

```bash
python scripts/plot_e3.py --curve results/e3/accuracy_cost.csv --pipeline results/<pipeline run>/records.jsonl \
    --b2 results/<b2 run>/records.jsonl --out results/e3
```

It writes `accuracy_cost.pdf/.png` (mean tokens per problem against accuracy for the pipeline and B2 at k = 1, 2, 3,
with B0 and B1 as points) and `risk_coverage_k3.pdf/.png` (wrong-accept rate against coverage at k = 3, with a dashed
line at the 50% coverage used for H3).

## B0 and B1 against the base paper (no API calls)

```bash
python scripts/compare_baselines.py --baseline results/<baseline r1 run>/records.jsonl --paper docs/paper_sir.json --markdown
```

B0 is read from the first attempt of each B1 record. Per class and overall, the script reports B0 and B1 accuracy at
the 0.2% rule and at the paper's stricter 0.1% rule (with exact 95% intervals), solved rate, silent failures (optimal
status but a wrong value), problems fixed and broken by the repair round with a McNemar test, and tokens and calls.
`--paper` is optional: a JSON file with the base paper's SIR accuracy per class, entered by hand from the paper.
Class names must match the data (`BinPacking`, `Inventory`, `JobShop`, `Knapsack`, `NetworkFlow`, `Pollution`,
`Portfolio`, `Production`, `TSP`, `Transportation`).

`docs/paper_sir.json` holds the values we use. They come from the paper's Table 2 (DeepSeek-V3.2, SIR), the only
per-class SIR numbers the paper gives in a table: TSP, Knapsack and NetworkFlow. The other seven classes are shown
only in plots, so they have no paper value. Each value is the mean of the Easy, Medium and Hard accuracy, because the
paper does not say which sizes belong to each tier. The paper grades at a 0.1% relative error, so compare it with B0
at the 0.1% rule. The model and the solver differ from ours (DeepSeek-V3.2 and Gurobi), so this column gives context;
our own B0 on the same problems is the baseline.

## Evaluation rule

A predicted objective counts as correct when `|predicted - reference| <= 0.002 * |reference|`, the same rule as the
base paper's evaluation script. The reference answer is used only for grading; it is never shown to any agent.

## Repository layout

```
optverify/
  calibration.py  Gap 2 calibrated threshold and the leave-one-class-out test
  contracts.py    shared data records
  data.py         OPT-Engine loader and per-class sampling
  interactive.py  shared interactive problem solver helper
  llm.py          provider clients with token counting; request pacing in the OpenAI-compatible client
  opsor/          OpsOR-Bench problem families and reference models
  prompts.py      prompt templates
  roles.py        parser, formalizer with repair, paraphraser, explainer
  solver_tool.py  runs generated PuLP code with HiGHS
  static/         interactive interface template (index.html)
  verifier.py     verifier signals and the answer / abstain / escalate decision
  systems.py      baseline (B0/B1), single agent B2 and proposed pipeline
  grading.py      correctness rule and run summaries
  run.py          command line entry point
  web.py          interactive web interface entry point
data/opsor/       generated OpsOR-Bench problem file
samples/          fixed evaluation sample ID files (canonical, ablation, linguistic, constraint pairs)
scripts/download_data.py     pinned data download
scripts/make_opsor.py        regenerates the OpsOR-Bench file with fixed seeds
scripts/make_samples.py      regenerates the sample files with seed 0
scripts/analyze_e3.py        E3 equal-budget analysis from saved records
scripts/calibrate.py         Gap 2 calibration and leave-one-class-out test from saved records
scripts/compare_baselines.py B0 and B1 per class and the base-paper comparison
scripts/plot_e3.py           E3 accuracy-cost and risk-coverage plots
tests/
docs/architecture.md
docs/paper_sir.json  base-paper SIR accuracy per class, for compare_baselines.py
docs/phase1/      submitted Phase 1 report (PDF and LaTeX source)
results/          saved runs
```

## Data splits

| Split | File | Size | Use |
|---|---|---|---|
| Development | samples/dev_30.json | 30 canonical problems, 3 per class, seed 1 | Prompt changes and design choices only. Never reported as results. |
| Canonical test | samples/canonical_100.json | 100 canonical problems, 10 per class, seed 0 | Reported results only |
| Ablation | samples/ablation_30.json | 30 problems, a subset of the canonical test sample | Reported ablations only |
| Linguistic | samples/linguistic_30.json | 30 problems, 10 each for Inventory, Knapsack and TSP | Reported E1 results only |
| Constraint pairs | samples/constraint_pairs_30.json | 30 original and augmented pairs | Reported E1 results only |
| OpsOR-Bench | data/opsor/opsor_bench.jsonl | 36 problems, three families | Reported E2 shift test only |

Gap 2 calibration is leave-one-class-out inside the canonical test sample, so each problem is scored only in the fold that holds out its class.

## Team

| Name | Roll Number | Role |
|---|---|---|
| Mushahid Hussain | 23I-0541 | Group head |
| Muhammad Waqas | 23I-0569 | Member |
| Abdul Rauf | 23I-0591 | Member |

Supervisor: Muhammad Sajjad (Group G1)

## Initial Results

All Phase 1 results use `gpt-oss-120b` on Amazon Bedrock at temperature 0 (report Section 3).

**Baseline (B0: zero-shot, no repair) on the canonical split.**
- **Run A**, 3 problems from each of the 10 classes: 66.7% accuracy, 96.7% solved rate
  (`results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_r0_20261020-1634/`).
- **Run B**, 1 problem from each class: 80.0% accuracy, 100.0% solved rate
  (`results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_r0_20261020-1340/`).

| Class | Run A (n=3) | Run B (n=1) |
|---|---|---|
| BinPacking | 100% | 100% |
| Inventory | 0% | 0% |
| JobShop | 66.7% | 100% |
| Knapsack | 66.7% | 100% |
| NetworkFlow | 100% | 100% |
| Pollution | 0% | 0% |
| Portfolio | 66.7% | 100% |
| Production | 100% | 100% |
| TSP | 66.7% | 100% |
| Transportation | 100% | 100% |

Inventory and Pollution Control failed in all four attempts, which points to systematic formulation problems (or
reference answers to check). With 3 problems per class, one problem moves a class result by 33 points, so very small
samples are noisy. 11 of the 39 runs that reached an optimal solver status returned a wrong value with no warning. These
silent failures motivate the verifier and calibrated abstention.

Run A and the pipeline run below were repeated after the solver-runner fix: on Windows, model code that printed a symbol
such as `≤` stopped with an encoding error and was counted as a code error.

### First end-to-end run of the proposed pipeline

Same model, the same 10 problems as Run B, `--paraphrases 2 --repairs 1`, fixed Phase 1 threshold 0.8
(`results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_r1_20261020-1634/`).

| Measure | Value |
|---|---|
| Problems completed | 10 of 10 |
| Answered / escalated / abstained | 7 / 3 / 0 |
| Selective accuracy | 100% (7 of 7 answers correct) |
| Wrong-accept rate | 0% (0 of 7) |
| Accuracy of the final model, before the decision | 80% (8 of 10) |
| Mean tokens per problem | 7,847 input + 10,649 output, 6.2 LLM calls |
| Cost of the whole run | about US$0.08 |

**What happened.**
- Both wrong models (Inventory, Pollution Control) were escalated because their rewordings reached different optima.
  On the same problems, B0 returned both wrong values with no warning.
- 1 of the 20 reworded runs (TSP) first returned no optimum, and the retry recovered it. Without the retry, the correct
  TSP answer would have been escalated.
- The one false alarm is Production: the model was correct, but one rewording returned the same value with the opposite
  sign (-1908.17 instead of 1908.17), as happens when a maximization is written as minimizing the negative. Phase 2
  will treat a value and its negative as the same optimum.
- Number coverage ignores item labels and reads commas in code as separators between values (an earlier run read
  `(3,14,100.2)` as one number), so all ten problems reached full coverage.

This run shows that the parts work together on 10 problems; it is not an evaluation.

## Notes

- The OPT-Engine repository has no licence file, so its data is downloaded at a pinned commit instead of being stored here.
- The solver-runner executes code written by an LLM. It runs in a separate process with a minimal environment and a
  time limit, but it is not a security sandbox. Run it only on your own machine.
