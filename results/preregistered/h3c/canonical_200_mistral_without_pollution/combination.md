# The pipeline combined with B2 (180 problems, without Pollution)

Budget: 16,961 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 16,961 | 78.9% | 0.829 | 5.6% | 5.9% | 6.9% | 13.6% |
| B2 | 16,934 | 87.8% | 0.780 | 4.7% | 4.7% | 5.6% | 7.4% |
| pipeline k=1 + B2 | 17,032 | 78.9% | 0.814 | 7.8% | 5.6% | 6.2% | 12.3% |
| pipeline k=2 + B2 | 17,013 | 78.9% | 0.802 | 7.8% | 6.3% | 6.9% | 13.0% |
| ceiling: pipeline k=3 + all of B2 | 40,401 | 78.9% | 0.871 | 3.3% | 5.6% | 5.6% | 12.3% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-0.2, +7.0] | [-1.9, +4.0] | [-1.4, +4.9] | [+0.0, +10.1] |
| pipeline k=1 + B2 minus pipeline k=3 | [+0.0, +5.6] | [-2.0, +0.0] | [-2.1, +2.1] | [-2.5, +0.0] |
| pipeline k=2 + B2 minus B2 | [-0.2, +7.0] | [-1.5, +4.8] | [-0.7, +5.1] | [+0.6, +10.2] |
| pipeline k=2 + B2 minus pipeline k=3 | [+0.0, +5.6] | [+0.0, +2.1] | [-1.4, +2.8] | [-1.9, +0.0] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-4.8, +3.4] | [-1.9, +3.8] | [-2.1, +3.5] | [-0.2, +10.1] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-5.6, +2.4] | [-2.0, +0.0] | [-2.8, +0.1] | [-2.9, +0.0] |
