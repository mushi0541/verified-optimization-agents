# The pipeline combined with B2 (200 problems)

Budget: 18,293 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 18,293 | 82.5% | 0.746 | 7.9% | 7.1% | 9.0% | 13.3% |
| B2 | 18,307 | 83.5% | 0.695 | 9.9% | 9.9% | 9.9% | 12.5% |
| pipeline k=1 + B2 | 18,267 | 82.5% | 0.708 | 9.9% | 8.7% | 9.4% | 12.5% |
| pipeline k=2 + B2 | 18,318 | 82.5% | 0.716 | 9.0% | 8.0% | 9.4% | 13.3% |
| ceiling: pipeline k=3 + all of B2 | 42,408 | 82.5% | 0.805 | 4.0% | 6.6% | 9.6% | 11.1% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-5.0, +5.1] | [-4.6, +2.6] | [-3.7, +2.7] | [-2.4, +1.9] |
| pipeline k=1 + B2 minus pipeline k=3 | [-1.5, +5.8] | [-0.9, +4.3] | [-2.2, +3.1] | [-3.1, +1.7] |
| pipeline k=2 + B2 minus B2 | [-6.0, +4.3] | [-5.6, +2.2] | [-3.9, +3.4] | [-1.7, +2.7] |
| pipeline k=2 + B2 minus pipeline k=3 | [+0.0, +3.0] | [+0.0, +2.6] | [-1.5, +3.3] | [-2.2, +2.2] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-9.7, -1.4] | [-6.6, +0.6] | [-3.4, +2.5] | [-3.0, +1.3] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-7.4, +0.0] | [-4.3, +2.9] | [-1.5, +2.6] | [-3.9, +1.1] |
