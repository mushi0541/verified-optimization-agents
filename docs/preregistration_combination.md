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
