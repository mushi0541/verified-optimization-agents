# v1 against v2, paired on 60 problems

- v1: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_dev_tsp_inventory_60_r1_20261102-0923/records.jsonl`
- v2: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_prompts-v2_dev_tsp_inventory_60_r1_20261102-0924/records.jsonl`
- Threshold for accepted answers: 0.8

| Group | Problems | Correct, v1 / v2 | Only v1 / only v2 correct | McNemar p | No feasible model | Accepted | Wrong accepted | Tokens per problem |
|---|---|---|---|---|---|---|---|---|
| Inventory | 30 | 15 / 13 | 4 / 2 | 0.688 | 3 / 2 | 13 / 5 | 4 / 1 | 19,172 / 20,476 |
| TSP | 30 | 28 / 25 | 5 / 2 | 0.453 | 2 / 2 | 26 / 21 | 0 / 0 | 41,221 / 38,987 |
| all | 60 | 43 / 38 | 9 / 4 | 0.267 | 5 / 4 | 39 / 26 | 4 / 1 | 30,197 / 29,732 |
