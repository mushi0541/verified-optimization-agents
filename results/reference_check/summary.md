# Reference check (Pollution and Inventory)

Each question's data is read from its text and the model the text states is solved with HiGHS. A reference
counts as reproduced within the grading tolerance (0.2%). Made by `scripts/check_references.py`.

| Class | Problems | Checked | Reference reproduced | Pipeline answers | Pipeline = reference | Pipeline = a stated reading only |
|---|---|---|---|---|---|---|
| Pollution | 80 | 73 | 0 | 21 | 0 | 7 |
| Inventory | 160 | 160 | 159 | 23 | 12 | 7 |

Inventory references reproduced by each capacity reading: capacity at end of period: 91, capacity also after arrival: 159.


## Hand check records (results/reference_check/hand_labels.csv)

Hand-checked cases are recorded in `hand_labels.csv` with columns `problem_id, problem_class, reference, hand_optimum, reading, label, note`:

* **Inventory:** 157 canonical problems are `reference_correct`. Two problems (`canonical-0644` and `canonical-0667`) are labeled `text_ambiguous` because the reference requires after-arrival capacity despite explicit "end of period" phrasing in the prompt. One problem (`canonical-0648`) is labeled `reference_wrong` because neither capacity reading reproduces reference 1,818.0 (hand optima yield 876.0 and 1,061.0). Five newly parsed problems were confirmed by hand spot-check (`canonical-0630`, `0634`, `0666`, `0680`, `0736`).
* **Pollution Control:** 73 parsed canonical problems are labeled `reference_wrong` based on automated and hand verification (none reproduce the reference; 6 are mathematically infeasible as stated, 34 are below the physical minimum expenditure). Four cases were verified by hand (`canonical-1572`, `1575`, `1578`, `1601`). The 7 unparsed canonical questions are recorded as `not_checked`.
* **Sensitivity Analysis:** Main evaluation includes all instances; sensitivity analysis excludes `reference_wrong` cases (all Pollution instances and `canonical-0648`), while `text_ambiguous` instances remain in both analyses.
