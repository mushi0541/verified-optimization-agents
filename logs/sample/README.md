# Sample traces

Ten real traces from one pipeline run on the development split (`samples/dev_30.json`), made with:

    python -m optverify.run pipeline --model bedrock:openai.gpt-oss-120b-1:0 --sample-file samples/dev_30.json --repairs 1 --paraphrases 3 --threshold 0.8 --workers 4 --trace

The run had k = 3 reworded runs, r = 1 repair and a fixed threshold of 0.8, with 0 failed problems out of 30. Each
file has one JSON line per step (`parser`, `formalizer`, `solver`, `repair`, `paraphrase_<j>`, `verifier`, `decision`,
`explainer`), as described in the README section "Observability". These are development problems, never test problems.

| File | Class | Decision | Correct | What it shows |
|---|---|---|---|---|
| `canonical-1155.jsonl` | Knapsack | answer | yes | Every signal passes (score 1.0). |
| `canonical-1731.jsonl` | Transportation | answer | yes | Every signal passes (score 1.0). |
| `canonical-1250.jsonl` | Portfolio | answer | yes | The first code ends in an error and one repair fixes it; one unused number lowers the score to 0.99. |
| `canonical-1601.jsonl` | Pollution | answer | no | Wrong accept: requirements R3 and R5 have no named constraint, but the score (0.87) still passes 0.8. |
| `canonical-1643.jsonl` | Pollution | answer | no | Wrong accept with requirement coverage 0.5 (score 0.83); all rewordings agree on the same wrong value. |
| `canonical-0695.jsonl` | Inventory | escalate | no | Correct refusal: R7 has no named constraint and the rewordings disagree (1917 against 1921). |
| `canonical-0890.jsonl` | JobShop | escalate | no | Correct refusal: all three rewordings find 54 (the reference), the main model finds 265. |
| `canonical-0652.jsonl` | Inventory | escalate | yes | False alarm: the answer 561 is right, but two rewordings give 555 and R8 is not linked. |
| `canonical-0139.jsonl` | BinPacking | abstain | no | No feasible model after the repair, so the system answers nothing. |
| `canonical-1508.jsonl` | TSP | abstain | no | No feasible model after the repair, so the system answers nothing. |

The two Pollution cases are wrong accepts. They are also in the class whose reference answers we hand-check (#40),
so some of these may turn out to be reference errors rather than model errors.
