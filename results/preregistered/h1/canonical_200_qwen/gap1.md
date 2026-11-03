# Gap 1 (H1): results/pipeline_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261102-1258/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.651 [0.60, 0.71] | 0.651 |
| number | 0.636 [0.57, 0.70] | 0.636 |
| requirement | 0.757 [0.68, 0.83] | 0.757 |
| paraphrase | 0.897 [0.85, 0.95] | 0.897 |
| combined | 0.928 [0.88, 0.96] | 0.928 |
| combined_without_number | 0.920 [0.87, 0.96] | 0.920 |
| combined_without_requirement | 0.903 [0.85, 0.95] | 0.903 |
| combined_without_paraphrase | 0.756 [0.68, 0.83] | 0.756 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 200 | 137 | +0.277 [+0.22, +0.34] | number: no, requirement: no, paraphrase: yes | 132 | 90.2% | 86.9% |

B0 on the same 200 problems: answers 150 (75.0%), precision 82.0%, 27 wrong answers accepted.
