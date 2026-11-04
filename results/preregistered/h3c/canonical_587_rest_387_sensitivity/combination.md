# The pipeline combined with B2 (346 problems, without Pollution, canonical-0648)

Budget: 21,378 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 21,378 | 82.9% | 0.835 | 5.1% | 5.0% | 5.1% | 8.9% |
| B2 | 21,341 | 87.3% | 0.908 | 1.8% | 1.8% | 1.8% | 7.1% |
| pipeline k=1 + B2 | 21,380 | 82.9% | 0.882 | 3.5% | 3.7% | 3.2% | 8.7% |
| pipeline k=2 + B2 | 21,591 | 82.9% | 0.845 | 5.1% | 5.0% | 4.3% | 7.7% |
| ceiling: pipeline k=3 + all of B2 | 48,930 | 82.9% | 0.935 | 1.7% | 1.7% | 3.2% | 8.0% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-0.4, +4.0] | [+0.6, +3.8] | [+0.4, +3.2] | [-0.9, +4.6] |
| pipeline k=1 + B2 minus pipeline k=3 | [-3.7, +0.0] | [-2.9, +0.0] | [-2.8, -0.2] | [-1.6, +1.0] |
| pipeline k=2 + B2 minus B2 | [+0.6, +6.2] | [+1.3, +5.2] | [+0.9, +4.3] | [-1.5, +3.9] |
| pipeline k=2 + B2 minus pipeline k=3 | [-1.6, +1.5] | [-1.2, +1.2] | [-1.8, +0.7] | [-2.1, +0.0] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-1.9, +1.1] | [-1.1, +1.4] | [-0.4, +3.2] | [-1.1, +3.7] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-6.6, -0.6] | [-5.4, -1.2] | [-3.6, -0.4] | [-2.0, +0.1] |
