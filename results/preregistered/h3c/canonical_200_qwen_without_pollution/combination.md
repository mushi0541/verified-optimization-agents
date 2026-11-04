# The pipeline combined with B2 (180 problems, without Pollution)

Budget: 22,764 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 22,764 | 76.1% | 0.866 | 2.2% | 7.1% | 8.1% | 15.4% |
| B2 | 22,635 | 89.4% | 0.758 | 4.1% | 4.0% | 4.7% | 6.5% |
| pipeline k=1 + B2 | 22,757 | 76.1% | 0.868 | 4.4% | 4.0% | 7.6% | 15.4% |
| pipeline k=2 + B2 | 23,172 | 76.1% | 0.895 | 2.2% | 4.8% | 6.9% | 15.4% |
| ceiling: pipeline k=3 + all of B2 | 54,698 | 76.1% | 0.894 | 2.2% | 5.3% | 7.6% | 15.4% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-3.0, +3.3] | [-2.0, +2.4] | [-0.7, +8.3] | [+3.6, +13.1] |
| pipeline k=1 + B2 minus pipeline k=3 | [+0.0, +4.4] | [-7.1, +0.8] | [-4.2, +1.7] | [+0.0, +1.2] |
| pipeline k=2 + B2 minus B2 | [-4.4, +1.1] | [-1.6, +3.2] | [-0.7, +7.2] | [+3.1, +12.9] |
| pipeline k=2 + B2 minus pipeline k=3 | [-0.1, +1.1] | [-6.3, +0.8] | [-4.2, +0.6] | [+0.0, +0.0] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-5.5, +0.7] | [-1.5, +4.0] | [+0.6, +8.1] | [+3.5, +13.0] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-3.3, +2.2] | [-5.6, +0.8] | [-2.8, +1.4] | [+0.0, +0.0] |
