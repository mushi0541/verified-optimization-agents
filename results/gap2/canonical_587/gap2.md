# Gap 2 (H2): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl

H2 (alpha = 10%, at least 50% answered): **not supported**

| Run | Alpha | Answered | Coverage | Wrong accepted | Wrong-accept rate [exact 95%] | All-classes threshold |
|---|---|---|---|---|---|---|
| 1 | 5% | 0 / 587 | 0.0% | 0 | n/a [0.0%, 100.0%] | answer nothing |
| 1 | 10% | 92 / 587 | 15.7% | 46 | 50.0% [39.4%, 60.6%] | answer nothing |
| 1 | 20% | 556 / 587 | 94.7% | 112 | 20.1% [16.9%, 23.7%] | 0.683 |
| 1 | fixed 0.8 | 480 / 587 | 81.8% | 50 | 10.4% | 0.8 |

Alpha scan (an extra analysis, not H2 itself): the smallest alpha the data supports.

| Run | Smallest alpha meeting H2's rule | ... and its one-sided bound | Coverage there |
|---|---|---|---|
| 1 | 21.0% | 26.0% | 95.1% |

Shift test, run 1: thresholds calibrated on every class of this run, applied to results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl (36 problems).

| Setting | Threshold | CrewRostering | EquipmentDispatch | GateAssignment | All |
|---|---|---|---|---|---|
| alpha 5% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 10% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 20% | 0.683 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| fixed | 0.800 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
