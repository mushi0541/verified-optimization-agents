# The pipeline combined with B2 (200 problems)

Budget: 15,630 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 15,630 | 73.0% | 0.815 | 5.6% | 8.2% | 13.1% | 18.0% |
| B2 | 15,657 | 75.5% | 0.759 | 8.0% | 13.9% | 15.9% | 20.0% |
| pipeline k=1 + B2 | 15,641 | 73.0% | 0.770 | 7.0% | 10.0% | 14.4% | 18.0% |
| pipeline k=2 + B2 | 15,887 | 73.0% | 0.763 | 8.0% | 10.1% | 13.0% | 18.0% |
| ceiling: pipeline k=3 + all of B2 | 36,630 | 73.0% | 0.803 | 7.0% | 9.6% | 13.1% | 18.0% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-4.7, +2.1] | [-7.2, -0.2] | [-5.6, +2.5] | [-7.0, +2.6] |
| pipeline k=1 + B2 minus pipeline k=3 | [-2.5, +5.3] | [-1.1, +5.0] | [-1.0, +3.1] | [-0.3, +0.3] |
| pipeline k=2 + B2 minus B2 | [-4.6, +4.8] | [-7.9, -0.9] | [-6.8, +1.3] | [-7.4, +2.7] |
| pipeline k=2 + B2 minus pipeline k=3 | [-1.7, +7.0] | [-2.1, +4.9] | [-1.9, +1.0] | [-0.3, +0.0] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-4.7, +2.0] | [-8.4, -1.2] | [-7.1, +0.7] | [-7.6, +2.6] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-3.3, +6.0] | [-2.2, +5.0] | [-2.7, +1.9] | [-1.6, +0.0] |
