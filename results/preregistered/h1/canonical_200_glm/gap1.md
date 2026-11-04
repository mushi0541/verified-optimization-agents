# Gap 1 (H1): results/pipeline_bedrock-zai.glm-4.7_canonical_200_r1_20261102-1258/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.704 [0.64, 0.77] | 0.704 |
| number | 0.713 [0.64, 0.79] | 0.713 |
| requirement | 0.701 [0.63, 0.77] | 0.701 |
| paraphrase | 0.872 [0.81, 0.92] | 0.872 |
| combined | 0.890 [0.83, 0.94] | 0.890 |
| combined_without_number | 0.884 [0.82, 0.94] | 0.884 |
| combined_without_requirement | 0.888 [0.83, 0.94] | 0.888 |
| combined_without_paraphrase | 0.710 [0.63, 0.78] | 0.710 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 200 | 146 | +0.187 [+0.12, +0.25] | number: no, requirement: no, paraphrase: yes | 147 | 89.8% | 90.4% |

B0 on the same 200 problems: answers 159 (79.5%), precision 74.8%, 40 wrong answers accepted.
