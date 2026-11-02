# Gap 1 (H1): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_para-bedrock-deepseek.v3.2_dev_93_r1_20261101-2321/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.525 [0.50, 0.58] | 0.525 |
| number | 0.466 [0.41, 0.53] | 0.466 |
| requirement | 0.661 [0.53, 0.79] | 0.661 |
| paraphrase | 0.804 [0.69, 0.92] | 0.804 |
| combined | 0.815 [0.68, 0.94] | 0.815 |
| combined_without_number | 0.829 [0.70, 0.94] | 0.829 |
| combined_without_requirement | 0.783 [0.65, 0.91] | 0.783 |
| combined_without_paraphrase | 0.637 [0.49, 0.78] | 0.637 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 93 | 73 | +0.290 [+0.15, +0.42] | number: no, requirement: no, paraphrase: yes | 77 | 89.6% | 94.5% |
