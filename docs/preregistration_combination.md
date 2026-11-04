# Pre-registration: the pipeline combined with B2, on problems not used to design it

Written on 2026-11-02, before any B2 sample on these problems exists. The commit that adds this file, and the issue
that links it, are the time stamps.

## Why

H3 was not supported on `canonical_200` (devlog 15): at an equal token budget the pipeline's wrong-accept rate is
not lower than B2's. An exploratory analysis on the same 200 problems (`scripts/explore_combination.py`,
`results/exploratory/combination/`) found that spending part of the budget on the pipeline and the rest on B2 samples
gives a lower wrong-accept rate than either alone at low coverage, but with intervals that include zero. That analysis
looked at the data, so it is only a lead. This file fixes the test before new data is collected.

## Data

`samples/canonical_587_rest_387.json`: the 387 problems of `canonical_587` that are not in `canonical_200`. The
pipeline already ran on them (`results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254`,
v1 prompts, k = 3, r = 1). No design choice, prompt or threshold was chosen by looking at the combination on them.

New run: B2 on these 387 problems, gpt-oss-120b on Bedrock, r = 1, sample temperature 0.7, budget 26,000 tokens and
at most 24 samples (more than the budget below, so the analysis can hold B2 to the budget, as in E3).

## The combined system (fixed)

- Budget: the pipeline's mean tokens per problem at k = 3 on the 387 problems.
- The pipeline with its first paraphrase run only (k = 1, as `optverify/rescore.py` rescores it), plus B2's first samples whose
  tokens are closest to the rest of the budget (the budget minus the pipeline's mean tokens at k = 1).
- Answer: the pipeline's answer (none when it has no feasible model).
- Score: the mean of the pipeline's score and the share of those B2 samples that reach the same optimum (verifier
  tolerance).

## Hypotheses and tests (fixed)

- **H3c (primary):** on the 387 problems, the combined system has a lower wrong-accept rate than B2 held to the same
  budget, when each answers the top 50% of problems by score. Supported only if the upper end of the paired bootstrap
  95% interval of the difference (combined minus B2; 1,000 resamples of problems, seed as in the script) is below 0.
- **H3 on 587 (secondary):** the E3 test of devlog 15 (pipeline k = 3 against B2, `scripts/analyze_e3.py`, same
  rule), on all 587 problems.
- **Reported in any case, not tests:** the same differences at 70, 80 and 90% coverage; without Pollution; against
  the pipeline at k = 3; AUROC; accuracy (McNemar). Every number is reported, whichever way it goes.

## What would change the plan

Nothing in this file changes after the B2 run starts. A failed or stopped B2 problem is resumed with `--resume`. If
some problems still fail, they are left out and listed, and the test runs on the rest.

## Addendum 1: every unused canonical problem (written before any run on them)

`samples/canonical_unused.json`: the 1,070 canonical problems in no other sample, test or development (BinPacking
550, Knapsack 190, JobShop 90, Portfolio 90, Inventory 60, TSP 60, Pollution 10, Production 10, Transportation 10;
NetworkFlow has none left). No run of any system has seen them.

New runs, gpt-oss-120b, the #34 settings and v1 prompts: the pipeline (k = 3, r = 1), B1 (r = 1), and B2 (r = 1,
budget 26,000 tokens, at most 24 samples).

Tests, with the same rules as above and as on `canonical_587`:
- **H3c** and **H3** exactly as above, on the 1,070 problems, and on all 1,457 held-out problems (the 387 and the
  1,070 together).
- **H1** (`scripts/analyze_gap1.py`) and **H2** (`scripts/analyze_gap2.py`, leave-one-class-out, alpha 10%), with the
  same settings as on `canonical_587`.

Reported in any case, not tests: per class, and with every class weighted equally, because BinPacking is half of
this sample.

## Addendum 2: more models (written before any full run with them)

The model list is fixed here, after a 2-problem smoke test on development problems (`canonical-0139`,
`canonical-0637`) that only checked that each model runs the pipeline end to end. All on Bedrock us-east-1:
`deepseek.v3.2`, `qwen.qwen3-next-80b-a3b`, `mistral.mistral-large-3-675b-instruct`, `moonshotai.kimi-k2.5`,
`zai.glm-4.7`, and `openai.gpt-oss-20b-1:0` (a smaller model of the main family).

For each model, on `canonical_200`, with the #34 settings and v1 prompts: the pipeline (k = 3, r = 1), B1 (r = 1),
and then B2 (r = 1, at most 24 samples, budget 1.25 times that model's pipeline mean tokens, so the analysis can hold
B2 to the pipeline's budget as in E3). The same model is used for every step, including the paraphraser.

Tests per model, with the rules above: **H1** (`analyze_gap1.py`), **H3** (`analyze_e3.py`) and **H3c**
(`explore_combination.py`, the k = 1 combination against B2 at 50% coverage). For gpt-oss-120b, `canonical_200` was
used to explore the combination, so H3c there is not a test; for the other models it is new data. Reported in any
case: every model's numbers, including a model on which nothing works.

## Addendum 3: problems with doubtful references (written before the hand-check labels of #40 exist)

Rauf is hand-checking the Inventory and Pollution references (#40). Each checked problem gets one label:
`reference_correct`, `reference_wrong` or `text_ambiguous`. The rule, fixed now:
- **Main analysis:** every problem, as above.
- **Sensitivity analysis:** without every Pollution problem (#79) and without every problem labelled
  `reference_wrong`. The same tests and rules are applied, and both sets of results are reported.
- **`text_ambiguous`:** kept in both analyses, and also reported on its own.
- **The paper lists every excluded problem by ID,** with the reason.
