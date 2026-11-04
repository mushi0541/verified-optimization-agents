# The pipeline combined with B2 (1407 problems, without Pollution)

Budget: 17,172 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 17,172 | 89.4% | 0.772 | 5.1% | 4.1% | 3.6% | 3.6% |
| B2 | 17,144 | 91.9% | 0.843 | 2.5% | 2.5% | 2.5% | 2.8% |
| pipeline k=1 + B2 | 17,185 | 89.4% | 0.801 | 4.7% | 3.5% | 3.0% | 3.3% |
| pipeline k=2 + B2 | 17,261 | 89.4% | 0.786 | 5.0% | 3.8% | 3.3% | 3.7% |
| ceiling: pipeline k=3 + all of B2 | 44,470 | 89.4% | 0.838 | 3.8% | 2.7% | 2.7% | 3.1% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [+1.2, +3.0] | [+0.5, +1.5] | [+0.1, +1.0] | [-0.0, +1.1] |
| pipeline k=1 + B2 minus pipeline k=3 | [-1.3, +0.2] | [-1.2, -0.1] | [-1.1, -0.1] | [-0.8, +0.2] |
| pipeline k=2 + B2 minus B2 | [+1.4, +3.5] | [+0.7, +1.9] | [+0.3, +1.4] | [+0.3, +1.5] |
| pipeline k=2 + B2 minus pipeline k=3 | [-0.9, +0.4] | [-0.8, +0.1] | [-0.7, +0.1] | [-0.5, +0.7] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [+0.6, +2.1] | [-0.2, +0.7] | [-0.3, +0.7] | [-0.2, +0.9] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-2.4, -0.3] | [-2.0, -0.6] | [-1.4, -0.4] | [-0.9, -0.0] |
