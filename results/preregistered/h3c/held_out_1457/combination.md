# The pipeline combined with B2 (1457 problems)

Budget: 17,449 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 17,449 | 86.4% | 0.779 | 6.4% | 5.2% | 4.6% | 5.9% |
| B2 | 17,423 | 88.8% | 0.839 | 3.6% | 3.6% | 3.6% | 4.9% |
| pipeline k=1 + B2 | 17,469 | 86.4% | 0.797 | 6.2% | 4.7% | 4.2% | 5.8% |
| pipeline k=2 + B2 | 17,525 | 86.4% | 0.788 | 6.5% | 4.9% | 4.4% | 6.0% |
| ceiling: pipeline k=3 + all of B2 | 44,767 | 86.4% | 0.854 | 4.3% | 3.2% | 3.4% | 5.8% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [+1.4, +3.6] | [+0.4, +1.9] | [-0.0, +1.4] | [+0.1, +1.7] |
| pipeline k=1 + B2 minus pipeline k=3 | [-1.5, +0.4] | [-1.2, +0.2] | [-1.0, +0.2] | [-0.6, +0.6] |
| pipeline k=2 + B2 minus B2 | [+1.5, +4.1] | [+0.5, +2.2] | [+0.1, +1.5] | [+0.2, +1.7] |
| pipeline k=2 + B2 minus pipeline k=3 | [-1.0, +0.5] | [-0.9, +0.3] | [-0.8, +0.3] | [-0.5, +0.7] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-0.1, +1.6] | [-1.0, +0.2] | [-0.7, +0.5] | [-0.0, +1.5] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-3.6, -1.1] | [-2.9, -1.2] | [-1.9, -0.6] | [-0.6, +0.3] |

Per class and with every class weighted equally (a report, not a test): accuracy, and the wrong-accept rate when the top 50% of each class is answered.

| Class | Problems | pipeline k=3: acc / WAR | B2: acc / WAR | pipeline k=1 + B2: acc / WAR | pipeline k=2 + B2: acc / WAR | ceiling: pipeline k=3 + all of B2: acc / WAR |
|---|---|---|---|---|---|---|
| BinPacking | 590 | 99.0% / 0.0% | 99.8% / 0.0% | 99.0% / 0.0% | 99.0% / 0.0% | 99.0% / 0.0% |
| Inventory | 100 | 35.0% / 51.0% | 39.0% / 55.3% | 35.0% / 50.0% | 35.0% / 47.0% | 35.0% / 44.0% |
| JobShop | 130 | 87.7% / 0.0% | 93.8% / 0.0% | 87.7% / 0.0% | 87.7% / 0.0% | 87.7% / 0.0% |
| Knapsack | 230 | 91.3% / 7.3% | 91.7% / 6.8% | 91.3% / 7.0% | 91.3% / 6.9% | 91.3% / 7.2% |
| NetworkFlow | 27 | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% |
| Pollution | 50 | 2.0% / 100.0% | 0.0% / 100.0% | 2.0% / 100.0% | 2.0% / 100.0% | 2.0% / 100.0% |
| Portfolio | 130 | 89.2% / 6.7% | 90.0% / 8.3% | 89.2% / 6.7% | 89.2% / 6.7% | 89.2% / 7.7% |
| Production | 50 | 82.0% / 17.4% | 82.0% / 7.7% | 82.0% / 13.3% | 82.0% / 17.4% | 82.0% / 2.9% |
| TSP | 100 | 82.0% / 0.0% | 98.0% / 0.0% | 82.0% / 0.0% | 82.0% / 0.0% | 82.0% / 0.0% |
| Transportation | 50 | 98.0% / 0.0% | 100.0% / 0.0% | 98.0% / 0.0% | 98.0% / 0.0% | 98.0% / 0.0% |
| **equal weight** |  | 76.6% / 18.2% | 79.4% / 17.8% | 76.6% / 17.7% | 76.6% / 17.8% | 76.6% / 16.2% |
