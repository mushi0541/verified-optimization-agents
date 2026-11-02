# Paraphrase model comparison (#56)

- Same model as the formalizer: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl`
- Other paraphrase model: `results/pipeline_bedrock-openai.gpt-oss-120b-1-0_para-bedrock-deepseek.v3.2_canonical_200_r1_20261102-0107/records.jsonl`

| Paraphraser | Correct | Paraphrase AUROC | Combined AUROC | False alarms | Tokens per problem |
|---|---|---|---|---|---|
| same model | 156/200 | 0.878 | 0.883 | 6 | 20783 |
| other model | 155/200 | 0.864 | 0.876 | 8 | 20247 |

On the 173 problems where both runs gave the same feasible answer (25 wrong, 148 correct):

- Wrong answers all rewordings agree on: 8 with the same model, 7 with the other model.
- Caught only by the other model: canonical-1706, canonical-1582, canonical-1692.
- Caught only by the same model: canonical-1627, canonical-0704.
- Correct answers all rewordings agree on: 141 with the same model, 138 with the other model.

| Problem | Class | Agreement, same model | Agreement, other model |
|---|---|---|---|
| canonical-0644 | Inventory | 1.000 | 1.000 |
| canonical-0774 | Inventory | 0.000 | 0.000 |
| canonical-1588 | Pollution | 1.000 | 1.000 |
| canonical-1639 | Pollution | 0.333 | 0.333 |
| canonical-1627 | Pollution | 0.667 | 1.000 |
| canonical-1580 | Pollution | 0.667 | 0.667 |
| canonical-1610 | Pollution | 0.333 | 0.333 |
| canonical-1581 | Pollution | 0.667 | 0.667 |
| canonical-1391 | Portfolio | 1.000 | 1.000 |
| canonical-1281 | Portfolio | 1.000 | 1.000 |
| canonical-1390 | Portfolio | n/a | n/a |
| canonical-1706 | Production | 1.000 | 0.667 |
| canonical-0678 | Inventory | 1.000 | 1.000 |
| canonical-0779 | Inventory | 0.333 | 0.333 |
| canonical-0697 | Inventory | 0.000 | 0.000 |
| canonical-0645 | Inventory | 0.000 | 0.000 |
| canonical-0704 | Inventory | 0.500 | 1.000 |
| canonical-1604 | Pollution | 0.000 | 0.000 |
| canonical-1616 | Pollution | 0.000 | 0.000 |
| canonical-1582 | Pollution | 1.000 | 0.667 |
| canonical-1584 | Pollution | 0.500 | 0.500 |
| canonical-1606 | Pollution | 0.333 | 0.000 |
| canonical-1638 | Pollution | 0.000 | 0.000 |
| canonical-1692 | Production | 1.000 | 0.333 |
| canonical-1710 | Production | 0.667 | 0.667 |
