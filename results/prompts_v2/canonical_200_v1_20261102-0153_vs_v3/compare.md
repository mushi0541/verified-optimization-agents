# v1 against v3, paired on 200 problems

- v1: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0153/records.jsonl`
- v3: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_prompts-v3_canonical_200_r1_20261102-1109/records.jsonl`
- Threshold for accepted answers: 0.8

| Group | Problems | Correct, v1 / v3 | Only v1 / only v3 correct | McNemar p | No feasible model | Accepted | Wrong accepted | Tokens per problem |
|---|---|---|---|---|---|---|---|---|
| BinPacking | 20 | 20 / 20 | 0 / 0 | 1.000 | 0 / 0 | 20 / 20 | 0 / 0 | 11,957 / 12,239 |
| Inventory | 20 | 11 / 8 | 3 / 0 | 0.250 | 1 / 1 | 9 / 10 | 3 / 3 | 19,275 / 20,007 |
| JobShop | 20 | 17 / 20 | 0 / 3 | 0.250 | 0 / 0 | 17 / 20 | 0 / 0 | 20,812 / 20,930 |
| Knapsack | 20 | 20 / 20 | 0 / 0 | 1.000 | 0 / 0 | 20 / 20 | 0 / 0 | 12,222 / 12,129 |
| NetworkFlow | 20 | 18 / 20 | 0 / 2 | 0.500 | 0 / 0 | 18 / 19 | 0 / 0 | 35,561 / 32,824 |
| Pollution | 20 | 0 / 0 | 0 / 0 | 1.000 | 0 / 0 | 6 / 5 | 6 / 5 | 24,027 / 26,291 |
| Portfolio | 20 | 17 / 17 | 0 / 0 | 1.000 | 0 / 0 | 20 / 20 | 3 / 3 | 22,182 / 22,792 |
| Production | 20 | 17 / 17 | 0 / 0 | 1.000 | 0 / 0 | 20 / 19 | 3 / 2 | 24,102 / 23,866 |
| TSP | 20 | 18 / 17 | 3 / 2 | 1.000 | 2 / 3 | 18 / 17 | 0 / 0 | 23,007 / 23,721 |
| Transportation | 20 | 20 / 20 | 0 / 0 | 1.000 | 0 / 0 | 19 / 20 | 0 / 0 | 20,017 / 20,707 |
| all | 200 | 158 / 159 | 6 / 7 | 1.000 | 3 / 4 | 167 / 170 | 15 / 13 | 21,316 / 21,551 |
