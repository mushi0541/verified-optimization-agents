# The pipeline combined with B2 (180 problems, without Pollution)

Budget: 15,494 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 15,494 | 81.1% | 0.839 | 1.9% | 3.2% | 5.6% | 9.3% |
| B2 | 15,518 | 83.9% | 0.777 | 5.4% | 5.5% | 7.5% | 11.1% |
| pipeline k=1 + B2 | 15,574 | 81.1% | 0.729 | 4.4% | 4.8% | 6.2% | 9.3% |
| pipeline k=2 + B2 | 15,765 | 81.1% | 0.753 | 4.2% | 4.8% | 4.9% | 9.3% |
| ceiling: pipeline k=3 + all of B2 | 36,470 | 81.1% | 0.774 | 4.4% | 4.8% | 5.6% | 9.3% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-3.3, +0.4] | [-4.8, +0.0] | [-4.7, +2.3] | [-7.2, +2.7] |
| pipeline k=1 + B2 minus pipeline k=3 | [+0.1, +6.7] | [-0.8, +4.0] | [-1.5, +2.9] | [+0.0, +0.8] |
| pipeline k=2 + B2 minus B2 | [-4.4, +0.2] | [-4.8, +0.0] | [-5.5, +1.7] | [-7.0, +2.9] |
| pipeline k=2 + B2 minus pipeline k=3 | [+0.1, +5.7] | [-1.5, +4.0] | [-2.1, +1.0] | [-0.0, +0.2] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-4.9, +1.5] | [-4.8, +0.0] | [-6.1, +0.3] | [-7.8, +2.8] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [+0.1, +6.8] | [-1.6, +4.0] | [-2.8, +0.5] | [-1.9, +0.0] |
