# Failure analysis

## Outcomes per sample

| Sample | Problems | Wrong accept | Correct refusal | False alarm |
|---|---|---|---|---|
| canonical_200 | 200 | 13 | 31 | 6 |
| constraint_pairs_60 | 120 | 7 | 39 | 8 |
| linguistic_60 | 60 | 4 | 8 | 6 |

## Wrong answers by category (102 in all)

| Category | Wrong accept | Correct refusal | Total | Share |
|---|---|---|---|---|
| wrong constraint | 14 | 39 | 53 | 52.0% |
| doubtful reference | 7 | 19 | 26 | 25.5% |
| code error | 0 | 9 | 9 | 8.8% |
| other | 2 | 7 | 9 | 8.8% |
| missing constraint | 1 | 2 | 3 | 2.9% |
| integrality error | 0 | 2 | 2 | 2.0% |

## False alarms by signal

| Signal | Count |
|---|---|
| paraphrase disagreement | 19 |
| requirement not linked | 0 |
| number not used | 1 |
