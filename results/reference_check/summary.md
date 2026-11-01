# Reference check (Pollution and Inventory)

Each question's data is read from its text and the model the text states is solved with HiGHS. A reference
counts as reproduced within the grading tolerance (0.2%). Made by `scripts/check_references.py`.

| Class | Problems | Checked | Reference reproduced | Pipeline answers | Pipeline = reference | Pipeline = a stated reading only |
|---|---|---|---|---|---|---|
| Pollution | 80 | 73 | 0 | 21 | 0 | 7 |
| Inventory | 160 | 117 | 106 | 16 | 9 | 5 |

Inventory references reproduced by each capacity reading: capacity also after arrival: 106, capacity at end of period: 59.
