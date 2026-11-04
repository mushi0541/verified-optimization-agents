# The pipeline combined with B2 (1060 problems, without Pollution)

Budget: 15,799 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 15,799 | 91.6% | 0.729 | 5.3% | 3.8% | 3.3% | 2.9% |
| B2 | 15,813 | 93.3% | 0.812 | 2.5% | 2.5% | 2.5% | 2.5% |
| pipeline k=1 + B2 | 15,771 | 91.6% | 0.757 | 4.5% | 3.2% | 2.8% | 2.5% |
| pipeline k=2 + B2 | 15,913 | 91.6% | 0.749 | 4.7% | 3.4% | 2.9% | 2.6% |
| ceiling: pipeline k=3 + all of B2 | 43,013 | 91.6% | 0.767 | 4.3% | 3.1% | 2.7% | 2.6% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [+1.2, +3.0] | [+0.3, +1.2] | [+0.0, +0.7] | [-0.2, +0.5] |
| pipeline k=1 + B2 minus pipeline k=3 | [-1.5, -0.1] | [-1.1, -0.1] | [-0.9, -0.1] | [-0.8, +0.0] |
| pipeline k=2 + B2 minus B2 | [+1.3, +3.3] | [+0.4, +1.5] | [+0.1, +0.9] | [-0.2, +0.7] |
| pipeline k=2 + B2 minus pipeline k=3 | [-1.3, +0.0] | [-0.9, +0.0] | [-0.8, +0.0] | [-0.7, +0.3] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [+1.0, +2.8] | [+0.1, +1.2] | [-0.1, +0.7] | [-0.2, +0.6] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-1.7, -0.2] | [-1.3, -0.1] | [-1.1, -0.1] | [-0.6, +0.1] |
