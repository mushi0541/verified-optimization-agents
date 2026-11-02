# Gap 1 (H1): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_dev_93_r1_20261101-2255/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.568 [0.50, 0.65] | 0.568 |
| number | 0.513 [0.43, 0.61] | 0.513 |
| requirement | 0.648 [0.52, 0.77] | 0.648 |
| paraphrase | 0.818 [0.71, 0.93] | 0.818 |
| combined | 0.866 [0.74, 0.96] | 0.866 |
| combined_without_number | 0.874 [0.76, 0.96] | 0.874 |
| combined_without_requirement | 0.799 [0.67, 0.92] | 0.799 |
| combined_without_paraphrase | 0.621 [0.48, 0.76] | 0.621 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 93 | 71 | +0.297 [+0.17, +0.41] | number: no, requirement: no, paraphrase: yes | 78 | 88.5% | 97.2% |
