# The pipeline combined with B2 (180 problems, without Pollution)

Budget: 15,606 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 15,606 | 87.8% | 0.740 | 4.9% | 5.6% | 4.9% | 4.9% |
| B2 | 15,604 | 92.2% | 0.650 | 4.8% | 4.8% | 4.8% | 6.2% |
| pipeline k=1 + B2 | 15,671 | 87.8% | 0.728 | 5.1% | 5.6% | 4.9% | 5.6% |
| pipeline k=2 + B2 | 15,556 | 87.8% | 0.737 | 4.9% | 5.6% | 4.9% | 5.2% |
| ceiling: pipeline k=3 + all of B2 | 36,900 | 87.8% | 0.759 | 4.2% | 4.8% | 4.9% | 4.9% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-3.0, +3.3] | [-1.5, +2.7] | [-2.0, +1.8] | [-1.9, +1.9] |
| pipeline k=1 + B2 minus pipeline k=3 | [+0.0, +0.6] | [+0.0, +0.8] | [+0.0, +0.3] | [-1.2, +2.5] |
| pipeline k=2 + B2 minus B2 | [-3.0, +3.3] | [-1.6, +3.1] | [-2.3, +2.1] | [-2.5, +1.2] |
| pipeline k=2 + B2 minus pipeline k=3 | [+0.0, +0.2] | [+0.0, +0.8] | [+0.0, +0.0] | [-1.2, +1.9] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-3.5, +1.8] | [-1.9, +1.6] | [-2.1, +2.1] | [-2.5, +0.0] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-3.0, +0.6] | [-2.4, +0.8] | [+0.0, +0.7] | [-1.9, +1.9] |
