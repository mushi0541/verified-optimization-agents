# v2 against v3, paired on 60 problems

- v2: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_prompts-v2_dev_tsp_inventory_60_r1_20261102-0924/records.jsonl`
- v3: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_prompts-v3_dev_tsp_inventory_60_r1_20261102-1010/records.jsonl`
- Threshold for accepted answers: 0.8

| Group | Problems | Correct, v2 / v3 | Only v2 / only v3 correct | McNemar p | No feasible model | Accepted | Wrong accepted | Tokens per problem |
|---|---|---|---|---|---|---|---|---|
| Inventory | 30 | 13 / 15 | 1 / 3 | 0.625 | 2 / 2 | 5 / 9 | 1 / 2 | 20,476 / 20,945 |
| TSP | 30 | 25 / 28 | 2 / 5 | 0.453 | 2 / 2 | 21 / 27 | 0 / 0 | 38,987 / 37,291 |
| all | 60 | 38 / 43 | 3 / 8 | 0.227 | 4 / 4 | 26 / 36 | 1 / 2 | 29,732 / 29,118 |
