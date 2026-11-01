# Reference check (Pollution and Inventory)

Each question's data is read from its text and the model the text states is solved with HiGHS. A reference
counts as reproduced within the grading tolerance (0.2%). Made by `scripts/check_references.py`.

| Class | Problems | Checked | Reference reproduced | Pipeline answers | Pipeline = reference | Pipeline = a stated reading only |
|---|---|---|---|---|---|---|
| Pollution | 80 | 73 | 0 | 21 | 0 | 7 |
| Inventory | 160 | 125 | 122 | 19 | 10 | 7 |

Inventory references reproduced by each capacity reading: capacity at end of period: 69, capacity also after arrival: 122.
