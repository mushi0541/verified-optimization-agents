# Development log

One entry per major iteration: the date, the failure we saw, the change we made and its measured effect.
Dates are merge dates from `git log`, or commit dates for work done before the first pull request. The paper's
failure analysis uses this log.

Add an entry for each fix that answers a failure, newest last, and link it in the pull request description.

| # | Date | Area | Pull request |
|---|---|---|---|
| 1 | 2026-10-17 to 2026-10-20 | Provider limits: pacing, fitted output cap, switch to Bedrock | #10, #14 |
| 2 | 2026-10-20 | Number coverage: item labels and commas in code | #10, #12, #14 |
| 3 | 2026-10-20 | Failed paraphrase runs counted as disagreement | #10 |
| 4 | 2026-10-20 | B2 charged for samples it did not use | #3 |
| 5 | 2026-10-20 | Windows encoding crash in the solver child | #19 |
| 6 | 2026-10-20 | OpsOR-Bench wording ambiguities | #20 |
| 7 | 2026-10-20 | `VAR:` lines filled the stored solver output | #21 |
| 8 | 2026-10-26 | Rewordings with the opposite sign; paraphraser temperature | #28 (issue) |
| 9 | 2026-11-01 | Paraphraser and formalizer use the same model (supervisor feedback) | #56 (issue) |
| 10 | 2026-11-01 | Requirement coverage: cut-off parser output, variable types, lost constraint names | #60 |
| 11 | 2026-11-01 | B2 records crashed the calibration; calibration used for another configuration | #57, #61 |
| 12 | 2026-11-01 | Network outage during an E3 run | #64, #66 |
| 13 | 2026-11-02 | Too little calibration data to certify alpha = 10% | #78 |

## 1. Provider limits: request pacing, fitted output cap, then Amazon Bedrock

**Date.** 2026-10-17 (request pacing, in the first commits), 2026-10-20 (output cap, #10; Bedrock, #14).

**Failure.** The Groq free plan allows 8,000 tokens per minute and 200,000 per day. Groq counts the prompt plus
`max_tokens` against the per-minute limit. In the first pipeline run (Phase 1, 10 problems), two requests were
rejected with error 413 (9,259 and 8,291 tokens requested), so TSP and Transportation did not complete. Later, some
members could not create a Groq key at all: the key page failed its Cloudflare check.

**Change.**
- `LLM_MAX_RPM` spaces out requests (`optverify/llm.py`, Phase 1).
- A request rejected with 413 is sent once more with an output cap fitted to the limit stated in the error
  (`fitted_output_cap`, #10).
- Amazon Bedrock became the main provider for every role and baseline, with the same `gpt-oss-120b` weights (#14).
  Each run's config now records the endpoint that served it (#16), so runs on different providers are not mixed.

**Effect.** The rerun of the same 10 problems completed 10 of 10 (8 of 10 before). On Bedrock there is no daily
token limit at our scale. After the supervisor's feedback (20 problems per class, a DeepSeek-V3.2 reproduction and
a second paraphrase model), the whole Phase 2 plan is about 45 million tokens, about US$20 (tracker #47).

## 2. Number coverage: item labels and commas in model code

**Date.** 2026-10-20 (#10, #12, #14).

**Failure.** Number coverage checks that every number in the question appears in the model code. It produced false
alarms in two ways:
- item labels such as "Package 3" or "Office 2" were counted as data, although the code names items by index;
- code such as `(3,14,100.2)` was read as `3` and `14,100.2` (a thousands separator), so 14 and 100.2 looked unused.

**Change.**
- A capitalized word followed by integers counts as a label only when the integers form an unbroken run such as
  1, 2, 3 (#10, tightened in #12). The first rule, "two different integers", would also have hidden real data in
  wording like "Each 30 minutes ... Each 45 minutes", which is the unsafe direction for a verifier.
- In code, a comma always separates values; code may group digits with underscores (#14).
- A percentage also counts as used when the code writes it as a fraction, 24% as 0.24 (#10).

**Effect.** Rescoring the saved Bedrock pipeline run raised TSP's coverage from 0.67 to 1.00 and changed no
decision. On all 5,570 downloaded questions, every word the first label rule treated as a label is still a label
under the run rule, so no question's coverage changed (#12).

## 3. Failed paraphrase runs counted as disagreement

**Date.** 2026-10-20 (#10).

**Failure.** A reworded run that returned no optimum (a code error or an infeasible model) counted as a
disagreement with the main answer. In the first pipeline run, both escalations were such false alarms.

**Change.** A failed reworded run is retried once, inside the same `paraphrase_<j>` step so its tokens stay with
that run. A run that still fails is left out of the agreement, and the decision states how many were left out. If no
run succeeds, the score uses the other signals.

**Effect.** Rescoring the saved pipeline runs: counting failed runs as disagreement escalates 3 correct answers
(NetworkFlow and Portfolio in the first Phase 1 run, Portfolio in the rerun); with the leave-out rule all three are
answered, and the one wrong model with a failed run (Inventory) is still escalated. In the Bedrock pipeline run, 1 of
the 20 reworded runs (TSP) first returned no optimum and the retry recovered it.

## 4. B2 charged for samples it did not use

**Date.** 2026-10-20 (#3, review fix).

**Failure.** B2 draws samples until the problem's tokens reach the budget, then answers with the first samples whose
tokens are closest to the budget. Its `usage`, and so the token means in `summary.json`, still counted every sample
drawn, including the ones after those used. The equal-budget comparison (Gap 3, objective D3) needs the cost of the
samples behind the answer.

**Change.** Records save `samples_used`, and `usage` totals only those samples. Every drawn sample stays in
`samples` and `usage_by_step`.

**Effect.** No B2 run existed yet, so no saved result changed. The change was requested in the review of #3
(https://github.com/mushi0541/verified-optimization-agents/pull/3#pullrequestreview-5584445963). A test covers a
budget where 3 samples are drawn and 2 are used.

## 5. Windows encoding crash in the solver child

**Date.** 2026-10-20 (#19).

**Failure.** On Windows the solver's child process wrote its output with the cp1252 code page. When model code
printed a symbol such as `≤`, `≥` or a non-breaking hyphen, Python stopped with `UnicodeEncodeError`, and correct
code was recorded as status `error`. The same code runs fine on Linux.

**Change.** The child runs in UTF-8 mode (`python -I -X utf8`), and its output is read as UTF-8. The isolation
(`-I`, minimal environment, time limit) is unchanged.

**Effect.**
- Phase 1 Run A: accuracy 60.0% to 66.7%, solved rate 80.0% to 96.7%.
- B0 on the 100-problem sample (Bedrock): 68% to 78%.
- The B1 run on Cerebras (kept only as a provider check) had 14 crashed first attempts. Replaying their code with
  the fix, with no new LLM calls, made 8 of them correct: B0 79 of 100 instead of 71.

## 6. OpsOR-Bench wording ambiguities

**Date.** 2026-10-20 (#20).

**Failure.** An independent re-modelling of all 36 problems from the question text alone found rules that could be
read in more than one way: when two flights at the same gate overlap, and how the crew rest rule counts consecutive
shifts.

**Change.** The gate overlap rule and the crew shift rule were stated explicitly, availability is listed in shift
order, and the dispatch questions list only usable transit costs. The data file was regenerated.

**Effect.** All 36 reference answers are unchanged; only the question text changed. The independent models match
all 36 stored optima, and regeneration is byte-identical.

## 7. `VAR:` lines filled the stored solver output

**Date.** 2026-10-20 (#21).

**Failure.** The solver runner prints up to 100 `VAR: <name> <value>` lines so the explanation can show the solution
plan. Records keep only the last 2,000 characters of stdout. With names such as `Assign_(Flight_01,Gate_2)`, 100
lines take about 3,500 characters, which would push the model's own output and the `STATUS` line out of the record.

**Change.** Variable values are parsed from the full output into `variables`, and the `VAR:` lines are removed
before the output is stored.

**Effect.** On a 120-variable model with long names, the stored output keeps the model's own lines, the `STATUS`
line and `VARS_OMITTED: 20`, and `variables` holds 100 values.

## 8. Rewordings that report the optimum with the opposite sign; paraphraser temperature

**Date.** 2026-10-26 (issue #28).

**Failure.**
- In the Bedrock pipeline run, a correct Production answer was escalated. One rewording returned -1908.17 for
  1908.17, as happens when a maximization is written as minimizing the negative, so the agreement was 0.5.
- The report (Section 2.7) says the paraphraser samples at temperature 0.7, because rewordings at temperature 0 are
  almost identical, but `run_pipeline` used the temperature-0 client for every call.

**Change.**
- Paraphrase agreement treats a value and its negative as the same optimum, with the same 0.2% tolerance. Zero is
  handled as before: 0 agrees with 0 and with -0, and not with any other value.
- `run_pipeline` takes a separate paraphrase client. The command line sets it with `--paraphrase-temperature`
  (default 0.7, saved in the run config), and the web interface uses the same default. Every other call, including
  the formalizer call on each rewording, stays at temperature 0.

**Effect.** Rescoring the saved Bedrock pipeline run (no new LLM calls) turns the Production escalation into an
answer. That run goes from 7 to 8 answered problems out of 10, all 8 correct, with no false alarm left; both wrong
models (Inventory and Pollution) are still escalated. The cost is a narrower check: a main model whose optimum has
the wrong sign now agrees with rewordings that have the right sign. None of the 189 solved attempts in all saved
runs has an objective that is correct except for its sign. The temperature
change affects new runs only.

## 9. Paraphraser and formalizer use the same model

**Date.** 2026-11-01 (issue #56, supervisor feedback on Phase 1).

**Failure.** The paraphraser and the formalizer are the same model, so their mistakes can be correlated: a reworded
question solved by the same model may repeat the main model's error and agree with a wrong answer. That would weaken
paraphrase-optimum agreement as a check.

**Change.** `--paraphrase-model` (default: the main model) chooses the model that writes the rewordings, at the
paraphrase temperature. Each rewording is still solved by the main model, so only the source of the rewordings
changes. The run config records `paraphrase_model` and `paraphrase_endpoint`, and the run folder name carries
`_para-<model>`, so runs with the two paraphraser settings are never mixed. The candidate is `bedrock:deepseek.v3.2`,
a different model family.

**Effect.** On the development split `dev_93` (`results/paraphraser/dev_93/`, `scripts/compare_paraphrasers.py`):
- **AUROC:** no gain. Paraphrase agreement scores 0.804 with DeepSeek against 0.818 with the same model, and the
  combined score 0.815 against 0.866. The intervals overlap widely (`results/gap1/dev_93*`).
- **False alarms:** 4 correct answers fall below the 0.8 threshold with DeepSeek, against 2, all from disagreeing
  rewordings. Of the 2 extra ones, canonical-0652 has a wrong main answer in the gpt-oss run, and canonical-0623 has
  the same correct answer in both runs, but DeepSeek's rewordings reach 1,020 twice instead of once.
- **Shared misreadings:** the main model's answer is sampled again in each run, so the fair comparison uses the 75
  problems where both runs gave the same feasible answer (7 wrong).
  - Same-model rewordings all agree on 5 of the 7 wrong answers, and DeepSeek rewordings on 3.
  - DeepSeek catches canonical-1653 (the Production cargo misreading of the failure analysis) and canonical-1643,
    and misses none that the same model catches.
  - Three of the 7 are Pollution, whose references are doubtful (#79). canonical-1571 equals the stated model's
    optimum, so it is wrong only against the reference, and canonical-1609 is infeasible as stated. So at most 4 of
    the 5 are clear errors. canonical-1643 is a real catch under either reading: two DeepSeek rewordings reach the
    stated optimum 23,625.8, while the pipeline's 24,530.2 is neither that nor the reference.
  - On the 68 correct answers, full agreement is about the same: 64 against 65.
- **Cost:** 19,128 tokens per problem against 21,678, but US$0.0109 against US$0.0090, because DeepSeek's tokens cost
  more (#87).

On `canonical_200` (#56's main run, `results/paraphraser/canonical_200/`, against E3 repeat 1 with the same settings):
- **AUROC:** no gain. Paraphrase agreement 0.864 [0.80, 0.93] against 0.878 [0.81, 0.94], and the combined score
  0.876 against 0.883 (`results/gap1/canonical_200_deepseek_paraphraser/`). H1 is "partly supported" in both, with
  a gain over feasibility of +0.321 against +0.303.
- **False alarms:** 8 against 6. **Accuracy:** 155 against 156 of 200.
- **Shared misreadings,** on the 173 problems with the same feasible answer in both runs (25 wrong):
  - same-model rewordings all agree on 8 wrong answers, and DeepSeek's on 7;
  - DeepSeek alone breaks 3: canonical-1706 and canonical-1692 (two of the three Production cargo misreadings of the
    failure analysis) and canonical-1582 (Pollution);
  - the same model alone breaks 2: canonical-1627 (Pollution) and canonical-0704 (Inventory);
  - against the text, the two Pollution cases are not catches: in both, the pipeline's answer equals the stated
    model's optimum (#79), so the disagreeing rewording broke an answer that is right for the question. The
    genuine catches are therefore **DeepSeek 2** (canonical-1706 and 1692, the Production misreadings) and **the same
    model 1** (canonical-0704, Inventory, whose references are sound);
  - on the 148 correct answers, full agreement is 141 against 138.
- **Cost:** 20,247 tokens per problem against 20,783, and US$0.0114 against US$0.0086 (33% more).
- **Reading:** across both splits, a second paraphrase model does not improve the signal as a whole. It is slightly
  lower on AUROC, with slightly more false alarms, at a higher cost, so the default stays the main model. What it
  does change is *which* errors are caught: DeepSeek broke three Production misreadings (1653 on dev, 1706 and 1692
  here) that every same-model rewording repeated. That is the correlated-error effect the supervisor pointed out. It
  is real but small, and it is stated as a limitation in the paper.

## 10. Requirement coverage: cut-off parser output, variable types, lost constraint names

**Date.** 2026-11-01 (#60). Development split only (`samples/dev_30.json`); runs in `results/dev_requirement_coverage/`.

**Failure.** The two runs with requirement IDs (`1_iteration1` and `2_iteration2`) flagged correct models for three
reasons:
- the parser listed variable types ("all variables are binary") as requirements, and a type cannot be a named
  constraint;
- a repair round rewrote the model and dropped the constraint names;
- the parser's JSON failed on 1 of 30 problems in `1_iteration1` and 4 of 30 in `2_iteration2` (5 of 30 with the
  Phase 1 prompts, `0_old_prompt`), all JobShop, NetworkFlow and Pollution instances. On these large instances the
  parser lists every number. Repeating some of its calls by hand showed the replies were cut off at the 4,096-token
  output cap; those repeated calls were not saved. Each failure removed the requirement signal, and in `2_iteration2`
  two wrong answers were accepted this way.

**Change.** The parser is told not to list variable types or the objective as requirements, the pipeline's repair
prompt asks to keep the constraint names, and the parser gets an output cap of 12,000 tokens and one retry on invalid
JSON.

**Effect.** On the same 30 dev problems: 0 parser failures (5 with the Phase 1 prompts); at threshold 0.8, 24 answered
and 0 wrong accepted (25 and 2 with the Phase 1 prompts); AUROC of the combined score 0.99 (0.85). Some variable-type
requirements remain: 5 of the 25 correct models are below full requirement coverage, against 4 of the 5 wrong ones.
With 30 problems these numbers move between runs; the signal is evaluated on the test samples in E4 (#35).

## 11. B2 records crashed the calibration, and a calibration fitted one system could be applied to another

**Date.** 2026-11-01 (#57 and #61, found in review).

**Failure.** B2 records store no verifier report (`"verifier": null`), so `scripts/calibrate.py` stopped with an
`AttributeError` on them. `run.py b2 --calibration` would also have applied a threshold fitted on pipeline verifier
scores to B2's sample agreement rate, and a file fitted at k = 2 could be applied to a k = 3 run or to a run with a
signal switched off. All of these scores differ.

**Change.** B2 is scored by its sample agreement rate and calibrated on its own records. A calibration file saves the
configuration it was made from (the system name such as `pipeline_p3` or `b2_r1`, the enabled signals and the parser
switch), and `run.py` refuses a file made for another configuration.

**Effect.** No saved result changed (no calibration had been run yet). Tests cover B2 records and each refusal.

## 12. Network outage during an E3 run

**Date.** 2026-11-01 (#64; the runs are in #66).

**Failure.** During E3 repeat 1 the internet connection on the machine dropped for a few minutes. Every LLM call in
that window failed after its retries: in the first pass 159 of 200 canonical problems, 85 of 120 constraint-pair
problems and 2 of 60 linguistic problems failed (`pass_1.txt` in each run folder). Starting the runs again would have
repeated the finished problems and paid for them twice.

**Change.** `run.py --resume <run folder>` runs only the problems missing from that run's records, adds their records
and rewrites the summary, which counts the resumes. It refuses any change of settings except those that change no record (`--workers`,
`--env-file`, `--trace`).

**Effect.** The three runs of E3 repeat 1 were finished from their own folders, and the console output of every pass
is saved next to the records (`pass_1.txt` to `pass_3.txt`):
- the canonical and constraint-pair runs took three passes, because I stopped the second pass by mistake before it
  wrote its summary. A stopped pass writes no summary, so `resumes` is 1 in all three runs;
- the linguistic run took two passes.

All three ended with their complete samples and 0 failed problems (#66), and no finished problem was run or paid for
twice. `summary.json` lists only the last pass's failures, so the pass files are the record of the first pass.

## 13. Too little calibration data to certify alpha = 10%

**Date.** 2026-11-02 (#78). Found in the Gap 2 analysis of E3 repeat 1 (#65, #66).

**Failure.** At alpha = 10%, the leave-one-class-out test answered only 6 of 200 problems. A threshold is accepted
only when the one-sided exact 95% bound on its calibration wrong-accept rate is at most 10%, and each fold calibrates
on about 180 problems. With the pipeline's error rates that is too few accepted answers. `scripts/power_h2.py`
gives the smallest number n of accepted answers whose one-sided exact 95% bound (`upper_bound` in
`optverify/calibration.py`) is at most 10% when round(rate x n) of them are wrong:

| Wrong-accept rate among accepted | Accepted answers needed for a bound of at most 10% |
|---|---|
| 5% | 89 |
| 6% | 154 |
| 7% | 263 |
| 8% | 593 |

At the fixed 0.8 threshold the rate is 8.0% with 163 accepted, and the strictest thresholds give about 5.5% but answer
only 45 to 50% of the problems, below the 50% that H2 needs.

**Change.**
- `canonical_587` adds up to 40 new problems per class to `canonical_200`, giving 60 per class. NetworkFlow gets 47,
  because the benchmark has only 50 and 3 are in the development split. Each fold then calibrates on about 530 problems.
- `dev_93` grows the development split (dev_30 plus 7 per class) for signal design.
- **Rules kept:** the H2 rule and alpha are unchanged, `canonical_200` is still reported, and the sample size was
  chosen from this power analysis, not from a test result on the new problems.
- Pooling the three repeats would not help, because they hold the same problems and are not independent.

**Effect.** More data alone does not reach 10%: the class shift, not the sample size, is what fails
(`results/gap2/canonical_587*`). The run finished all 587 problems.
- **All classes:** H2 is not supported. At alpha = 10% the test answers 92 of 587 (15.7%) and half of them are
  wrong. Only two folds find a threshold:
  - with Pollution held out, the other classes allow 0.683, and all 38 Pollution answers it accepts are wrong;
  - with Production held out, the threshold 0.889 accepts 54 answers, 8 of them wrong.

  So 8 of the 9 folds that calibrate on Pollution find no threshold, because its confident wrong answers keep their
  bound above 10%. The Production fold is the exception. The 38 "wrong" answers of the Pollution fold are all on
  Pollution references that the reference check could not reproduce from the text (#79), so most of the
  all-class failure at 10% comes from that one class of doubtful references. The smallest alpha the data supports is 21% (26% with the bound), against 18% (24%) on
  `canonical_200`.
- **Without Pollution** (its references do not follow from the text, #79): the held-out wrong-accept rate tracks the
  target, 7.5%, 9.1% and 10.7% at alpha 8%, 9% and 10%, with 86% to 94% answered.
  - At 10% the rate is 0.7 points too high, and its one-sided bound is 13.3%, so H2 still fails.
  - Most of the 53 wrong accepts come from one fold: with Inventory held out, the other classes allow a loose
    threshold (0.533) that accepts 57 Inventory answers, 34 of them wrong. The Inventory references are sound, so
    these are real model errors on a class the calibration did not see.
- **The fixed 0.8 threshold** does better than the calibrated one:
  - 10.4% wrong at 81.8% coverage on all classes;
  - 5.5% [3.6%, 8.0%] at 86.3% without Pollution.
- **Gap 1 agrees with `canonical_200`** (`results/gap1/canonical_587/`): the combined AUROC is 0.859, +0.321
  [+0.28, +0.36] over feasibility, and only the paraphrase drop is significant.
- **Conclusion:** a threshold fitted on some problem classes does not carry over to a class with its own kind of
  error. A larger sample makes the bound tighter, not the shift smaller.


## 14. The parser writes the TSP subtour constraint wrongly, and the formalizer copies it

**Date.** 2026-11-02 (#41 failure analysis, with a diagnostic run). Found while comparing the pipeline with B1 (#33).

**Failure.** On `canonical_200`, B1 solves all 20 TSP problems in repeat 1, but the pipeline solves 14, 16 and 18
in its three repeats. The failure analysis (#80) traced the infeasible TSP models to a Miller-Tucker-Zemlin
constraint that includes the start city. The saved specs show where that comes from:
- the parser usually writes the textbook rule as a requirement, "for all i ≠ j, u_i - u_j + N x_ij ≤ N - 1",
  which keeps the start city in;
- the formalizer is told to implement every requirement as a named constraint, so it often copies the rule;
- B1 formalizes from the question alone and leaves the start city out.

`scripts/tsp_parser_rules.py` lists, for every TSP record, the parser's subtour requirements and labels the rule by
the range of its MTZ formula (`results/failures/tsp_parser/parser_rules.csv`, with the requirement text kept so each
label can be checked by hand). By final solver status:

| Parser rule | E3 repeat 1 | `canonical_587` |
|---|---|---|
| Keeps the start city in | 6 correct, 5 infeasible, 1 no code | 24 correct, 6 infeasible, 2 wrong (optimal) |
| Leaves the start city out | 8 correct | 19 correct, 2 wrong (optimal) |
| States no formula | none | 2 correct, 1 infeasible, 2 no code, 2 wrong (optimal) |

- **Infeasible models:** all 12 (5 and 7) come with a rule that keeps the start city in (11) or states no formula
  (1). None comes with a rule that leaves it out.
- **Leaving it out works:** when the rule leaves the start city out, 27 of 29 answers are correct, and the 2 wrong
  ones are feasible models that are wrong for another reason.
- **The formalizer sometimes fixes it:** when the rule keeps it in, 30 of 44 answers are still correct, so the
  formalizer does not always copy it.
- **No code:** these 3 cases have no model at all, so the rule cannot be checked against one.

**Diagnostic run.** The same pipeline without the parser (`--no-parser`, k = 3, r = 1, threshold 0.8) on the 60 TSP
problems of `canonical_587` (`samples/tsp_60.json`, written by `scripts/make_samples.py`). It is compared on the
same 60 problems with the `canonical_587` run in `results/failures/tsp_parser/ablations.csv` (row iv, from
`scripts/ablation_table.py`):

| | With the parser | Without the parser |
|---|---|---|
| Correct | 45 of 60 (75.0%) | 56 of 60 (93.3%) |
| Infeasible models | 7 | 1 |
| No code (no model at all) | 2 | 1 |
| Answered at 0.8 | 45 | 56 |
| Wrong accepted | 1 | 0 |
| Tokens per problem | 29,772 | 23,378 |

- **Paired:** 12 problems are correct only without the parser, and 1 only with it. The exact McNemar p is 0.003,
  counted from the two `records.jsonl` files.
- **Repair:** on TSP, the repair round matters a lot. With the parser, r = 0 gives only 33% (row vii), because the
  first model is often infeasible and the repair round fixes many of them.

**Change.** None to the system: a prompt change found on test problems would be tuned on the test set. The finding
goes into the failure analysis and future work. A parser that states *what* must hold ("no subtours") rather than
a formula, or a repair prompt that names this common cause of infeasibility, are direct fixes to test on the
development split.

**Effect.** This is a diagnostic on one class, not ablation (iv) itself. Ablation (iv) runs on `ablation_50` (#38),
which has only 5 TSP problems. It shows a cost of the parser that the Phase 1 design did not expect: an error in the
parser's requirements reaches the model built from them. Here the models are mostly infeasible, so the checks refuse
them: the cost falls on coverage, not on the wrong-accept rate.

## 15. B2 stopped at its sample cap, below the pipeline's token budget

**Date.** 2026-11-02 (#37, Gap 3). Found in the first 4 problems of B2 repeat 1 on `canonical_200`.

**Failure.** B2 draws samples until its tokens reach the budget, or until it has `max_samples` samples. The budget is
the E3 repeat 1 mean, 20,783 tokens per problem. With `max_samples` 10, all 10 samples were used at 15,196 to
19,500 tokens, so the cap stopped B2 first, at a mean near 17,600. That is outside the 10% band of objective D3
(18,705 to 22,861) and would compare B2 at a smaller budget than the pipeline, which is unfair to B2.

**Change.** `--max-samples 20`, so the budget is what stops B2 on 199 of the 200 problems. The cap still stopped one:
canonical-0947, a Knapsack problem with short samples, at 20,401 tokens. B2 is charged only for the samples within
the budget (`samples_within_budget`). The 4-problem partial run was stopped and is not in `results/`, and the run started again
from the beginning. `experiments/configs/G3.json` now says 20. A network outage stopped 88 problems of the new run;
they were run again with `--resume` (`pass_2.txt`), so 200 of 200 finished with 0 failed.

**Effect** (`results/gap3/canonical_200/`, `scripts/analyze_e3.py` against E3 repeat 1, B0 and B1 from #90):

| Paraphrases k | Tokens per problem, pipeline / B2 | Wrong-accept rate at 50% coverage, pipeline / B2 | Paired 95% interval (pipeline minus B2) |
|---|---|---|---|
| 1 | 12,418 / 12,344 | 9.0% / 10.1% | [-6.7, +4.8] points |
| 2 | 16,642 / 16,721 | 7.0% / 8.1% | [-6.6, +3.7] points |
| 3 | 20,783 / 20,881 | 6.0% / 6.4% | [-5.0, +4.3] points |

- **Budget match:** B2 is within 0.6% of the pipeline at every level, so D3 holds.
- **H3: not supported.** At equal tokens, the pipeline's wrong-accept rate is lower at every level, but every interval
  contains 0. Accuracy is 78.0% against 80.5% (exact McNemar p = 0.30), so B2 is not significantly better either.
- **Reading:** at the same cost, the pipeline's verification signals and majority-vote sampling refuse wrong answers
  about equally well on this benchmark. The pipeline gives reasons for each refusal (missing requirements,
  disagreeing rewordings) where B2 only gives a vote share; that is a difference in what the user learns, not in the
  error rate. This is one repeat; repeats 2 and 3 of B2 (#37) would narrow the intervals.

## 16. Why no threshold meets alpha = 10% under leave-one-class-out

**Date.** 2026-11-02 (#36, exploratory). A follow-up to devlog 13: is the calibration rule the problem, or the
score?

**Failure.** H2 fails at alpha = 10% on every canonical run. Devlog 13 showed that most of the failure comes from
held-out classes with their own kind of error. This entry asks whether another rule for picking the threshold would
avoid it.

**The floor of the score** (`scripts/score_floor.py`, `results/gap2/score_floor/`). No threshold accepts fewer wrong
answers than the strictest one, which keeps only the answers at the top score (1.0). On `canonical_587`:
- 280 answers have score 1.0, and 21 of them (7.5%) are wrong. Without Pollution it is 11 of 270 (4.1%).
- **Pollution:** 10 of 10 answers at score 1.0 are wrong. Their references do not follow from the text (#79).
- **Production:** 8 of 54 answers at score 1.0 are wrong (14.8%). This is the cargo misreading that every rewording
  repeats (devlog 9, #41).
- **Two smaller classes** are also above 10% at score 1.0: Inventory (1 of 4) and Portfolio (1 of 6).

So when one of these classes is held out, no threshold can bring *that fold* below 10%. But H2 is judged on the
held-out answers pooled over all ten folds, and the pooled floor is below 10% (4% to 8% in every `canonical_200`
repeat).

**One threshold could meet H2 on all classes.** Over all 587 problems of `canonical_587`, the thresholds from 0.99145
to 0.99187 answer 54.7% to 55.2% with 23 wrong (7.1% to 7.2%), and their one-sided bound is at most 10.0%. That meets
every part of H2. These thresholds are picked in hindsight, and the window is only three thresholds wide, so this is
not a result. It shows that the score separates well enough. What fails is the rule: from nine classes, no rule finds
such a threshold, because R0's threshold swings with whether Pollution is in the calibration set (devlog 13).

**Other rules** (`scripts/threshold_rules.py`, `results/gap2/threshold_rules/`, each tested leave-one-class-out as in
H2):
- R0, the H2 rule (pooled one-sided bound);
- R1, nested strictest: hold out each calibration class in turn, and take the strictest of those thresholds;
- R2, worst class: every calibration class must be at most alpha;
- R3, pooled observed rate with no bound.

On E3 repeat 1 of `canonical_200`, no rule set to alpha = 10% meets it with at least 50% answered. (R2 set to 12%
answers 54.5% with 6.4% wrong, but reaching 10% by setting the rule to 12% would be tuning it on the result.) On
`canonical_587`:
- **All classes:** none meets it either. R2 answers nothing, because three classes with 5 or more answers at score
  1.0 are above alpha there (Pollution, Production and Portfolio; Inventory has only 4). R3 answers 80.2%, with
  13.2% wrong.
- **Without Pollution:** R1 at alpha 10% answers 86.1% with 7.5% wrong, and a one-sided bound of 9.8%. That meets both
  the H2 rule and the bound. R0 gives 10.7% there (devlog 13). But R0 at alpha 8% answers 451 of 527 with the same
  34 wrong, so R1 at 10% picks almost the threshold R0 picks one step stricter. Its gain is close to "use a lower
  alpha", which the alpha scan already shows (the smallest alpha meeting H2's rule without Pollution is 8%).

**Change.** None to H2. R1 was not chosen in advance, and on `canonical_200` it answers almost nothing, because its
inner folds are too small. Reporting it as the H2 result would be choosing the rule after seeing the results.

**Effect.** Two findings for the paper:
1. The per-class floor explains why the Pollution and Production folds fail: errors that every signal agrees with
   (Pollution's doubtful references, Production's shared misreading). The pooled failure is the rule's sensitivity to
   which classes are in the calibration set. A threshold that meets H2 on all classes exists, but no rule finds it
   from nine classes.
2. The nested rule R1 is close to R0 with a lower alpha, so it is not a new idea in itself. A rule that is robust to
   which classes are calibrated on remains the open problem, and needs a test set up in advance, on new problems.
