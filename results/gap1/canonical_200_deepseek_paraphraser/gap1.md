# Gap 1 (H1): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_para-bedrock-deepseek.v3.2_canonical_200_r1_20261102-0107/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.556 [0.51, 0.61] | 0.556 |
| number | 0.581 [0.51, 0.65] | 0.581 |
| requirement | 0.661 [0.58, 0.75] | 0.661 |
| paraphrase | 0.864 [0.80, 0.93] | 0.864 |
| combined | 0.876 [0.80, 0.94] | 0.876 |
| combined_without_number | 0.860 [0.78, 0.93] | 0.860 |
| combined_without_requirement | 0.896 [0.83, 0.95] | 0.896 |
| combined_without_paraphrase | 0.663 [0.57, 0.76] | 0.663 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 200 | 155 | +0.321 [+0.24, +0.40] | number: no, requirement: no, paraphrase: yes | 161 | 91.3% | 94.8% |
