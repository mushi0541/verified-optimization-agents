# Gap 1 (H1): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.576 [0.54, 0.61] | 0.576 |
| number | 0.587 [0.54, 0.63] | 0.587 |
| requirement | 0.512 [0.45, 0.58] | 0.512 |
| paraphrase | 0.834 [0.79, 0.88] | 0.834 |
| combined | 0.781 [0.72, 0.85] | 0.781 |
| combined_without_number | 0.773 [0.70, 0.84] | 0.773 |
| combined_without_requirement | 0.857 [0.81, 0.90] | 0.857 |
| combined_without_paraphrase | 0.519 [0.45, 0.59] | 0.519 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 1070 | 971 | +0.205 [+0.14, +0.27] | number: no, requirement: no, paraphrase: yes | 988 | 96.5% | 98.1% |

B0 on the same 1070 problems: answers 1022 (95.5%), precision 92.9%, 73 wrong answers accepted.
