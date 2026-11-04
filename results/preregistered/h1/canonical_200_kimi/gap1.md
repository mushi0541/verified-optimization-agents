# Gap 1 (H1): results/pipeline_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261102-1258/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.557 [0.51, 0.62] | 0.557 |
| number | 0.572 [0.50, 0.65] | 0.572 |
| requirement | 0.583 [0.48, 0.68] | 0.583 |
| paraphrase | 0.793 [0.70, 0.88] | 0.793 |
| combined | 0.775 [0.67, 0.87] | 0.775 |
| combined_without_number | 0.768 [0.67, 0.86] | 0.768 |
| combined_without_requirement | 0.817 [0.73, 0.90] | 0.817 |
| combined_without_paraphrase | 0.588 [0.48, 0.69] | 0.588 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 200 | 165 | +0.218 [+0.12, +0.32] | number: no, requirement: no, paraphrase: yes | 173 | 89.0% | 93.3% |

B0 on the same 200 problems: answers 197 (98.5%), precision 81.7%, 36 wrong answers accepted.
