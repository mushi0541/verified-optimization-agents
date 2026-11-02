# Gap 2 (H2): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl

**Sensitivity analysis without Pollution.** Not the H2 result itself; report it next to the full one.

H2 (alpha = 10%, at least 50% answered): **not supported**

| Run | Alpha | Answered | Coverage | Wrong accepted | Wrong-accept rate [exact 95%] | All-classes threshold |
|---|---|---|---|---|---|---|
| 1 | 5% | 54 / 527 | 10.2% | 8 | 14.8% [6.6%, 27.1%] | answer nothing |
| 1 | 10% | 495 / 527 | 93.9% | 53 | 10.7% [8.1%, 13.8%] | 0.683 |
| 1 | 20% | 516 / 527 | 97.9% | 72 | 14.0% [11.1%, 17.2%] | 0.500 |
| 1 | fixed 0.8 | 455 / 527 | 86.3% | 25 | 5.5% | 0.8 |

Alpha scan (an extra analysis, not H2 itself): the smallest alpha the data supports.

| Run | Smallest alpha meeting H2's rule | ... and its one-sided bound | Coverage there |
|---|---|---|---|
| 1 | 8.0% | 16.0% | 85.6% |

Shift test, run 1: thresholds calibrated on every class of this run except Pollution, applied to results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl (36 problems).

| Setting | Threshold | CrewRostering | EquipmentDispatch | GateAssignment | All |
|---|---|---|---|---|---|
| alpha 5% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 10% | 0.683 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| alpha 20% | 0.500 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| fixed | 0.800 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
