# Exploratory: the pipeline combined with B2 (200 problems)

Budget: 20,783 tokens per problem (the pipeline at k = 3). Not pre-registered.

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 20,783 | 78.0% | 0.860 | 6.0% | 5.5% | 7.5% | 13.4% |
| B2 | 20,881 | 80.5% | 0.842 | 6.3% | 6.3% | 6.2% | 12.9% |
| pipeline k=1 + B2 | 20,837 | 78.0% | 0.862 | 5.0% | 5.4% | 8.3% | 14.4% |
| pipeline k=2 + B2 | 20,750 | 78.0% | 0.874 | 5.0% | 4.9% | 8.1% | 13.3% |
| ceiling: pipeline k=3 + all of B2 | 43,002 | 78.0% | 0.897 | 4.0% | 3.6% | 8.8% | 14.4% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-5.8, +2.7] | [-3.9, +2.0] | [-1.6, +6.0] | [-2.0, +4.9] |
| pipeline k=1 + B2 minus pipeline k=3 | [-3.7, +0.0] | [-2.2, +1.8] | [-2.0, +4.3] | [-0.1, +3.3] |
| pipeline k=2 + B2 minus B2 | [-5.9, +3.2] | [-5.0, +2.0] | [-2.5, +4.8] | [-2.6, +4.4] |
| pipeline k=2 + B2 minus pipeline k=3 | [-3.0, +0.0] | [-2.4, +0.2] | [-2.5, +3.1] | [-0.6, +1.7] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-6.2, +0.8] | [-5.2, +0.4] | [-2.1, +5.6] | [-1.7, +5.0] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-6.0, +1.0] | [-4.3, +0.9] | [-2.5, +3.8] | [-0.2, +2.8] |
