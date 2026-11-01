# Failure analysis

## Outcomes per sample

| Sample | Problems | Wrong accept | Correct refusal | False alarm |
|---|---|---|---|---|
| canonical_200 | 200 | 13 | 31 | 6 |
| constraint_pairs_60 | 120 | 7 | 39 | 8 |
| linguistic_60 | 60 | 4 | 8 | 6 |

**Not final:** 80 rows are still pending (blank label), shown as 'pending'.

## Wrong answers by category (102 in all)

| Category | Wrong accept | Correct refusal | Total | Share |
|---|---|---|---|---|
| pending | 18 | 62 | 80 | 78.4% |
| code error | 0 | 9 | 9 | 8.8% |
| wrong constraint | 3 | 2 | 5 | 4.9% |
| missing constraint | 1 | 2 | 3 | 2.9% |
| other | 2 | 1 | 3 | 2.9% |
| integrality error | 0 | 2 | 2 | 2.0% |

## False alarms by signal

| Signal | Count |
|---|---|
| paraphrase disagreement | 19 |
| requirement not linked | 1 |
| number not used | 0 |
