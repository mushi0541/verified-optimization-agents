# The pipeline combined with B2 (200 problems)

Budget: 17,511 tokens per problem (the pipeline at k = 3). Pre-registered test (#103, docs/preregistration_combination.md).

| System | Tokens | Accuracy | AUROC | WAR at 50% | WAR at 70% | WAR at 80% | WAR at 90% |
|---|---|---|---|---|---|---|---|
| pipeline k=3 | 17,511 | 71.0% | 0.861 | 5.6% | 8.6% | 13.1% | 22.2% |
| B2 | 17,596 | 79.0% | 0.798 | 7.6% | 8.6% | 10.8% | 16.4% |
| pipeline k=1 + B2 | 17,471 | 71.0% | 0.831 | 8.4% | 11.4% | 14.4% | 21.1% |
| pipeline k=2 + B2 | 17,538 | 71.0% | 0.829 | 8.4% | 9.9% | 15.0% | 21.7% |
| ceiling: pipeline k=3 + all of B2 | 41,045 | 71.0% | 0.900 | 6.0% | 7.1% | 13.1% | 21.1% |

Paired 95% intervals of the wrong-accept difference (points):

| Comparison | at 50% | at 70% | at 80% | at 90% |
|---|---|---|---|---|
| pipeline k=1 + B2 minus B2 | [-3.7, +5.4] | [-1.4, +6.2] | [+0.4, +8.1] | [+0.4, +9.7] |
| pipeline k=1 + B2 minus pipeline k=3 | [-2.0, +6.0] | [-1.4, +5.4] | [-1.5, +3.7] | [-2.5, +0.0] |
| pipeline k=2 + B2 minus B2 | [-3.5, +5.5] | [-1.8, +6.4] | [+0.8, +7.7] | [+0.6, +9.6] |
| pipeline k=2 + B2 minus pipeline k=3 | [-1.8, +6.0] | [-1.4, +5.0] | [-1.9, +4.4] | [-1.7, +0.6] |
| ceiling: pipeline k=3 + all of B2 minus B2 | [-6.9, +2.3] | [-3.6, +2.9] | [-1.3, +6.9] | [+0.4, +9.8] |
| ceiling: pipeline k=3 + all of B2 minus pipeline k=3 | [-4.7, +3.1] | [-4.0, +1.4] | [-2.5, +1.9] | [-2.2, +0.0] |
