# The wrong-accept floor at the top score

Answers at the highest score of each run; no threshold accepts fewer wrong answers than this.

**Only the problems of `samples/canonical_200.json`** (`--sample`).

| Run | Top score | BinPacking | Inventory | JobShop | Knapsack | NetworkFlow | Pollution | Portfolio | Production | TSP | Transportation | All | Without Pollution |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429` | 1.000 | 0/7 | 2/3 | 0/6 | 0/20 | 0/19 | 1/1 | 0/0 | 2/19 | 0/5 | 0/10 | 5/90 (5.6%) | 4/89 (4.5%) |
| `pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254` | 1.000 | 0/5 | 1/3 | 0/9 | 0/19 | 0/20 | 2/2 | 0/0 | 1/17 | 0/8 | 0/13 | 4/96 (4.2%) | 2/94 (2.1%) |
| `pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0153` | 1.000 | 0/5 | 2/3 | 0/10 | 0/19 | 0/16 | 3/3 | 0/0 | 3/20 | 0/9 | 0/18 | 8/103 (7.8%) | 5/100 (5.0%) |

Cells are wrong / answers at the top score.
