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

**Effect.** To be measured: one pipeline run on `canonical_200` with the second paraphraser, compared with the
same-model paraphraser on the paraphrase-agreement AUROC and the false-alarm rate. This entry is updated with the
result when the run is in.
