# Verified Optimization Agents

AI4015 Agentic AI, Fall 2026, semester project **G1-01**: LLM agents that translate natural-language
operations questions into optimization models, verify those models, and answer, abstain or escalate to a human.

- Base paper: OPT-Engine (Chen et al., ICML 2026), benchmark C^3-Bench.
- Architecture, gap mapping and data contracts: [docs/architecture.md](docs/architecture.md)

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
`LLM_MAX_RPM` spaces out requests so free-tier limits are respected.

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
```

Each run writes `results/<run name>/records.jsonl` (one record per problem: code, solver status, tokens,
verifier report, decision) and `results/<run name>/summary.json` (accuracy, solved rate, tokens, latency,
accuracy per class, and for the pipeline: coverage, selective accuracy and wrong-accept rate).

## Evaluation rule

A predicted objective counts as correct when `|predicted - reference| <= 0.002 * |reference|`, the same rule as the
base paper's evaluation script. The reference answer is used only for grading; it is never shown to any agent.

## Repository layout

```
optverify/
  contracts.py    shared data records
  data.py         OPT-Engine loader and per-class sampling
  llm.py          provider clients with token counting and rate limiting
  prompts.py      prompt templates
  roles.py        parser, formalizer with repair, paraphraser, explainer
  solver_tool.py  runs generated PuLP code with HiGHS
  verifier.py     verifier signals and the answer / abstain / escalate decision
  systems.py      baseline and proposed pipeline
  grading.py      correctness rule and run summaries
  run.py          command line entry point
scripts/download_data.py
tests/
docs/architecture.md
results/          saved runs
```

## Team

| Name | Roll Number | Role |
|---|---|---|
| Mushahid Hussain | i230541 | Group head |
| (add teammate) | | |
| (add teammate) | | |

Supervisor: Muhammad Sajjad (Group G1)

## Initial Results

Results will appear here after running the baseline with a free-tier model.
To produce them:

1. Get a free Groq API key at https://console.groq.com/keys
2. Copy `.env.example` to `.env` and paste the key
3. Run: `python -m optverify.run baseline --model openai:openai/gpt-oss-120b --split canonical --per-class 3`
4. Commit the `results/` folder

## Notes

- The OPT-Engine repository has no licence file, so its data is downloaded at a pinned commit instead of being stored here.
- The solver-runner executes code written by an LLM. It runs in a separate process with a minimal environment and a
  time limit, but it is not a security sandbox. Run it only on your own machine.
