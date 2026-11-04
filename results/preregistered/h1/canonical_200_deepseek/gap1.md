# Gap 1 (H1): results/pipeline_bedrock-deepseek.v3.2_canonical_200_r1_20261102-1257/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.583 [0.53, 0.65] | 0.583 |
| number | 0.579 [0.50, 0.66] | 0.579 |
| requirement | 0.632 [0.54, 0.72] | 0.632 |
| paraphrase | 0.789 [0.71, 0.86] | 0.789 |
| combined | 0.773 [0.68, 0.86] | 0.773 |
| combined_without_number | 0.764 [0.67, 0.85] | 0.764 |
| combined_without_requirement | 0.813 [0.73, 0.89] | 0.813 |
| combined_without_paraphrase | 0.629 [0.53, 0.73] | 0.629 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 200 | 158 | +0.190 [+0.10, +0.28] | number: no, requirement: no, paraphrase: yes | 171 | 87.7% | 94.9% |

B0 on the same 200 problems: answers 192 (96.0%), precision 82.8%, 33 wrong answers accepted.
