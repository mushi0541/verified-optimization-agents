# Gap 2 (H2): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl, results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl, results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0153/records.jsonl

**Only the problems of `samples/canonical_200.json`** (`--sample`), in every repeat.

H2 (alpha = 10%, at least 50% answered): **not supported**

| Run | Alpha | Answered | Coverage | Wrong accepted | Wrong-accept rate [exact 95%] | All-classes threshold |
|---|---|---|---|---|---|---|
| 1 | 5% | 0 / 200 | 0.0% | 0 | n/a [0.0%, 100.0%] | answer nothing |
| 1 | 10% | 6 / 200 | 3.0% | 3 | 50.0% [11.8%, 88.2%] | answer nothing |
| 1 | 20% | 190 / 200 | 95.0% | 34 | 17.9% [12.7%, 24.1%] | 0.647 |
| 1 | fixed 0.8 | 163 / 200 | 81.5% | 13 | 8.0% | 0.8 |
| 2 | 5% | 0 / 200 | 0.0% | 0 | n/a [0.0%, 100.0%] | answer nothing |
| 2 | 10% | 56 / 200 | 28.0% | 14 | 25.0% [14.4%, 38.4%] | 0.992 |
| 2 | 20% | 194 / 200 | 97.0% | 37 | 19.1% [13.8%, 25.3%] | 0.694 |
| 2 | fixed 0.8 | 169 / 200 | 84.5% | 14 | 8.3% | 0.8 |
| 3 | 5% | 0 / 200 | 0.0% | 0 | n/a [0.0%, 100.0%] | answer nothing |
| 3 | 10% | 0 / 200 | 0.0% | 0 | n/a [0.0%, 100.0%] | answer nothing |
| 3 | 20% | 184 / 200 | 92.0% | 29 | 15.8% [10.8%, 21.8%] | 0.722 |
| 3 | fixed 0.8 | 167 / 200 | 83.5% | 15 | 9.0% | 0.8 |

Width of the pooled exact interval, all problems against the subset:

- Run 1, alpha 5%: 1.000 (200 problems) against 1.000 (100 problems)
- Run 1, alpha 10%: 0.764 (200 problems) against 1.000 (100 problems)
- Run 1, alpha 20%: 0.114 (200 problems) against 0.185 (100 problems)
- Run 2, alpha 5%: 1.000 (200 problems) against 1.000 (100 problems)
- Run 2, alpha 10%: 0.240 (200 problems) against 0.461 (100 problems)
- Run 2, alpha 20%: 0.115 (200 problems) against 0.156 (100 problems)
- Run 3, alpha 5%: 1.000 (200 problems) against 1.000 (100 problems)
- Run 3, alpha 10%: 1.000 (200 problems) against 1.000 (100 problems)
- Run 3, alpha 20%: 0.110 (200 problems) against 0.166 (100 problems)

Alpha scan (an extra analysis, not H2 itself): the smallest alpha the data supports.

| Run | Smallest alpha meeting H2's rule | ... and its one-sided bound | Coverage there |
|---|---|---|---|
| 1 | 18.0% | 24.0% | 94.0% |
| 2 | 12.0% | 26.0% | 82.0% |
| 3 | 17.0% | 21.0% | 91.5% |

Shift test, run 1: thresholds calibrated on every class of this run, applied to results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl (36 problems).

| Setting | Threshold | CrewRostering | EquipmentDispatch | GateAssignment | All |
|---|---|---|---|---|---|
| alpha 5% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 10% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 20% | 0.647 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| fixed | 0.800 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |

Shift test, run 2: thresholds calibrated on every class of this run, applied to results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl (36 problems).

| Setting | Threshold | CrewRostering | EquipmentDispatch | GateAssignment | All |
|---|---|---|---|---|---|
| alpha 5% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 10% | 0.992 | 6/12 answered, 0.0% wrong | 0/12 answered, n/a wrong | 1/12 answered, 0.0% wrong | 7/36 answered, 0.0% wrong |
| alpha 20% | 0.694 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| fixed | 0.800 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |

Shift test, run 3: thresholds calibrated on every class of this run, applied to results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl (36 problems).

| Setting | Threshold | CrewRostering | EquipmentDispatch | GateAssignment | All |
|---|---|---|---|---|---|
| alpha 5% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 10% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 20% | 0.722 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| fixed | 0.800 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
