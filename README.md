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
| Model and provider setup | `optverify/llm.py`: free OpenAI-compatible endpoints (Groq, OpenRouter, Google AI Studio, Ollama) or Bedrock |
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
| B0 and B1 per class, and the base-paper comparison | Baselines | `scripts/compare_baselines.py`, paper values in `docs/paper_sir.json` | Done; needs the B1 runs |
| E3 plots: accuracy-cost and risk-coverage curves | Gap 3 | `scripts/plot_e3.py` | Assigned (issue #9) |
| Offline tests for the deterministic parts, run on every pull request | All | `tests/`, `.github/workflows/tests.yml` | Done |
| Output cap fitted to the per-minute token limit (a rejected request is sent once more) | All | `optverify/llm.py` `fitted_output_cap` | Done |
| Failed paraphrase runs retried once and left out of the agreement; number coverage ignores item labels and accepts percentages written as fractions | Gap 1 | `optverify/systems.py`, `optverify/verifier.py` | Done; checked on the 10 Phase 1 problems (see below) |
| Fixed evaluation samples, OpsOR-Bench, interactive interface | All | | Planned (Phase 2 schedule, report Table 8) |
| Requirement coverage, calibrated threshold | Gaps 1 and 2 | | Planned (Phase 2 schedule, report Table 8) |

## Setup

Python 3.12 is recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_data.py          # downloads ~11 MB into data/optengine/
python -m pytest -q                       # offline tests, no API key needed
```

## Models (free tiers)

Copy `.env.example` to `.env` and fill in one provider. The default is the Groq free plan (no card needed).
Each member uses their own key. Never commit `.env`.

```
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=<your Groq API key>
LLM_MAX_RPM=2
```

| Variable | Meaning |
|---|---|
| `LLM_BASE_URL` | Address of the OpenAI-compatible endpoint (Groq above) |
| `LLM_API_KEY` | Your own API key from https://console.groq.com/keys |
| `LLM_MAX_RPM` | Most requests per minute; requests are spaced out so free-tier limits are respected |

Model flag for each provider:

| Provider | Model flag | Notes |
|---|---|---|
| Groq free plan | `--model openai:openai/gpt-oss-120b` | 1,000 requests and 200K tokens per day |
| OpenRouter free | `--model openai:google/gemma-4-31b-it:free` | 50 requests per day without credits |
| Local Ollama | `--model openai:qwen2.5:7b` | Free, slow without a GPU |

## Run

```bash
# Baseline (base paper style), 3 problems from each of the 10 classes
python -m optverify.run baseline --model openai:openai/gpt-oss-120b --split canonical --per-class 3

# Same, with up to 2 repair rounds driven by solver error messages
python -m optverify.run baseline --model openai:openai/gpt-oss-120b --split canonical --per-class 3 --repairs 2

# Proposed pipeline with 2 reworded runs for the verifier
python -m optverify.run pipeline --model openai:openai/gpt-oss-120b --split canonical --per-class 1 --paraphrases 2 --repairs 1

# Single agent B2 (Gap 3): B1, then new samples at temperature 0.7 until the problem has used about
# --budget-tokens tokens (set it to the pipeline's mean tokens per problem at the largest k)
python -m optverify.run b2 --model openai:openai/gpt-oss-120b --split canonical --per-class 10 --repairs 1 --budget-tokens 17000
```

B2 answers with the most frequent optimum among its samples and uses their agreement rate as its score, in the
same answer / abstain / escalate rule as the pipeline. Each sample's tokens are saved (`usage_by_step["sample_<i>"]`),
so smaller budgets are read from the same records by keeping the first samples.

Each run writes `results/<run name>/records.jsonl` (one record per problem: code, solver status, tokens,
verifier report, decision) and `results/<run name>/summary.json` (accuracy, solved rate, tokens, latency,
accuracy per class, and for the pipeline: coverage, selective accuracy and wrong-accept rate).

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
  contracts.py    shared data records
  data.py         OPT-Engine loader and per-class sampling
  llm.py          provider clients with token counting; request pacing in the OpenAI-compatible client
  prompts.py      prompt templates
  roles.py        parser, formalizer with repair, paraphraser, explainer
  solver_tool.py  runs generated PuLP code with HiGHS
  verifier.py     verifier signals and the answer / abstain / escalate decision
  systems.py      baseline (B0/B1), single agent B2 and proposed pipeline
  grading.py      correctness rule and run summaries
  run.py          command line entry point
scripts/download_data.py     pinned data download
scripts/analyze_e3.py        E3 equal-budget analysis from saved records
scripts/compare_baselines.py B0 and B1 per class and the base-paper comparison
scripts/plot_e3.py           E3 accuracy-cost and risk-coverage plots
tests/
docs/architecture.md
docs/paper_sir.json  base-paper SIR accuracy per class, for compare_baselines.py
docs/phase1/      submitted Phase 1 report (PDF and LaTeX source)
results/          saved runs
```

## Team

| Name | Roll Number | Role |
|---|---|---|
| Mushahid Hussain | 23I-0541 | Group head |
| Muhammad Waqas | 23I-0569 | Member |
| Abdul Rauf | 23I-0591 | Member |

Supervisor: Muhammad Sajjad (Group G1)

## Initial Results

Baseline (zero-shot, no repair rounds) on OPT-Engine canonical split using Groq `openai/gpt-oss-120b`.

**Run A** (6 classes, 3 problems each): 61.1% accuracy, 83.3% solved rate.

**Run B** (all 10 classes, 1 problem each): 80.0% accuracy, 90.0% solved rate.

| Class | Run A (n=3) | Run B (n=1) |
|---|---|---|
| BinPacking | 100% | 0% |
| Inventory | 0% | 100% |
| JobShop | 66.7% | 100% |
| Knapsack | 100% | 100% |
| NetworkFlow | 100% | 100% |
| Pollution | 0% | 0% |
| Portfolio | not run | 100% |
| Production | not run | 100% |
| TSP | not run | 100% |
| Transportation | not run | 100% |

Pollution Control scores 0% in both runs, which points to a systematic formulation problem (or reference answers to check).
The same Bin Packing problem was solved in Run A but failed with a code error in Run B, even at temperature 0, and the
two Inventory results come from different problems, so very small samples are noisy. These patterns motivate the proposed
five-role pipeline with number coverage, paraphrase agreement and calibrated abstention.

### First end-to-end run of the proposed pipeline

Same model, one canonical problem per class, `--paraphrases 2 --repairs 1`, fixed Phase 1 threshold 0.8
(`results/pipeline_openai-openai-gpt-oss-120b_canonical_r1_20261017-1424/`).

| Measure | Value |
|---|---|
| Problems completed | 8 of 10 (TSP and Transportation were rejected by the API: one request above the free plan's 8,000 tokens-per-minute limit) |
| Answered / escalated / abstained | 4 / 2 / 2 |
| Selective accuracy | 100% (4 of 4 answers correct) |
| Wrong-accept rate | 0% (0 of 4) |
| Mean tokens per problem | 6,117 input + 7,209 output, 5.4 LLM calls |

Both wrong models (Inventory, Pollution Control) were refused. Both escalations were false alarms caused by paraphrase
runs that returned no optimum; Phase 2 will retry such runs and score them separately from a true disagreement.

### Re-run after the first Phase 2 fixes

**What changed in the code.** Four fixes from the Phase 1 observations:
- requests above the per-minute limit now get an output cap fitted to that limit and are retried once;
- a failed paraphrase run is retried once, and a run that still fails is not counted as a disagreement;
- number coverage ignores item labels such as "Package 3";
- a percentage written as a fraction (24% as 0.24) counts as used.

**The run.** The same 10 problems and settings (`results/pipeline_openai-openai-gpt-oss-120b_canonical_r1_20261020-1109/`).

| Measure | Value |
|---|---|
| Problems completed | 10 of 10 |
| Answered / escalated / abstained | 7 / 3 / 0 |
| Selective accuracy | 100% (7 of 7 answers correct) |
| Wrong-accept rate | 0% (0 of 7) |
| Accuracy of the final model, before the decision | 80% (8 of 10) |
| Mean tokens per problem | 8,251 input + 10,796 output, 7.1 LLM calls |

**What happened.**
- TSP and Transportation now complete, and both answers are correct.
- Both wrong models (Inventory, Pollution Control) were escalated because their reworded runs disagreed.
- There was one false alarm: in Production, both reworded runs agreed on an optimum different from the correct main model.

These 10 problems are the ones that revealed the issues, so this run checks the fixes; it is not an evaluation. Token use
is higher than in Phase 1 because the two largest problems now complete.

## Notes

- The OPT-Engine repository has no licence file, so its data is downloaded at a pinned commit instead of being stored here.
- The solver-runner executes code written by an LLM. It runs in a separate process with a minimal environment and a
  time limit, but it is not a security sandbox. Run it only on your own machine.
