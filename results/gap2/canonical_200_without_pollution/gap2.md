# Gap 2 (H2): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl, results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl, results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0153/records.jsonl

**Only the problems of `samples/canonical_200.json`** (`--sample`), in every repeat.

**Sensitivity analysis without Pollution.** Not the H2 result itself; report it next to the full one.

H2 (alpha = 10%, at least 50% answered): **not supported**

| Run | Alpha | Answered | Coverage | Wrong accepted | Wrong-accept rate [exact 95%] | All-classes threshold |
|---|---|---|---|---|---|---|
| 1 | 5% | 0 / 180 | 0.0% | 0 | n/a [0.0%, 100.0%] | answer nothing |
| 1 | 10% | 59 / 180 | 32.8% | 14 | 23.7% [13.6%, 36.6%] | 0.995 |
| 1 | 20% | 172 / 180 | 95.6% | 16 | 9.3% [5.4%, 14.7%] | 0.500 |
| 1 | fixed 0.8 | 158 / 180 | 87.8% | 8 | 5.1% | 0.8 |
| 2 | 5% | 0 / 180 | 0.0% | 0 | n/a [0.0%, 100.0%] | answer nothing |
| 2 | 10% | 168 / 180 | 93.3% | 12 | 7.1% [3.7%, 12.1%] | 0.722 |
| 2 | 20% | 177 / 180 | 98.3% | 20 | 11.3% [7.0%, 16.9%] | 0.500 |
| 2 | fixed 0.8 | 162 / 180 | 90.0% | 7 | 4.3% | 0.8 |
| 3 | 5% | 0 / 180 | 0.0% | 0 | n/a [0.0%, 100.0%] | answer nothing |
| 3 | 10% | 29 / 180 | 16.1% | 6 | 20.7% [8.0%, 39.7%] | answer nothing |
| 3 | 20% | 172 / 180 | 95.6% | 16 | 9.3% [5.4%, 14.7%] | 0.583 |
| 3 | fixed 0.8 | 161 / 180 | 89.4% | 9 | 5.6% | 0.8 |

Alpha scan (an extra analysis, not H2 itself): the smallest alpha the data supports.

| Run | Smallest alpha meeting H2's rule | ... and its one-sided bound | Coverage there |
|---|---|---|---|
| 1 | 12.0% | 14.0% | 73.3% |
| 2 | 9.0% | 16.0% | 84.4% |
| 3 | 13.0% | 13.0% | 90.0% |

Shift test, run 1: thresholds calibrated on every class of this run except Pollution, applied to results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl (36 problems).

| Setting | Threshold | CrewRostering | EquipmentDispatch | GateAssignment | All |
|---|---|---|---|---|---|
| alpha 5% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 10% | 0.995 | 6/12 answered, 0.0% wrong | 0/12 answered, n/a wrong | 1/12 answered, 0.0% wrong | 7/36 answered, 0.0% wrong |
| alpha 20% | 0.500 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| fixed | 0.800 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |

Shift test, run 2: thresholds calibrated on every class of this run except Pollution, applied to results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl (36 problems).

| Setting | Threshold | CrewRostering | EquipmentDispatch | GateAssignment | All |
|---|---|---|---|---|---|
| alpha 5% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 10% | 0.722 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| alpha 20% | 0.500 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| fixed | 0.800 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |

Shift test, run 3: thresholds calibrated on every class of this run except Pollution, applied to results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl (36 problems).

| Setting | Threshold | CrewRostering | EquipmentDispatch | GateAssignment | All |
|---|---|---|---|---|---|
| alpha 5% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 10% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 20% | 0.583 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| fixed | 0.800 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
