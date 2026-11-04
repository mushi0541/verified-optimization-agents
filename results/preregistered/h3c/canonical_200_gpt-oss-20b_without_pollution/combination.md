# The pipeline combined with B2 (180 problems, without Pollution)

Budget: 25,312 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 25,312 | 72.8% | 0.721 | 3.3% | 4.8% | 6.4% | 6.4% |
| B2 | 25,226 | 91.7% | 0.697 | 4.3% | 4.0% | 4.2% | 4.9% |
| pipeline k=1 + B2 | 25,436 | 72.8% | 0.785 | 3.3% | 4.0% | 6.4% | 6.4% |
| pipeline k=2 + B2 | 26,093 | 72.8% | 0.727 | 3.3% | 4.0% | 6.4% | 6.4% |
| ceiling: pipeline k=3 + all of B2 | 60,059 | 72.8% | 0.787 | 2.2% | 3.2% | 6.4% | 6.4% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-4.7, +2.1] | [-3.2, +2.8] | [-1.4, +5.1] | [-1.6, +4.6] |
| pipeline k=1 + B2 minus pipeline k=3 | [-3.3, +3.3] | [-3.2, +0.0] | [-0.7, +0.7] | [+0.0, +0.0] |
| pipeline k=2 + B2 minus B2 | [-4.7, +3.3] | [-3.2, +3.2] | [-1.4, +5.6] | [-1.7, +4.6] |
| pipeline k=2 + B2 minus pipeline k=3 | [+0.0, +2.2] | [-2.4, +0.0] | [+0.0, +0.0] | [+0.0, +0.0] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-5.0, +0.8] | [-3.2, +2.4] | [-1.4, +5.1] | [-1.5, +4.8] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-4.4, +2.2] | [-3.2, +0.0] | [-0.7, +0.0] | [+0.0, +0.0] |
