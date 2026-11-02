# Paraphrase model comparison (#56)

- Same model as the formalizer: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_dev_93_r1_20261101-2255/records.jsonl`
- Other paraphrase model: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_para-bedrock-deepseek.v3.2_dev_93_r1_20261101-2321/records.jsonl`

| Paraphraser | Correct | Paraphrase AUROC | Combined AUROC | False alarms | Tokens per problem |
|---|---|---|---|---|---|
| same model | 71/93 | 0.818 | 0.866 | 2 | 21678 |
| other model | 73/93 | 0.804 | 0.815 | 4 | 19128 |

On the 75 problems where both runs gave the same feasible answer (7 wrong, 68 correct):

- Wrong answers all rewordings agree on: 5 with the same model, 3 with the other model.
- Caught only by the other model: canonical-1643, canonical-1653.
- Caught only by the same model: none.
- Correct answers all rewordings agree on: 64 with the same model, 65 with the other model.

| Problem | Class | Agreement, same model | Agreement, other model |
|---|---|---|---|
| canonical-1643 | Pollution | 1.000 | 0.333 |
| canonical-0750 | Inventory | 0.333 | 0.333 |
| canonical-0658 | Inventory | 1.000 | 1.000 |
| canonical-1571 | Pollution | 1.000 | 1.000 |
| canonical-1609 | Pollution | 1.000 | 1.000 |
| canonical-1724 | Production | 0.667 | 0.667 |
| canonical-1653 | Production | 1.000 | 0.333 |
