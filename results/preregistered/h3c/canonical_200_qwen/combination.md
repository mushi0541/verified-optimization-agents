# The pipeline combined with B2 (200 problems)

Budget: 24,052 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 24,052 | 68.5% | 0.897 | 3.0% | 13.6% | 16.1% | 23.9% |
| B2 | 24,013 | 80.5% | 0.853 | 3.3% | 6.8% | 9.1% | 14.2% |
| pipeline k=1 + B2 | 23,984 | 68.5% | 0.902 | 5.0% | 10.0% | 15.0% | 23.9% |
| pipeline k=2 + B2 | 24,355 | 68.5% | 0.918 | 3.0% | 8.6% | 15.3% | 23.9% |
| ceiling: pipeline k=3 + all of B2 | 56,135 | 68.5% | 0.930 | 3.3% | 8.6% | 15.0% | 23.9% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-2.0, +5.1] | [-1.0, +6.3] | [+1.5, +11.6] | [+4.9, +13.4] |
| pipeline k=1 + B2 minus pipeline k=3 | [-0.5, +4.0] | [-7.9, +0.7] | [-2.8, +1.7] | [+0.0, +0.6] |
| pipeline k=2 + B2 minus B2 | [-3.1, +3.2] | [-1.0, +5.7] | [+1.2, +11.5] | [+4.4, +14.0] |
| pipeline k=2 + B2 minus pipeline k=3 | [-2.0, +1.0] | [-7.9, +1.4] | [-3.1, +0.6] | [+0.0, +0.0] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-2.5, +2.9] | [-0.7, +5.0] | [+0.9, +11.7] | [+5.1, +13.5] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-3.0, +2.0] | [-7.9, -0.6] | [-3.1, +1.3] | [+0.0, +0.0] |
