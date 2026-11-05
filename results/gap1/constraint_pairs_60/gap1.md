# Gap 1 (H1): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_constraint_pairs_60_r1_20261101-1430/records.jsonl, results/pipeline_bedrock-openai.gpt-oss-120b-1-0_constraint_pairs_60_r1_20261101-2337/records.jsonl, results/pipeline_bedrock-openai.gpt-oss-120b-1-0_constraint_pairs_60_r1_20261105-2035/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Run 2 | Run 3 | Mean (sd) |
|---|---|---|---|---|
| feasibility | 0.674 [0.60, 0.75] | 0.682 [0.61, 0.76] | 0.663 [0.60, 0.73] | 0.673 (0.009) |
| number | 0.661 [0.58, 0.75] | 0.662 [0.58, 0.75] | 0.648 [0.57, 0.73] | 0.657 (0.007) |
| requirement | 0.699 [0.60, 0.79] | 0.756 [0.66, 0.84] | 0.744 [0.65, 0.83] | 0.733 (0.030) |
| paraphrase | 0.936 [0.88, 0.98] | 0.983 [0.97, 0.99] | 0.945 [0.90, 0.98] | 0.955 (0.025) |
| combined | 0.934 [0.88, 0.97] | 0.969 [0.94, 0.99] | 0.952 [0.91, 0.99] | 0.952 (0.017) |
| combined_without_number | 0.942 [0.89, 0.98] | 0.980 [0.96, 0.99] | 0.957 [0.91, 0.99] | 0.960 (0.019) |
| combined_without_requirement | 0.934 [0.88, 0.98] | 0.979 [0.96, 0.99] | 0.953 [0.91, 0.99] | 0.955 (0.022) |
| combined_without_paraphrase | 0.693 [0.60, 0.79] | 0.749 [0.65, 0.84] | 0.725 [0.63, 0.81] | 0.722 (0.028) |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 120 | 74 | +0.261 [+0.18, +0.33] | number: no, requirement: no, paraphrase: yes | 73 | 90.4% | 89.2% |
| 2 | 120 | 76 | +0.287 [+0.22, +0.35] | number: no, requirement: no, paraphrase: yes | 73 | 93.2% | 89.5% |
| 3 | 120 | 74 | +0.289 [+0.21, +0.36] | number: no, requirement: no, paraphrase: yes | 69 | 94.2% | 87.8% |

By group (bootstrap 95% intervals within each group):

| Run | Group | Problems | Correct | Feasibility | Combined [95%] | Gain [95%] | Coverage | Precision |
|---|---|---|---|---|---|---|---|---|
| 1 | augmented | 60 | 32 | 0.732 | 0.909 [0.82, 0.97] | +0.177 [+0.08, +0.27] | 51.7% | 87.1% |
| 1 | original | 60 | 42 | 0.583 | 0.966 [0.92, 1.00] | +0.383 [+0.29, +0.47] | 70.0% | 92.9% |
| 2 | augmented | 60 | 34 | 0.731 | 0.959 [0.90, 0.99] | +0.229 [+0.14, +0.32] | 53.3% | 90.6% |
| 2 | original | 60 | 42 | 0.611 | 0.979 [0.94, 1.00] | +0.368 [+0.27, +0.46] | 68.3% | 95.1% |
| 3 | augmented | 60 | 33 | 0.741 | 0.923 [0.84, 0.98] | +0.182 [+0.09, +0.28] | 50.0% | 90.0% |
| 3 | original | 60 | 41 | 0.553 | 0.987 [0.96, 1.00] | +0.435 [+0.35, +0.50] | 65.0% | 97.4% |
