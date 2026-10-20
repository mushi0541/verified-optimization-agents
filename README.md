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
| Tests (offline, no API key) | `tests/` |

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
tests/
docs/architecture.md
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

## Notes

- The OPT-Engine repository has no licence file, so its data is downloaded at a pinned commit instead of being stored here.
- The solver-runner executes code written by an LLM. It runs in a separate process with a minimal environment and a
  time limit, but it is not a security sandbox. Run it only on your own machine.
