# v1 against v3, paired on 60 problems

- v1: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_dev_tsp_inventory_60_r1_20261102-0923/records.jsonl`
- v3: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_prompts-v3_dev_tsp_inventory_60_r1_20261102-1010/records.jsonl`
- Threshold for accepted answers: 0.8

| Group | Problems | Correct, v1 / v3 | Only v1 / only v3 correct | McNemar p | No feasible model | Accepted | Wrong accepted | Tokens per problem |
|---|---|---|---|---|---|---|---|---|
| Inventory | 30 | 15 / 15 | 2 / 2 | 1.000 | 3 / 2 | 13 / 9 | 4 / 2 | 19,172 / 20,945 |
| TSP | 30 | 28 / 28 | 1 / 1 | 1.000 | 2 / 2 | 26 / 27 | 0 / 0 | 41,221 / 37,291 |
| all | 60 | 43 / 43 | 3 / 3 | 1.000 | 5 / 4 | 39 / 36 | 4 / 2 | 30,197 / 29,118 |
