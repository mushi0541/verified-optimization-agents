# Verified Optimization Agents

AI4015 Agentic AI, Fall 2026, semester project **G1-01**: LLM agents that translate natural-language
operations questions into optimization models, verify those models, and answer, abstain or escalate to a human.

- Base paper: OPT-Engine (Chen et al., ICML 2026), benchmark C^3-Bench.
- Architecture, gap mapping and data contracts: [docs/architecture.md](docs/architecture.md)
- Development log (failures, fixes and their measured effect): [docs/devlog.md](docs/devlog.md)
- Phase 1 report (submitted): [docs/phase1/Phase1_G1-01_23I-0541.pdf](docs/phase1/Phase1_G1-01_23I-0541.pdf), LaTeX source in `docs/phase1/latex/`
- Phase 2 paper (IEEE two-column, 10 pages): `docs/paper/main.tex` and `docs/paper/refs.bib`. Build it from `docs/paper` with
  `pdflatex main && bibtex main && pdflatex main && pdflatex main`. Its tables are written to `docs/paper/tables/` by
  `scripts/make_paper_tables.py`, and its figures are read from `results/gap2/` and `results/gap3/`, all from saved runs.

## Gap resolution

A hand copy of the paper's Table "Gap resolution" (`docs/paper/tables/gap_resolution.tex`, written by
`scripts/make_paper_tables.py`); after a rebuild, check it against that file. Main model gpt-oss-120b; "pre-registered
runs" are the tests on new problems and six more models (#103, #104). The base paper, OPT-Engine, has no check, no
abstention and no token report, so its column says what it does. "Addressed?" says whether our component met its
hypothesis, that is, whether it improved on the base paper: Gap 3's question is answered, but the answer is no.

| Gap | Method / component | Metric | Base paper result | Our result | Addressed? |
|---|---|---|---|---|---|
| 1. Label-free verification | Verifier: number, requirement and paraphrase signals (`optverify/verifier.py`) | AUROC for correct against wrong answers (H1: gain of at least 0.10) | No check; solver feasibility alone gives 0.54 | 0.87; H1 partly met in 6 of 7 pre-registered runs | Partially |
| 2. Error control under shift | Decision gate with a threshold calibrated to a target wrong-accept rate (`optverify/calibration.py`) | Held-out WAR at most 10% with half the problems answered (H2) | Always answers | Met in 0 of 3 samples; the smallest alpha the data can meet is 12% to 21% | Not |
| 3. Cost | Token meter per step; single agent B2 at an equal budget (`optverify/systems.py`) | WAR minus B2's at 50% coverage (H3) | Tokens not reported | [-5.0, +4.3] points on 200 problems; met in 0 of 9 pre-registered runs | Not |
| 3. Cost (H3c) | Pipeline at k = 1 with B2's votes (`scripts/explore_combination.py`) | The same | Not applicable | Met in 0 of 9 pre-registered runs | Not |

In short: the signals do detect wrong models (Gap 1), but the calibrated error bound does not hold on unseen problem
classes (Gap 2), and at an equal token budget majority voting is at least as good as the pipeline (Gap 3). Details are
in the paper and in the "Outcomes" paragraph of [Phase 2 progress](#phase-2-progress).

## Architecture

```mermaid
flowchart LR
    Q[/"Operations question<br/>(C^3-Bench or OpsOR-Bench)"/]

    subgraph BASE["Baselines"]
        BF["Formalizer<br/>one LLM call writes PuLP code<br/>(B0: no repair, B1: one repair)"] --> BS["Solver-runner tool<br/>PuLP + HiGHS in a separate process"]
        BS -- "B1: status or error text" --> BF
        BS --> B2["B2: more B1 samples at temperature 0.7<br/>until the token budget is used;<br/>majority answer, agreement as score"]
    end

    subgraph PROP["Proposed pipeline (E3: k = 3, r = 1)"]
        P1["Parser<br/>JSON spec with requirements R1, R2, ..."] --> P2["Formalizer<br/>PuLP code, one named constraint<br/>per requirement"]
        P2 --> P3["Solver-runner tool<br/>repair on any non-optimal status"]
        P3 -- "optimal" --> PR["Paraphraser<br/>k reworded questions"]
        PR --> P2b["Baseline prompt + solver<br/>on each rewording"]
        P3 --> P4["Verifier (Gap 1)<br/>number coverage<br/>requirement coverage<br/>paraphrase agreement"]
        P2b --> P4
        P4 --> D{"Decision layer (Gap 2)<br/>score = mean of the signals<br/>fixed threshold 0.8, or calibrated<br/>to a target wrong-accept rate"}
        D -- "no feasible model" --> A["Abstain"]
        D -- "score >= threshold" --> ANS["Answer + explanation"]
        D -- "score < threshold" --> H["Escalate to a human<br/>with the reasons"]
    end

    Q --> BF
    Q --> P1
    T["Token meter on every LLM call<br/>(equal budget for B2, Gap 3)"] -.-> BASE
    T -.-> PROP
    ANS --> G["Grader: |pred - ref| <= 0.2% |ref|"]
    BS --> G
    B2 --> G
```

The roles, the data contracts and the mapping of each gap to its code are in [docs/architecture.md](docs/architecture.md).

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

## Changes since Phase 1

The base paper and the three gaps are unchanged. Each design change since the Phase 1 report, why it was made, and
where. Measured effects are in the [development log](docs/devlog.md).

| Change | Why | Pull requests |
|---|---|---|
| Main provider moved from the Groq free plan to Amazon Bedrock, with the same model (gpt-oss-120b); all Phase 1 results rerun on Bedrock | Groq's limits (200K tokens a day, 8,000 a minute) were far too small for the planned runs, and some members could not get a key | #10, #14, #16 |
| Number coverage ignores item labels ("Package 3"), accepts percentages written as fractions, and reads commas in code as separators | False alarms on correct models in the Phase 1 pipeline run | #10, #12, #14 |
| A failed reworded run is retried once and left out of the agreement instead of counting as a disagreement | A failed run is not evidence of a different answer; it escalated correct answers | #10 |
| Generated code runs in UTF-8 mode | On Windows, code that printed symbols such as `≤` crashed and counted as a modelling error | #19 |
| Paraphrase agreement treats a value and its negative as the same optimum; the paraphraser runs at temperature 0.7 as the report states | A correct answer was escalated because a rewording minimized the negative; rewordings at temperature 0 are near copies | #49 |
| Token use is saved per step, and B2 is charged only for the samples behind its answer | Needed to compare the pipeline with a single agent at an equal token budget (Gap 3) | #2, #3 |
| Fixed sample files, and a separate development split that shares no problem with any test sample | The Phase 2 brief forbids tuning on the test set | #17, #52 |
| Test samples grow to 20 problems per class (`canonical_200`, `linguistic_60`, `constraint_pairs_60`) and the ablation sample to 5 per class (`ablation_50`), each starting with the Phase 1 sample | Supervisor feedback: 10 per class gives wide intervals, especially per held-out class in Gap 2 | #58 |
| A larger canonical sample (`canonical_587`, 60 per class) for Gap 2, and a larger development split (`dev_93`). **A deviation from the Phase 1 plan:** the size was chosen after H2 failed on `canonical_200`, and the `canonical_200` result is always reported beside it | A power analysis on E3 repeat 1 (`scripts/power_h2.py`): certifying a 10% wrong-accept rate needs 154 to 593 accepted calibration answers per fold, against about 150 with `canonical_200` | #78 |
| Requirement coverage, the third Gap 1 signal, is measured by linking each parser requirement (R1, R2, ...) to named constraints; the parser gets a larger output cap and one retry | Planned in Phase 1; on the dev split the parser's JSON was cut off on large instances, which removed the signal | #60 |
| The fixed 0.8 threshold is replaced by a threshold calibrated to a target wrong-accept rate, tested leave-one-class-out; B2 is calibrated on its own agreement rate, and a calibration is used only for the configuration it was made from | Gap 2 as planned; the scores of different systems and settings are not comparable | #57, #61 |
| Each Gap 1 signal and the parser can be switched off, and ablations are read from saved records | The Phase 2 brief requires switchable gap components; rescoring avoids paying for repeated runs | #61 |
| An optional second model writes the rewordings (`--paraphrase-model`) | Supervisor feedback: the paraphraser and the formalizer share a model, so their errors can be correlated | #62 |
| B0 and B1 are reported over repeats, grouped by model, next to the base paper's reported values, so B0 can also be reproduced with the paper's own model (DeepSeek-V3.2, runs in #33) | Supervisor feedback: compare properly with the base paper | #50 |
| A run can be resumed after failed problems (`--resume`) | A network outage during an E3 run failed most problems; rerunning everything would pay twice | #64, #66 |
| A development log records each failure, fix and measured effect | The Phase 2 brief asks for it, and the paper's failure analysis uses it | #48 |

Supervisor feedback on Phase 1 and where each point is handled: issue #23.

## Phase 2 progress

| Part | Gap | Where | Status |
|---|---|---|---|
| Token use per step (`parse`, `formalize`, `repair`, `paraphrase_<j>`, `sample_<i>`) | Gap 3 | `RunRecord.usage_by_step` in `optverify/contracts.py` | Done |
| Single agent B2 at an equal token budget | Gap 3 | `optverify/systems.py` `run_single_agent`, `python -m optverify.run b2` | Done; runs in `results/b2_*` (#98, #104) |
| E3 analysis: pipeline against B2 at k = 1, 2, 3 | Gap 3 | `scripts/analyze_e3.py` | Done; `results/gap3/canonical_200/` (#98) and `results/preregistered/h3/` (#104) |
| B0 and B1 per class, and the base-paper comparison | Baselines | `scripts/compare_baselines.py`, paper values in `docs/paper_sir.json` | Done; `results/e1_e2/` on `canonical_200`, with B0 for gpt-oss-120b and DeepSeek-V3.2 (#90) |
| E3 plots: accuracy-cost and risk-coverage curves | Gap 3 | `scripts/plot_e3.py` | Done; the Gap 3 figures are in the paper (#115) |
| Offline tests for the deterministic parts, run on every pull request | All | `tests/`, `.github/workflows/tests.yml` | Done |
| Output cap fitted to the per-minute token limit (a rejected request is sent once more) | All | `optverify/llm.py` `fitted_output_cap` | Done |
| Failed paraphrase runs retried once and left out of the agreement; number coverage ignores item labels, accepts percentages written as fractions and reads commas in code as separators between values | Gap 1 | `optverify/systems.py`, `optverify/verifier.py` | Done; checked on the 10 Phase 1 problems (see below) |
| Main provider switched to Amazon Bedrock (same model) | All | `optverify/llm.py` `BedrockLLM` | Done; all Phase 1 results rerun on Bedrock |
| Generated code runs in UTF-8 mode, so printed symbols such as `≤` no longer crash it on Windows | All | `optverify/solver_tool.py` | Done; Phase 1 Run A and pipeline rerun |
| Paraphrase agreement treats a value and its negative as the same optimum; the paraphraser samples at temperature 0.7 (`--paraphrase-temperature`) | Gap 1 | `optverify/verifier.py` `paraphrase_agreement`, `optverify/systems.py` `run_pipeline` | Done; removes the Production false alarm of the Phase 1 pipeline run (development log entry 8) |
| Second model for the paraphraser (`--paraphrase-model`, supervisor feedback), so its mistakes are less correlated with the formalizer's | Gap 1 | `optverify/run.py` `paraphrase_client` | Done; run with `bedrock:deepseek.v3.2` on `dev_93` and `canonical_200` (development log entry 9, #56) |
| Fixed evaluation samples | All | samples/, scripts/make_samples.py | Done |
| OpsOR-Bench: 36 problems in three families (gate assignment, ground-crew rostering, equipment dispatch) | Gap 2 | `optverify/opsor/`, `data/opsor/opsor_bench.jsonl`, `scripts/make_opsor.py` | Done |
| Interactive interface | All | `optverify/web.py`, `optverify/static/index.html` | Done |
| Requirement coverage: the parser's requirements get IDs (R1, R2, ...), the formalizer names each constraint after its requirement, and the verifier scores the share of requirements linked to a constraint | Gap 1 | `optverify/roles.py` `number_requirements`, `optverify/prompts.py`, `optverify/solver_tool.py`, `optverify/verifier.py` `requirement_coverage` | Done; checked on the dev split (see below) |
| Switches for each signal and the parser, and rescoring of saved records for ablations (i) to (vii) | Gap 1 | `--signals`, `--no-parser` in `run.py`; `optverify/rescore.py`, `scripts/rescore.py` | Done |
| E4 Gap 1 analysis: AUROC of each signal and of the combined score, bootstrap intervals, the H1 verdict | Gap 1 | `scripts/analyze_gap1.py` | Done; `results/gap1/` (#93) |
| Calibrated threshold for a target wrong-accept rate alpha, with the leave-one-class-out test | Gap 2 | `optverify/calibration.py`, `scripts/calibrate.py`, `--calibration` in `run.py` and `web.py` | Done; `results/gap2/` (#36) |
| E4 Gap 2 analysis over the repeats: alphas, fixed threshold, B0, 10 against 20 per class, risk-coverage curve, the H2 verdict | Gap 2 | `scripts/analyze_gap2.py` | Done; `results/gap2/` (#93) |
| Comparison of two paraphrase models: AUROC, false alarms, and the misreadings each one catches on problems with the same answer | Gap 1 | `scripts/compare_paraphrasers.py`, `results/paraphraser/` | Done on `dev_93` and `canonical_200`: no gain overall, the default stays the main model (devlog 9, #56) |
| E3 on `canonical_587` (60 per class) with Gap 1 and Gap 2, including Gap 2 without Pollution as the sensitivity analysis. The sample was enlarged after H2 failed on `canonical_200`, a deviation from the Phase 1 plan (devlog 13) | Gap 1, Gap 2 | `results/pipeline_..._canonical_587_r1_20261101-2254/`, `results/gap1/canonical_587/`, `results/gap2/canonical_587*/` | Done; see devlog 13 |
| Ablations (i) to (vii) on `ablation_50`, with the two new runs (iv) and r = 2 | Gap 1 | `scripts/ablation_table.py`, `results/ablations/ablations.csv` | Done (#100, devlog 17) |
| Gap 2 exploratory: the wrong-accept floor of the score per class, and other threshold rules | Gap 2 | `scripts/score_floor.py`, `scripts/threshold_rules.py`, `results/gap2/score_floor/`, `results/gap2/threshold_rules/` | Done (#99, devlog 16); exploratory, not the H2 result |
| Prompt versions v2 and v3, designed on development problems only | All | `--prompt-version` in `run.py`, `results/prompts_v2/` | Done (#97, devlog 18): no gain, v1 stays the default |
| Pre-registered tests: the pipeline combined with B2, all 1,070 unused canonical problems, six more models | Gaps 1 to 3 | `docs/preregistration_combination.md`, `results/preregistered/` | Done (#103, #104, devlog 20 and 21) |
| E6: efficiency and reliability per model and system | All | `scripts/efficiency.py`, `results/e6/` | Done (#112) |
| Paper tables generated from `results/` | All | `scripts/make_paper_tables.py`, `docs/paper/tables/` | Done (#94, #96, #102, #112, #113) |

**Outcomes** (devlog 15, 20 and 21, `docs/paper/tables/preregistered.tex`): H1 is partly supported for every model
except gpt-oss-20b (its gain is 0.075, below 0.10). H2, H3 and H3c are not supported in the main analysis. In the
sensitivity analysis (without Pollution and the one `reference_wrong` problem) only one verdict changes: H3 for
GLM 4.7.

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
(US$0.15 per million input and US$0.60 per million output tokens in us-east-1), and each member pays from the free
credits AWS gives a new account, so the project still costs us nothing. The measured cost of every system and model
is in `results/e6/` (see E6 below).

Phase 2 also ran the main systems with six more Bedrock models, so the results are not tied to one model (#103):
`bedrock:deepseek.v3.2` (the base paper's model), `bedrock:qwen.qwen3-next-80b-a3b`,
`bedrock:mistral.mistral-large-3-675b-instruct`, `bedrock:moonshotai.kimi-k2.5`, `bedrock:zai.glm-4.7` and
`bedrock:openai.gpt-oss-20b-1:0`.

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

# Same, with a second model writing the rewordings (each rewording is still solved by --model)
python -m optverify.run pipeline --model bedrock:openai.gpt-oss-120b-1:0 --paraphrase-model bedrock:deepseek.v3.2 --split canonical --per-class 1 --paraphrases 2 --repairs 1

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

    python -m optverify.run baseline --model <model> --sample-file samples/canonical_200.json

`--sample-file` also reads constraint pair files (it runs both problems of every pair). It cannot be combined with `--per-class` or `--seed`.

### Continuing a run after failures

A problem whose LLM calls fail (for example during a network outage) is listed under `failed_problems` in the run's
`summary.json` and left out of `records.jsonl`. To run only those problems again and add them to the same run, repeat
the command with `--resume` and the run's folder:

    python -m optverify.run pipeline --model <model> --sample-file samples/canonical_200.json --repairs 1 --paraphrases 3 \
        --resume results/<run folder>

All settings must be the same as in the first command (only `--workers` and `--env-file` may change); otherwise the
run is refused. `summary.json` is then rewritten over all records, and its `resumes` field counts how often the run
was continued.

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

B2 is calibrated the same way on its own records, with its sample agreement rate as the score
(`scripts/calibrate.py --records results/<b2 run>/records.jsonl`). The file records the configuration it was made
from: the system name (for example `pipeline_p3` or `b2_r1`), the enabled signals and the parser switch. `run.py`
refuses a file made for another configuration, because the scores differ (B2's agreement rate is not a verifier
score, and k or a switched-off signal changes the verifier score). `web.py` accepts only a pipeline file.

### Gap 2 analysis over the repeats (E4, H2)

```bash
python scripts/analyze_gap2.py --records results/<pipeline repeat 1>/records.jsonl results/<repeat 2>/records.jsonl \
    --baseline results/<B1 run>/records.jsonl --subset samples/canonical_100.json --out results/gap2/canonical_200
```

For each repeat and each alpha (5%, 10% and 20% by default) it runs the leave-one-class-out test above and the fixed
0.8 threshold (ablation vi), with B0 as the reference (it never abstains). `--subset samples/canonical_100.json`
repeats the test on the first 10 problems per class, which shows how much 20 per class narrows the interval. H2 is
supported when, at alpha = 10%, the pooled held-out wrong-accept rate is at most alpha and at least 50% of the
problems are answered in every repeat; the exact upper bound is reported next to it. The output folder gets
`gap2.json`, `gap2.md` and the risk-coverage curve (`risk_coverage.csv`, `.pdf`, `.png`).

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

## Ablations

Each Gap 1 part can be switched off in a run:

```bash
python -m optverify.run pipeline --model <model> --sample-file <sample> --repairs 1 --signals number,paraphrase  # no requirement coverage
python -m optverify.run pipeline --model <model> --sample-file samples/ablation_50.json --repairs 1 --no-parser  # ablation iv
```

`--signals` takes any of `number`, `requirement`, `paraphrase` (or `none` for feasibility alone); without
`paraphrase` the paraphrase runs are skipped. Every record still stores every signal that was computed, so most
ablations need no new run. `scripts/rescore.py` reads them from the main records, takes off the tokens of the steps
it drops, and makes no API calls:

| Ablation | Command (add `--records results/<pipeline run>/records.jsonl`) |
|---|---|
| (i) without number coverage | `python scripts/rescore.py --signals requirement,paraphrase` |
| (ii) without requirement coverage | `python scripts/rescore.py --signals number,paraphrase` |
| (iii) without paraphrase agreement | `python scripts/rescore.py --signals number,requirement` |
| (iv) without the parser | new run with `--no-parser` (above) |
| (v) k = 1, 2, 3 paraphrases | `python scripts/rescore.py --k 1` (any k up to the run's k) |
| (vi) fixed against calibrated threshold | `python scripts/rescore.py --threshold 0.8` and `python scripts/rescore.py --alpha 0.10` |
| (vii) r = 0, 1, 2 repairs | r = 0: `python scripts/rescore.py --no-repair`; r = 1: the main run; r = 2: new run with `--repairs 2` |

The options combine (for example `--signals number,paraphrase --k 2 --alpha 0.10`), `--calibration <file>` applies
the threshold of a calibration file, and `--out <file>` saves the JSON. The output gives the accuracy of the final
model, mean tokens and calls, and the decision: answered, wrong accepted, coverage and the wrong-accept rate with
its exact 95% interval (per fold and pooled with `--alpha`). `--no-repair` is exact: a first attempt that is optimal
never ran a repair, and one that is not means the pipeline abstains.

## Gap 1 analysis: do the signals detect wrong models? (E4, H1, no API calls)

```bash
python scripts/analyze_gap1.py --records results/<pipeline repeat 1>/records.jsonl results/<repeat 2>/records.jsonl \
    --baseline results/<B1 run>/records.jsonl --out results/gap1/canonical_200
```

For each repeat it gives the AUROC for separating correct from wrong final answers of feasibility alone, of each
signal alone, of the combined score and of the combined score without each signal (the same scores as ablations i to
iii), with paired bootstrap 95% intervals and the mean and standard deviation over the repeats. At the decision
threshold (`--threshold`, or `--calibration <file>`) it reports coverage, precision and recall of the accepted
answers, and with `--baseline` the B0 numbers on the same problems. Constraint-pair and linguistic runs are also split
into original and augmented problems and into easy, moderate and hard wording.

H1 counts as supported in a repeat when the combined AUROC is at least 0.10 above feasibility alone with the interval
of the gain above 0, and removing any one signal lowers the AUROC (each interval of the drop above 0). The verdict is
"supported" only if this holds in every repeat, and "partly supported" if only the gain holds.


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

For the course E1 and E2 tables, pass each repeat with its own `--repeat`: the B1 repeats with gpt-oss-120b, and the
B0-only repeats with DeepSeek-V3.2, the base paper's own model:

```bash
python scripts/compare_baselines.py --repeat results/<B1 repeat 1>/records.jsonl --repeat results/<B1 repeat 2>/records.jsonl \
    --repeat results/<B1 repeat 3>/records.jsonl --repeat results/<DeepSeek B0 repeat 1>/records.jsonl ... \
    --paper docs/paper_sir.json --out-dir results/e1_e2
```

This writes `e1_e2.md`, `e1_e2.csv` and `e1_e2.json`. Repeats are grouped by the model in their records, and each
model gets one block labelled "reproduced (<model>, our runs)". Each block gives B0 and B1 accuracy at both rules,
silent failures, and the problems fixed and broken by the repair round, as the mean and sample standard deviation
(n - 1) over its repeats; the deviation needs 2 or more repeats. A block of B0-only runs leaves the B1 and repair cells
empty. The last column is the SIR accuracy "reported in OPT-Engine (DeepSeek-V3.2, Table 2)": one number from the
paper, with no standard deviation. Repeats of one model must cover the same problems with the same settings (the
script names a few differing problem IDs otherwise), and the JSON keeps every repeat in full so each mean can be
traced back to its runs.

`docs/paper_sir.json` holds the values we use. They come from the paper's Table 2 (DeepSeek-V3.2, SIR), the only
per-class SIR numbers the paper gives in a table: TSP, Knapsack and NetworkFlow. The other seven classes are shown
only in plots, so they have no paper value. Each value is the mean of the Easy, Medium and Hard accuracy, because the
paper does not say which sizes belong to each tier. The paper grades at a 0.1% relative error, so compare it with B0
at the 0.1% rule. The model and the solver differ from ours (DeepSeek-V3.2 and Gurobi), so this column gives context;
our own B0 on the same problems is the baseline.

## E6: efficiency and reliability (no API calls)

```bash
python scripts/efficiency.py --out-dir results/e6
```

Reads every run in `results/` (or only the folders given with `--runs`). Runs with the same system, model, endpoint
and problem set are treated as repeats, so each number is the mean and sample standard deviation over the repeats:
input and output tokens, LLM calls, solver calls, latency and cost per problem, the failed-run rate (target under 5%,
report objective D1), solver error and timeout rates, and the repair success rate. A repeat without a measure (such
as the repair success rate when nothing needed repair) is left out of that mean, and the output says how many repeats
had a value. Cost uses the price of each run's model from the `PRICES` table in the script, with the date the price
was read (Bedrock list prices, us-east-1; `gpt-oss-20b` has no listed price there). A model without a price gets an
empty cost cell. When a record splits its tokens by model (a
second paraphrase model), each model is priced on its own. Runs with a second paraphraser or other verifier switches
are never averaged with the main runs. Tokens and cost cover finished problems only, because no
usage is saved for a failed problem, so the cost is a lower bound when runs fail. It writes `efficiency.csv`,
`tokens_by_step.csv` (where each system spends its tokens, from `usage_by_step`) and `efficiency.json`.

The two folders in `results/e6` were made with these commands (the `canonical_200` one leaves out the v3-prompt and
second-paraphraser runs and the two B1 repeats run in ap-southeast-2, since E6 keeps one endpoint per row, and adds the
`canonical_200` part of the `canonical_587` run as a pipeline repeat):

```bash
python scripts/efficiency.py --sample samples/canonical_200.json --out-dir results/e6/canonical_200 \
    --runs $(ls -d results/*canonical_200_r* | grep -v -e prompts-v3 -e para-bedrock -e _20261105-1852 -e _20261105-1907) \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254
python scripts/efficiency.py --out-dir results/e6/canonical_unused --runs results/baseline_*canonical_unused_r1* \
    results/pipeline_*canonical_unused_r1* results/b2_*canonical_unused_r1*
```

## Evaluation rule

A predicted objective counts as correct when `|predicted - reference| <= 0.002 * |reference|`, the same rule as the
base paper's evaluation script. The reference answer is used only for grading; it is never shown to any agent.

## Reproduce the experiments

`experiments/run.py` runs one experiment from its config in `experiments/configs/`:

```bash
# every repeat of an experiment
python experiments/run.py E1

# one repeat (0-based), or another sample
python experiments/run.py E3 --repeat 0
python experiments/run.py E3 --sample-file samples/constraint_pairs_60.json
```

Each repeat goes to `results/<exp>/<model-slug>/repeat_<n>/` with `config.json`, `records.jsonl` and `summary.json`.
A failed problem stays in `records.jsonl` with `"failed": true`, and `summary.json` gives `failed_rate` over the whole
sample. Analysis-only configs (E4, E5, E6) refuse to run and say what to run instead. The reported runs were
started directly with `python -m optverify.run` and are saved in flat folders such as
`results/pipeline_<model>_<sample>_r1_<time>/` (see "Where each saved result comes from").

```bash
python experiments/aggregate.py E1
```

This writes `results/<exp>/<model-slug>/summary.json` and `summary.csv` (mean and sample standard deviation over the
repeats) and updates `results/manifest.json`.

| Course | Our experiment | Config | What it runs |
|---|---|---|---|
| E1 | Baseline B1 | `E1.json` | Single pass with one repair on `canonical_200` |
| E2 | Base paper B0 | `E2.json` | No repair, with gpt-oss-120b and DeepSeek-V3.2; the paper's reported numbers are labelled |
| E3 | Proposed pipeline (k = 3, r = 1) | `E3.json` | `canonical_200`, plus the shift samples with `--sample-file`; threshold 0.8 or a calibration file |
| G3 | B2 at the pipeline's budget (Gap 3) | `G3.json` | Needs `budget` (E3 mean tokens per problem) or `--budget-tokens` |
| E4 | Gap-wise tests (H1, H2, H3) | `E4.json` | Analysis of E1 to E3 and OpsOR-Bench |
| E5 | Ablations (i) to (vii) | `E5.json`, `E5-NOPARSER.json`, `E5-R2.json` | Most ablations rescore E3 records (`scripts/rescore.py`); (iv) and r = 2 are new runs |
| E6 | Efficiency and reliability | `E6.json` | Metrics from E1 to E3 records |

### Where each saved result comes from

The reported runs were made with `python -m optverify.run` (the settings of each run are in its `summary.json`
`config`), so each analysis reads those run folders. Every analysis below runs offline, with no API key.

| Course | Runs (in `results/`) | Analysis | Output |
|---|---|---|---|
| E1, E2 | `baseline_..._canonical_200_r1_...` (B1, gpt-oss-120b; B0 is its first attempts), `baseline_bedrock-deepseek.v3.2_canonical_200_r0_...` (B0, DeepSeek-V3.2) | `scripts/compare_baselines.py` | `results/e1_e2/` |
| E3 | `pipeline_..._canonical_200_r1_20261101-1429`, `..._20261102-0153`, and the `canonical_200` part of `pipeline_..._canonical_587_r1_20261101-2254` (three repeats) | read by the E4 and E5 scripts | |
| E4 Gap 1 | the three E3 repeats, with `--sample samples/canonical_200.json`; also `canonical_587`, `constraint_pairs_60`, `linguistic_60` | `scripts/analyze_gap1.py` | `results/gap1/<sample>/` |
| E4 Gap 2 | the same repeats; `--exclude-classes Pollution` for the sensitivity analysis; `--shift` with the OpsOR-Bench run | `scripts/analyze_gap2.py` | `results/gap2/<sample>/` |
| E4 Gap 3 | E3 repeat 1, `b2_..._canonical_200_r1_...` and the B1 run | `scripts/analyze_e3.py` | `results/gap3/canonical_200/` |
| E5 | the three E3 repeats with `--sample-file samples/ablation_50.json`, plus `pipeline_..._ablation_50_r1_20261102-1000` (iv, run with `--no-parser` before the `_noparser` tag of #101) and `pipeline_..._ablation_50_r2_20261102-1001` (r = 2) | `scripts/ablation_table.py` | `results/ablations/` |
| E6 | the main runs of every model on `canonical_200`, with `--sample samples/canonical_200.json`; the three `canonical_unused` runs | `scripts/efficiency.py` | `results/e6/<sample>/` |
| Pre-registered | the runs on `canonical_587_rest_387`, `canonical_unused` and the six other models (#103) | `scripts/analyze_gap1.py`, `analyze_gap2.py`, `analyze_e3.py`, `explore_combination.py` | `results/preregistered/` |

The paper's tables are then written from these outputs with `python scripts/make_paper_tables.py`.

## Observability

Pass `--trace` to write per-step JSON lines to `logs/<run_name>/<problem_id>.jsonl`. Each line records one step with the following keys:
- `time`: UTC ISO 8601 timestamp.
- `role`: One of `parser`, `formalizer`, `repair`, `solver`, `paraphrase_<j>`, `verifier`, `decision`, `explainer`.
- `input`: The prompt text or step inputs.
- `output`: The model reply text, solver status and objective, or decision summary.
- `tokens`: Token counts (`input_tokens`, `output_tokens`, `calls`).
- `latency_s`: Step duration in seconds.

Sensitive environment variable values and keys are automatically redacted.

Trajectories and failure analysis (#41):

```bash
# Print summary table of trace runs
python scripts/format_trajectories.py --traces "logs/sample/*.jsonl" --summary

# Render markdown report with step trajectories, signal breakdowns, and root causes
python scripts/format_trajectories.py --traces "logs/sample/*.jsonl" --cases canonical-1155 canonical-1250 canonical-1601 canonical-0890 --causes --out docs/failures/trajectories.md
```

See `docs/failures/trajectories.md` for full case study trajectories (two successes and two failures) and detailed root cause mitigations for each failure category.

## Repository layout

```
experiments/
  configs/        experiment definitions (E1 to E6, G3 and the E5 ablation runs)
  prompt_version.py prompt template SHA-256 and git commit hash
  run.py          experiment runner with repeats
  aggregate.py    summary statistics aggregator and manifest updater
optverify/
  calibration.py  Gap 2 calibrated threshold and the leave-one-class-out test
  contracts.py    shared data records
  data.py         OPT-Engine loader and per-class sampling
  interactive.py  shared interactive problem solver helper
  llm.py          provider clients with token counting; request pacing in the OpenAI-compatible client
  opsor/          OpsOR-Bench problem families and reference models
  prompts.py      prompt templates
  rescore.py      a saved pipeline record under a smaller configuration (signals, k, no repair)
  roles.py        parser, formalizer with repair, paraphraser, explainer
  solver_tool.py  runs generated PuLP code with HiGHS
  static/         interactive interface template (index.html)
  trace.py        per-step trace writer with secret redaction
  verifier.py     verifier signals and the answer / abstain / escalate decision
  systems.py      baseline (B0/B1), single agent B2 and proposed pipeline
  grading.py      correctness rule and run summaries
  run.py          command line entry point
  web.py          interactive web interface entry point
data/opsor/       generated OpsOR-Bench problem file
logs/sample/      sample trace files for answered and escalated cases
samples/          fixed evaluation sample ID files (canonical, ablation, linguistic, constraint pairs)
scripts/download_data.py     pinned data download
scripts/make_opsor.py        regenerates the OpsOR-Bench file with fixed seeds
scripts/make_samples.py      regenerates the sample files with seed 0
scripts/analyze_e3.py        E3 equal-budget analysis from saved records
scripts/calibrate.py         Gap 2 calibration and leave-one-class-out test from saved records
scripts/analyze_gap2.py      E4 Gap 2 over the repeats: alphas, fixed threshold, B0, risk-coverage curve, H2 verdict
scripts/rescore.py           ablations (i) to (vii) from saved records, no API calls
scripts/analyze_gap1.py      E4 Gap 1: AUROC of each signal and of the combined score, and the H1 verdict
scripts/compare_paraphrasers.py  two paraphrase models compared on saved runs (#56)
scripts/compare_baselines.py B0 and B1 per class and the base-paper comparison
scripts/plot_e3.py           E3 accuracy-cost and risk-coverage plots
scripts/efficiency.py        E6 efficiency and reliability from saved runs
scripts/ablation_table.py    E5 ablation table from saved records and the two ablation runs
scripts/compare_runs.py      two pipeline runs on the same problems, per class, paired (prompt versions, #97)
scripts/explore_combination.py  the pipeline combined with B2 (exploratory, then the pre-registered H3c test)
scripts/failure_analysis.py  failure analysis labels and frequency tables (#41)
scripts/format_trajectories.py  step trajectories from trace logs (#41)
scripts/power_h2.py          Gap 2 power analysis: accepted answers needed to certify a wrong-accept rate
scripts/score_floor.py       Gap 2 exploratory: wrong answers at the top score, per class
scripts/threshold_rules.py   Gap 2 exploratory: other threshold rules under leave-one-class-out
scripts/tsp_parser_rules.py  the parser's subtour rule for every TSP problem (devlog 14)
scripts/check_references.py  checks the Pollution and Inventory reference answers (#40)
scripts/check_refs.py        checks the paper's BibTeX references and citations (#43)
scripts/make_paper_tables.py writes the paper's tables (docs/paper/tables/) from results/
tests/
docs/architecture.md
docs/devlog.md    development log: each failure, the fix and its measured effect
docs/paper_sir.json  base-paper SIR accuracy per class, for compare_baselines.py
docs/phase1/      submitted Phase 1 report (PDF and LaTeX source)
docs/paper/       Phase 2 paper (IEEEtran LaTeX source and references)
results/          saved runs
results/manifest.json completed experiment runs and config hashes
```

How the course's suggested folders map to ours:

| Suggested folder | Ours |
|---|---|
| `src/` | `optverify/` (the package: agents, tools, verifier, decision layer, CLI and web interface) |
| `data/` | `data/` (downloaded by `scripts/download_data.py`, not committed, except `data/opsor/`) and `samples/` (fixed problem IDs) |
| `experiments/` | `experiments/` (configs and the repeat runner) and `scripts/` (analysis from saved runs, no API calls) |
| `results/` | `results/` (one folder per run, and one per analysis) |
| `docs/` | `docs/` (architecture, development log, Phase 1 report, Phase 2 paper) |
| `tests/` | `tests/` (offline, run on every pull request) |
| `logs/` | `logs/` (trace files written with `--trace`; only `logs/sample/` is committed) |

## Data splits

| Split | File | Size | Use |
|---|---|---|---|
| Development | samples/dev_30.json | 30 canonical problems, 3 per class, seed 1 | Prompt changes and design choices only. Never reported as results. |
| Development, larger | samples/dev_93.json | dev_30 plus 7 per class (no NetworkFlow problem is left) | Signal design only. Never reported as results. |
| Canonical test | samples/canonical_200.json | 200 canonical problems, 20 per class | Reported results only |
| Canonical test, larger | samples/canonical_587.json | canonical_200 plus up to 40 per class (60 per class; NetworkFlow 47) | Gap 2 (H2) with enough calibration data, reported next to canonical_200 |
| Ablation | samples/ablation_50.json | 50 problems, 5 per class, a subset of canonical_100 | Reported ablations only |
| Linguistic | samples/linguistic_60.json | 60 problems, 20 each for Inventory, Knapsack and TSP | Reported E1 results only |
| Constraint pairs | samples/constraint_pairs_60.json | 60 original and augmented pairs, 20 per class | Reported E1 results only |
| OpsOR-Bench | data/opsor/opsor_bench.jsonl | 36 problems, three families | Reported E2 shift test only |
| TSP diagnostic | samples/tsp_60.json | the 60 TSP problems of canonical_587 | The run without the parser (devlog 14); a diagnostic, not a new result |
| Development, prompt versions | samples/dev_tsp_inventory_60.json | 30 TSP and 30 Inventory problems in no other sample, seed 2 | Prompt versions v2 and v3 only (#97). Never reported as results. |
| Held out, rest of canonical_587 | samples/canonical_587_rest_387.json | the 387 problems of canonical_587 not in canonical_200 | Pre-registered H3c test (#103) |
| Held out, every unused problem | samples/canonical_unused.json | the 1,070 canonical problems in no other sample | Pre-registered H1, H2, H3 and H3c tests (#103, Addendum 1) |

Phase 2 uses 20 problems per class (supervisor feedback on Phase 1). Each larger file starts with the Phase 1 file of the same split (`canonical_100`, `ablation_30`, `linguistic_30`, `constraint_pairs_30`) and adds new problems drawn from the rest of the split with seed 0, so Phase 1 runs stay valid as the first part of each larger sample. The Phase 1 files are kept unchanged. New constraint pairs never reuse a problem of an earlier pair. The dev sample shares no problem with any test sample; it was regenerated for Phase 2 because 5 of its old problems are now in canonical_200. Regenerate every file with `python scripts/make_samples.py`; `tests/test_samples.py` checks that the result matches the checked-in files.

Gap 2 calibration is leave-one-class-out inside the canonical test sample, so each problem is scored only in the fold that holds out its class.

## Team

| Name | Roll Number | Role |
|---|---|---|
| Mushahid Hussain | 23I-0541 | Group head |
| Muhammad Waqas | 23I-0569 | Member |
| Abdul Rauf | 23I-0591 | Member |

Supervisor: Muhammad Sajjad (Group G1)

## Phase 1 results

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
  treats a value and its negative as the same optimum, and rescoring this run turns that escalation into an answer.
- Number coverage ignores item labels and reads commas in code as separators between values (an earlier run read
  `(3,14,100.2)` as one number), so all ten problems reached full coverage.

This run shows that the parts work together on 10 problems; it is not an evaluation.

## Notes

- The OPT-Engine repository has no licence file, so its data is downloaded at a pinned commit instead of being stored here.
- The solver-runner executes code written by an LLM. It runs in a separate process with a minimal environment and a
  time limit, but it is not a security sandbox. Run it only on your own machine.
