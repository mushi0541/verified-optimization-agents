# Gap 1 (H1): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_linguistic_60_r1_20261101-1431/records.jsonl, results/pipeline_bedrock-openai.gpt-oss-120b-1-0_linguistic_60_r1_20261102-0045/records.jsonl, results/pipeline_bedrock-openai.gpt-oss-120b-1-0_linguistic_60_r1_20261105-2152/records.jsonl

H1: **partly supported (the gain holds, but not every signal is needed)**

| Score | Run 1 | Run 2 | Run 3 | Mean (sd) |
|---|---|---|---|---|
| feasibility | 0.583 [0.50, 0.71] | 0.553 [0.50, 0.64] | 0.594 [0.50, 0.70] | 0.577 (0.021) |
| number | 0.540 [0.43, 0.69] | 0.542 [0.48, 0.63] | 0.616 [0.51, 0.74] | 0.566 (0.044) |
| requirement | 0.730 [0.57, 0.88] | 0.675 [0.54, 0.81] | 0.678 [0.52, 0.83] | 0.694 (0.031) |
| paraphrase | 0.802 [0.65, 0.94] | 0.946 [0.87, 1.00] | 0.905 [0.80, 0.99] | 0.884 (0.074) |
| combined | 0.834 [0.68, 0.96] | 0.956 [0.90, 0.99] | 0.945 [0.87, 1.00] | 0.912 (0.068) |
| combined_without_number | 0.836 [0.68, 0.96] | 0.956 [0.90, 0.99] | 0.940 [0.86, 0.99] | 0.911 (0.065) |
| combined_without_requirement | 0.796 [0.63, 0.94] | 0.947 [0.87, 1.00] | 0.909 [0.80, 0.99] | 0.884 (0.078) |
| combined_without_paraphrase | 0.727 [0.56, 0.88] | 0.671 [0.53, 0.80] | 0.717 [0.56, 0.86] | 0.705 (0.030) |

| Run | Problems | Correct | Gain over feasibility [95%] | Each drop above 0 | Accepted | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 1 | 60 | 48 | +0.251 [+0.09, +0.40] | number: no, requirement: no, paraphrase: no | 46 | 91.3% | 87.5% |
| 2 | 60 | 41 | +0.404 [+0.31, +0.47] | number: no, requirement: no, paraphrase: yes | 43 | 90.7% | 95.1% |
| 3 | 60 | 44 | +0.352 [+0.23, +0.45] | number: no, requirement: yes, paraphrase: yes | 43 | 93.0% | 90.9% |

By group (bootstrap 95% intervals within each group):

| Run | Group | Problems | Correct | Feasibility | Combined [95%] | Gain [95%] | Coverage | Precision |
|---|---|---|---|---|---|---|---|---|
| 1 | easy | 23 | 20 | 0.667 | 0.842 [0.50, 1.00] | +0.175 [-0.07, +0.50] | 78.3% | 94.4% |
| 1 | hard | 20 | 13 | 0.571 | 0.874 [0.63, 1.00] | +0.302 [+0.06, +0.50] | 65.0% | 84.6% |
| 1 | moderate | 17 | 15 | 0.500 | 0.767 [0.44, 1.00] | +0.267 [-0.06, +0.50] | 88.2% | 93.3% |
| 2 | easy | 23 | 17 | 0.500 | 1.000 [1.00, 1.00] | +0.500 [+0.50, +0.50] | 73.9% | 100.0% |
| 2 | hard | 20 | 13 | 0.571 | 0.929 [0.81, 1.00] | +0.357 [+0.19, +0.50] | 65.0% | 84.6% |
| 2 | moderate | 17 | 11 | 0.583 | 0.970 [0.85, 1.00] | +0.386 [+0.19, +0.50] | 76.5% | 84.6% |
| 3 | easy | 23 | 17 | 0.750 | 1.000 [1.00, 1.00] | +0.250 [+0.00, +0.50] | 65.2% | 100.0% |
| 3 | hard | 20 | 14 | 0.500 | 0.935 [0.79, 1.00] | +0.435 [+0.29, +0.50] | 70.0% | 85.7% |
| 3 | moderate | 17 | 13 | 0.500 | 0.923 [0.71, 1.00] | +0.423 [+0.21, +0.50] | 82.4% | 92.9% |
