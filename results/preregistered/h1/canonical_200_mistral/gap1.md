# Gap 1 (H1): results/pipeline_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261102-1258/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.578 [0.53, 0.63] | 0.578 |
| number | 0.555 [0.49, 0.62] | 0.555 |
| requirement | 0.585 [0.49, 0.67] | 0.585 |
| paraphrase | 0.900 [0.84, 0.95] | 0.900 |
| combined | 0.883 [0.81, 0.94] | 0.883 |
| combined_without_number | 0.886 [0.82, 0.94] | 0.886 |
| combined_without_requirement | 0.894 [0.83, 0.95] | 0.894 |
| combined_without_paraphrase | 0.575 [0.48, 0.67] | 0.575 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 200 | 142 | +0.305 [+0.23, +0.37] | number: no, requirement: no, paraphrase: yes | 143 | 91.6% | 92.3% |

B0 on the same 200 problems: answers 177 (88.5%), precision 78.0%, 39 wrong answers accepted.
