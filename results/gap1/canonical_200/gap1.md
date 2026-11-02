# Gap 1 (H1): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl, results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl, results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0153/records.jsonl

**Only the problems of `samples/canonical_200.json`** (`--sample`), in every run.

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Run 2 | Run 3 | Mean (sd) |
|---|---|---|---|---|
| feasibility | 0.580 [0.53, 0.64] | 0.512 [0.50, 0.54] | 0.536 [0.50, 0.58] | 0.542 (0.034) |
| number | 0.590 [0.51, 0.67] | 0.503 [0.45, 0.57] | 0.544 [0.47, 0.62] | 0.545 (0.044) |
| requirement | 0.681 [0.59, 0.77] | 0.656 [0.57, 0.74] | 0.586 [0.50, 0.67] | 0.641 (0.049) |
| paraphrase | 0.878 [0.81, 0.94] | 0.859 [0.78, 0.92] | 0.824 [0.75, 0.90] | 0.854 (0.027) |
| combined | 0.883 [0.81, 0.95] | 0.901 [0.83, 0.96] | 0.826 [0.73, 0.91] | 0.870 (0.039) |
| combined_without_number | 0.862 [0.78, 0.94] | 0.878 [0.80, 0.94] | 0.808 [0.71, 0.89] | 0.850 (0.037) |
| combined_without_requirement | 0.901 [0.84, 0.96] | 0.892 [0.82, 0.95] | 0.843 [0.76, 0.92] | 0.879 (0.031) |
| combined_without_paraphrase | 0.694 [0.60, 0.79] | 0.661 [0.57, 0.75] | 0.604 [0.51, 0.70] | 0.653 (0.046) |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 200 | 156 | +0.303 [+0.22, +0.38] | number: no, requirement: no, paraphrase: yes | 163 | 92.0% | 96.2% |
| 2 | 200 | 157 | +0.389 [+0.32, +0.45] | number: no, requirement: no, paraphrase: yes | 169 | 91.7% | 98.7% |
| 3 | 200 | 158 | +0.290 [+0.20, +0.37] | number: no, requirement: no, paraphrase: yes | 167 | 91.0% | 96.2% |
