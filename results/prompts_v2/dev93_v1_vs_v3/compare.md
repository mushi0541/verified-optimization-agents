# v1 against v3, paired on 93 problems

- v1: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_dev_93_r1_20261101-2255/records.jsonl`
- v3: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_prompts-v3_dev_93_r1_20261102-1034/records.jsonl`
- Threshold for accepted answers: 0.8

| Group | Problems | Correct, v1 / v3 | Only v1 / only v3 correct | McNemar p | No feasible model | Accepted | Wrong accepted | Tokens per problem |
|---|---|---|---|---|---|---|---|---|
| BinPacking | 10 | 9 / 10 | 0 / 1 | 1.000 | 1 / 0 | 9 / 10 | 0 / 0 | 12,853 / 12,770 |
| Inventory | 10 | 3 / 3 | 2 / 2 | 1.000 | 1 / 1 | 4 / 6 | 2 / 3 | 19,495 / 18,202 |
| JobShop | 10 | 9 / 10 | 0 / 1 | 1.000 | 1 / 0 | 8 / 10 | 0 / 0 | 22,183 / 22,178 |
| Knapsack | 10 | 10 / 10 | 0 / 0 | 1.000 | 0 / 0 | 10 / 10 | 0 / 0 | 10,133 / 10,805 |
| NetworkFlow | 3 | 3 / 3 | 0 / 0 | 1.000 | 0 / 0 | 3 / 3 | 0 / 0 | 30,371 / 32,540 |
| Pollution | 10 | 0 / 0 | 0 / 0 | 1.000 | 0 / 0 | 5 / 3 | 5 / 3 | 27,680 / 28,918 |
| Portfolio | 10 | 10 / 10 | 0 / 0 | 1.000 | 0 / 0 | 10 / 10 | 0 / 0 | 20,390 / 20,129 |
| Production | 10 | 7 / 7 | 0 / 0 | 1.000 | 0 / 0 | 9 / 9 | 2 / 2 | 23,658 / 21,501 |
| TSP | 10 | 10 / 9 | 1 / 0 | 1.000 | 0 / 1 | 10 / 9 | 0 / 0 | 38,660 / 34,603 |
| Transportation | 10 | 10 / 10 | 0 / 0 | 1.000 | 0 / 0 | 10 / 10 | 0 / 0 | 17,446 / 17,510 |
| all | 93 | 71 / 72 | 3 / 4 | 1.000 | 3 / 2 | 78 / 80 | 9 / 8 | 21,678 / 21,116 |
