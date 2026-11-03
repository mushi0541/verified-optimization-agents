# Gap 1 (H1): results/pipeline_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261102-1259/records.jsonl

H1: **not supported**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.862 [0.81, 0.91] | 0.862 |
| number | 0.888 [0.83, 0.94] | 0.888 |
| requirement | 0.883 [0.82, 0.94] | 0.883 |
| paraphrase | 0.931 [0.89, 0.97] | 0.931 |
| combined | 0.937 [0.89, 0.98] | 0.937 |
| combined_without_number | 0.927 [0.88, 0.97] | 0.927 |
| combined_without_requirement | 0.944 [0.90, 0.98] | 0.944 |
| combined_without_paraphrase | 0.893 [0.83, 0.95] | 0.893 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 200 | 131 | +0.075 [+0.03, +0.12] | number: no, requirement: no, paraphrase: yes | 132 | 91.7% | 92.4% |

B0 on the same 200 problems: answers 150 (75.0%), precision 87.3%, 19 wrong answers accepted.
