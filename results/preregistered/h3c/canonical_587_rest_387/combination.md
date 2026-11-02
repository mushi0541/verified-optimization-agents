# The pipeline combined with B2 (387 problems)

Budget: 21,723 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 21,723 | 74.4% | 0.824 | 8.8% | 8.9% | 11.5% | 18.3% |
| B2 | 21,750 | 78.0% | 0.891 | 4.3% | 4.3% | 7.6% | 15.9% |
| pipeline k=1 + B2 | 21,709 | 74.4% | 0.850 | 7.2% | 7.9% | 10.6% | 17.5% |
| pipeline k=2 + B2 | 21,908 | 74.4% | 0.828 | 9.3% | 8.9% | 10.3% | 17.5% |
| ceiling: pipeline k=3 + all of B2 | 49,307 | 74.4% | 0.915 | 3.6% | 5.2% | 10.6% | 17.5% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-0.1, +7.0] | [+1.2, +6.3] | [+0.5, +5.2] | [-0.7, +4.5] |
| pipeline k=1 + B2 minus pipeline k=3 | [-3.7, +1.0] | [-3.1, +0.8] | [-2.6, +1.0] | [-1.5, +0.3] |
| pipeline k=2 + B2 minus B2 | [+1.2, +9.1] | [+1.7, +7.6] | [+0.2, +4.7] | [-1.1, +4.5] |
| pipeline k=2 + B2 minus pipeline k=3 | [-1.5, +2.8] | [-1.8, +1.8] | [-2.6, +0.8] | [-1.7, +0.0] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-2.6, +0.9] | [-1.0, +2.8] | [+0.7, +5.2] | [-0.6, +4.8] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-9.3, -2.1] | [-5.9, -1.5] | [-2.3, +0.6] | [-1.5, +0.1] |
