# The pipeline combined with B2 (180 problems, without Pollution)

Budget: 18,212 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 18,212 | 91.7% | 0.703 | 4.1% | 4.8% | 4.2% | 4.6% |
| B2 | 18,246 | 92.8% | 0.619 | 5.2% | 5.2% | 5.2% | 4.9% |
| pipeline k=1 + B2 | 18,182 | 91.7% | 0.753 | 3.2% | 4.0% | 3.5% | 4.0% |
| pipeline k=2 + B2 | 18,250 | 91.7% | 0.695 | 4.3% | 4.8% | 4.2% | 4.9% |
| ceiling: pipeline k=3 + all of B2 | 42,332 | 91.7% | 0.772 | 2.2% | 3.2% | 4.2% | 4.9% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-5.4, +0.9] | [-3.9, +0.8] | [-3.6, +0.2] | [-2.5, +0.6] |
| pipeline k=1 + B2 minus pipeline k=3 | [-3.3, +0.2] | [-2.4, +0.0] | [-2.1, +1.4] | [-2.5, +0.7] |
| pipeline k=2 + B2 minus B2 | [-4.9, +2.6] | [-3.2, +2.3] | [-3.3, +1.7] | [-1.9, +1.9] |
| pipeline k=2 + B2 minus pipeline k=3 | [+0.0, +0.4] | [+0.0, +0.8] | [+0.0, +1.4] | [-1.2, +1.4] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-6.5, +0.1] | [-4.7, +0.3] | [-3.5, +0.7] | [-1.9, +1.9] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-5.2, +0.4] | [-4.0, +0.0] | [-2.1, +2.1] | [-1.9, +1.4] |
