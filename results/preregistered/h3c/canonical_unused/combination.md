# The pipeline combined with B2 (1070 problems)

Budget: 15,903 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 15,903 | 90.7% | 0.741 | 5.6% | 4.0% | 3.5% | 3.1% |
| B2 | 15,925 | 92.4% | 0.814 | 2.8% | 2.8% | 2.8% | 2.8% |
| pipeline k=1 + B2 | 15,866 | 90.7% | 0.766 | 4.9% | 3.5% | 3.0% | 2.9% |
| pipeline k=2 + B2 | 16,008 | 90.7% | 0.759 | 5.0% | 3.6% | 3.2% | 2.9% |
| ceiling: pipeline k=3 + all of B2 | 43,125 | 90.7% | 0.784 | 4.5% | 3.2% | 2.8% | 2.8% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [+1.1, +3.2] | [+0.1, +1.3] | [-0.2, +0.8] | [-0.3, +0.7] |
| pipeline k=1 + B2 minus pipeline k=3 | [-1.5, -0.1] | [-1.1, -0.1] | [-0.9, -0.1] | [-0.7, +0.3] |
| pipeline k=2 + B2 minus B2 | [+1.3, +3.3] | [+0.2, +1.5] | [-0.1, +0.9] | [-0.3, +1.0] |
| pipeline k=2 + B2 minus pipeline k=3 | [-1.3, +0.0] | [-0.9, +0.0] | [-0.8, +0.0] | [-0.5, +0.7] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [+0.8, +2.8] | [-0.1, +1.0] | [-0.4, +0.6] | [-0.4, +0.6] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-2.1, -0.2] | [-1.5, -0.3] | [-1.2, -0.2] | [-0.7, +0.2] |

Per class and with every class weighted equally (a report, not a test): accuracy, and the wrong-accept rate when the top 50% of each class is answered.

| Class | Problems | pipeline k=3: acc / WAR | B2: acc / WAR | pipeline k=1 + B2: acc / WAR | pipeline k=2 + B2: acc / WAR | ceiling: pipeline k=3 + all of B2: acc / WAR |
|---|---|---|---|---|---|---|
| BinPacking | 550 | 98.9% / 0.0% | 99.8% / 0.0% | 98.9% / 0.0% | 98.9% / 0.0% | 98.9% / 0.0% |
| Inventory | 60 | 35.0% / 50.0% | 41.7% / 54.6% | 35.0% / 53.3% | 35.0% / 56.7% | 35.0% / 46.7% |
| JobShop | 90 | 92.2% / 0.0% | 93.3% / 0.0% | 92.2% / 0.0% | 92.2% / 0.0% | 92.2% / 0.0% |
| Knapsack | 190 | 90.5% / 8.2% | 91.1% / 7.7% | 90.5% / 7.9% | 90.5% / 7.8% | 90.5% / 8.1% |
| Pollution | 10 | 0.0% / 100.0% | 0.0% / 100.0% | 0.0% / 100.0% | 0.0% / 100.0% | 0.0% / 100.0% |
| Portfolio | 90 | 87.8% / 6.7% | 88.9% / 8.4% | 87.8% / 6.7% | 87.8% / 6.7% | 87.8% / 6.7% |
| Production | 10 | 90.0% / 11.1% | 90.0% / 11.1% | 90.0% / 11.1% | 90.0% / 11.1% | 90.0% / 11.1% |
| TSP | 60 | 88.3% / 0.0% | 98.3% / 0.0% | 88.3% / 0.0% | 88.3% / 0.0% | 88.3% / 0.0% |
| Transportation | 10 | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% |
| **equal weight** |  | 75.9% / 19.6% | 78.1% / 20.2% | 75.9% / 19.9% | 75.9% / 20.2% | 75.9% / 19.2% |
