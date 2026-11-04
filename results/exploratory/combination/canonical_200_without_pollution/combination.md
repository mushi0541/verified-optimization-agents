# The pipeline combined with B2 (180 problems, without Pollution)

Budget: 20,187 tokens per problem (the pipeline at k = 3). Exploratory: not pre-registered.

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 20,187 | 86.7% | 0.768 | 4.4% | 4.8% | 4.2% | 6.0% |
| B2 | 20,248 | 89.4% | 0.813 | 3.9% | 3.9% | 3.9% | 5.6% |
| pipeline k=1 + B2 | 20,251 | 86.7% | 0.801 | 3.3% | 4.0% | 3.5% | 6.8% |
| pipeline k=2 + B2 | 20,205 | 86.7% | 0.767 | 4.4% | 4.8% | 4.2% | 6.5% |
| ceiling: pipeline k=3 + all of B2 | 42,366 | 86.7% | 0.831 | 2.2% | 3.2% | 4.2% | 7.4% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-3.9, +3.3] | [-2.5, +2.4] | [-2.0, +2.1] | [-0.6, +4.3] |
| pipeline k=1 + B2 minus pipeline k=3 | [-3.3, +0.1] | [-3.2, +0.0] | [-2.1, +1.4] | [-0.6, +2.5] |
| pipeline k=2 + B2 minus B2 | [-3.3, +5.0] | [-2.0, +4.0] | [-1.8, +3.5] | [-1.6, +3.8] |
| pipeline k=2 + B2 minus pipeline k=3 | [+0.0, +0.0] | [+0.0, +0.0] | [-0.7, +1.2] | [-0.8, +1.4] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-4.1, +1.9] | [-3.1, +0.9] | [-2.1, +1.5] | [-0.6, +4.6] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-5.3, +1.1] | [-4.0, +0.0] | [-2.8, +1.5] | [-0.6, +2.5] |
