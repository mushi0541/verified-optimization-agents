# B1-v1 against B1-v3, paired on 200 problems

- B1-v1: `results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0223/records.jsonl`
- B1-v3: `results/baseline_bedrock-openai.gpt-oss-120b-1-0_prompts-v3_canonical_200_r1_20261102-1109/records.jsonl`
- Threshold for accepted answers: 0.8

| Group | Problems | Correct, B1-v1 / B1-v3 | Only B1-v1 / only B1-v3 correct | McNemar p | No feasible model | Accepted | Wrong accepted | Tokens per problem |
|---|---|---|---|---|---|---|---|---|
| BinPacking | 20 | 20 / 20 | 0 / 0 | 1.000 | -- / -- | -- / -- | -- / -- | 1,689 / 1,750 |
| Inventory | 20 | 7 / 8 | 2 / 3 | 1.000 | -- / -- | -- / -- | -- / -- | 3,256 / 3,231 |
| JobShop | 20 | 16 / 20 | 0 / 4 | 0.125 | -- / -- | -- / -- | -- / -- | 2,839 / 2,929 |
| Knapsack | 20 | 20 / 20 | 0 / 0 | 1.000 | -- / -- | -- / -- | -- / -- | 1,575 / 1,521 |
| NetworkFlow | 20 | 20 / 20 | 0 / 0 | 1.000 | -- / -- | -- / -- | -- / -- | 3,742 / 3,480 |
| Pollution | 20 | 0 / 0 | 0 / 0 | 1.000 | -- / -- | -- / -- | -- / -- | 3,102 / 3,146 |
| Portfolio | 20 | 17 / 17 | 0 / 0 | 1.000 | -- / -- | -- / -- | -- / -- | 2,841 / 2,740 |
| Production | 20 | 17 / 17 | 0 / 0 | 1.000 | -- / -- | -- / -- | -- / -- | 2,528 / 2,576 |
| TSP | 20 | 20 / 20 | 0 / 0 | 1.000 | -- / -- | -- / -- | -- / -- | 2,737 / 2,755 |
| Transportation | 20 | 19 / 19 | 0 / 0 | 1.000 | -- / -- | -- / -- | -- / -- | 2,336 / 2,353 |
| all | 200 | 156 / 161 | 2 / 7 | 0.180 | -- / -- | -- / -- | -- / -- | 2,664 / 2,648 |
