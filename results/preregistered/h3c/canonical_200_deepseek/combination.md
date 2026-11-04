# The pipeline combined with B2 (200 problems)

Budget: 15,848 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 15,848 | 79.0% | 0.728 | 10.1% | 10.0% | 13.1% | 13.9% |
| B2 | 15,917 | 83.0% | 0.750 | 8.0% | 8.0% | 9.4% | 12.6% |
| pipeline k=1 + B2 | 15,881 | 79.0% | 0.756 | 9.6% | 9.3% | 8.9% | 13.3% |
| pipeline k=2 + B2 | 15,854 | 79.0% | 0.753 | 9.3% | 9.3% | 10.5% | 13.9% |
| ceiling: pipeline k=3 + all of B2 | 37,199 | 79.0% | 0.799 | 7.0% | 8.6% | 10.0% | 13.9% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-3.0, +5.9] | [-1.9, +4.5] | [-2.5, +2.5] | [-1.3, +4.2] |
| pipeline k=1 + B2 minus pipeline k=3 | [-2.4, +0.8] | [-2.9, +0.0] | [-6.2, +0.0] | [-2.2, +1.7] |
| pipeline k=2 + B2 minus B2 | [-3.3, +5.7] | [-1.7, +4.5] | [-1.5, +4.4] | [-1.1, +3.9] |
| pipeline k=2 + B2 minus pipeline k=3 | [-2.9, +0.2] | [-2.1, +0.1] | [-5.0, +0.6] | [-2.2, +1.7] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-4.5, +1.9] | [-1.8, +2.4] | [-2.1, +2.5] | [-1.7, +3.8] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-6.9, +0.1] | [-4.5, +0.7] | [-5.6, +0.0] | [-2.2, +1.1] |
