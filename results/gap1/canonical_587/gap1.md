# Gap 1 (H1): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Mean (sd) |
|---|---|---|
| feasibility | 0.539 [0.52, 0.56] | 0.539 |
| number | 0.518 [0.48, 0.56] | 0.518 |
| requirement | 0.628 [0.58, 0.68] | 0.628 |
| paraphrase | 0.852 [0.81, 0.89] | 0.852 |
| combined | 0.859 [0.82, 0.90] | 0.859 |
| combined_without_number | 0.853 [0.81, 0.89] | 0.853 |
| combined_without_requirement | 0.862 [0.82, 0.90] | 0.862 |
| combined_without_paraphrase | 0.621 [0.57, 0.67] | 0.621 |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 587 | 445 | +0.321 [+0.28, +0.36] | number: no, requirement: no, paraphrase: yes | 480 | 89.6% | 96.6% |
