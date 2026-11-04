# The pipeline combined with B2 (200 problems)

Budget: 26,013 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 26,013 | 65.5% | 0.771 | 6.0% | 7.9% | 12.7% | 12.7% |
| B2 | 26,058 | 82.5% | 0.792 | 5.3% | 5.0% | 10.8% | 14.4% |
| pipeline k=1 + B2 | 26,146 | 65.5% | 0.822 | 5.0% | 9.1% | 12.7% | 12.7% |
| pipeline k=2 + B2 | 26,922 | 65.5% | 0.773 | 7.0% | 9.3% | 12.7% | 12.7% |
| ceiling: pipeline k=3 + all of B2 | 60,891 | 65.5% | 0.876 | 3.0% | 7.1% | 12.7% | 12.7% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-4.4, +3.3] | [+0.0, +8.6] | [-2.4, +7.0] | [-5.9, +2.7] |
| pipeline k=1 + B2 minus pipeline k=3 | [-5.0, +2.0] | [-2.1, +2.9] | [+0.0, +0.0] | [+0.0, +0.0] |
| pipeline k=2 + B2 minus B2 | [-3.7, +5.5] | [-0.3, +8.6] | [-2.3, +7.0] | [-5.7, +2.4] |
| pipeline k=2 + B2 minus pipeline k=3 | [-3.0, +3.0] | [-2.1, +3.6] | [+0.0, +0.0] | [+0.0, +0.0] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-5.8, +1.0] | [-1.4, +8.2] | [-1.9, +6.9] | [-5.6, +2.6] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-7.0, +1.0] | [-4.3, +1.4] | [+0.0, +0.0] | [+0.0, +0.0] |
