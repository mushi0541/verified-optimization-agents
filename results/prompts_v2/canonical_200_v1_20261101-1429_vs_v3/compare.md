# v1 against v3, paired on 200 problems

- v1: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl`
- v3: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_prompts-v3_canonical_200_r1_20261102-1109/records.jsonl`
- Threshold for accepted answers: 0.8

| Group | Problems | Correct, v1 / v3 | Only v1 / only v3 correct | McNemar p | No feasible model | Accepted | Wrong accepted | Tokens per problem |
|---|---|---|---|---|---|---|---|---|
| BinPacking | 20 | 19 / 20 | 0 / 1 | 1.000 | 0 / 0 | 19 / 20 | 0 / 0 | 12,012 / 12,239 |
| Inventory | 20 | 11 / 8 | 4 / 1 | 0.375 | 0 / 1 | 7 / 10 | 2 / 3 | 20,162 / 20,007 |
| JobShop | 20 | 19 / 20 | 0 / 1 | 1.000 | 0 / 0 | 19 / 20 | 0 / 0 | 20,340 / 20,930 |
| Knapsack | 20 | 20 / 20 | 0 / 0 | 1.000 | 0 / 0 | 20 / 20 | 0 / 0 | 11,870 / 12,129 |
| NetworkFlow | 20 | 19 / 20 | 0 / 1 | 1.000 | 1 / 0 | 19 / 19 | 0 / 0 | 31,684 / 32,824 |
| Pollution | 20 | 0 / 0 | 0 / 0 | 1.000 | 0 / 0 | 5 / 5 | 5 / 5 | 26,150 / 26,291 |
| Portfolio | 20 | 17 / 17 | 0 / 0 | 1.000 | 0 / 0 | 20 / 20 | 3 / 3 | 22,121 / 22,792 |
| Production | 20 | 17 / 17 | 0 / 0 | 1.000 | 0 / 0 | 20 / 19 | 3 / 2 | 22,561 / 23,866 |
| TSP | 20 | 14 / 17 | 1 / 4 | 0.375 | 6 / 3 | 14 / 17 | 0 / 0 | 20,876 / 23,721 |
| Transportation | 20 | 20 / 20 | 0 / 0 | 1.000 | 0 / 0 | 20 / 20 | 0 / 0 | 20,058 / 20,707 |
| all | 200 | 156 / 159 | 5 / 8 | 0.581 | 7 / 4 | 163 / 170 | 13 / 13 | 20,783 / 21,551 |
