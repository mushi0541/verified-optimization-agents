# The pipeline combined with B2 (347 problems, without Pollution)

Budget: 21,366 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 21,366 | 82.7% | 0.837 | 5.1% | 4.9% | 5.0% | 9.2% |
| B2 | 21,327 | 87.0% | 0.910 | 1.8% | 1.8% | 1.8% | 7.4% |
| pipeline k=1 + B2 | 21,372 | 82.7% | 0.883 | 3.4% | 3.7% | 3.4% | 9.0% |
| pipeline k=2 + B2 | 21,575 | 82.7% | 0.848 | 5.1% | 4.9% | 4.3% | 8.0% |
| ceiling: pipeline k=3 + all of B2 | 48,920 | 82.7% | 0.936 | 1.7% | 1.6% | 3.6% | 8.3% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-0.5, +4.1] | [+0.5, +3.6] | [+0.4, +3.3] | [-0.6, +4.5] |
| pipeline k=1 + B2 minus pipeline k=3 | [-3.9, +0.0] | [-2.9, +0.0] | [-2.9, -0.2] | [-1.6, +0.9] |
| pipeline k=2 + B2 minus B2 | [+0.5, +6.1] | [+1.2, +5.3] | [+0.7, +4.3] | [-1.6, +3.7] |
| pipeline k=2 + B2 minus pipeline k=3 | [-1.6, +1.6] | [-1.2, +1.2] | [-2.2, +0.7] | [-2.2, +0.0] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-1.6, +1.0] | [-0.9, +1.4] | [-0.3, +3.3] | [-1.3, +4.1] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-6.5, -0.6] | [-5.3, -0.8] | [-3.6, -0.4] | [-1.9, +0.1] |
