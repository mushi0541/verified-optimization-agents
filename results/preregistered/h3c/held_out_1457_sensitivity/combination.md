# The pipeline combined with B2 (1406 problems, without Pollution, canonical-0648)

Budget: 17,172 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 17,172 | 89.5% | 0.770 | 5.1% | 4.1% | 3.6% | 3.5% |
| B2 | 17,144 | 92.0% | 0.842 | 2.5% | 2.5% | 2.5% | 2.8% |
| pipeline k=1 + B2 | 17,184 | 89.5% | 0.800 | 4.7% | 3.5% | 3.0% | 3.2% |
| pipeline k=2 + B2 | 17,260 | 89.5% | 0.784 | 5.0% | 3.8% | 3.3% | 3.7% |
| ceiling: pipeline k=3 + all of B2 | 44,469 | 89.5% | 0.836 | 3.8% | 2.7% | 2.7% | 3.0% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [+1.1, +3.0] | [+0.4, +1.5] | [+0.1, +1.0] | [-0.1, +1.1] |
| pipeline k=1 + B2 minus pipeline k=3 | [-1.3, +0.2] | [-1.2, -0.1] | [-1.1, -0.1] | [-0.8, +0.2] |
| pipeline k=2 + B2 minus B2 | [+1.4, +3.4] | [+0.6, +1.9] | [+0.2, +1.4] | [+0.3, +1.5] |
| pipeline k=2 + B2 minus pipeline k=3 | [-0.9, +0.3] | [-0.8, +0.1] | [-0.7, +0.1] | [-0.5, +0.7] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [+0.6, +2.1] | [-0.2, +0.7] | [-0.3, +0.7] | [-0.1, +0.9] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-2.4, -0.1] | [-2.0, -0.6] | [-1.4, -0.4] | [-0.8, +0.0] |
