# Gap 2 (H2): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl

H2 (alpha = 10%, at least 50% answered): **not supported**

| Run | Alpha | Answered | Coverage | Wrong accepted | Wrong-accept rate [exact 95%] | All-classes threshold |
|---|---|---|---|---|---|---|
| 1 | 5% | 182 / 1070 | 17.0% | 15 | 8.2% [4.7%, 13.2%] | answer nothing |
| 1 | 10% | 508 / 1070 | 47.5% | 81 | 15.9% [12.9%, 19.4%] | 0.490 |
| 1 | 20% | 1054 / 1070 | 98.5% | 83 | 7.9% [6.3%, 9.7%] | 0.490 |
| 1 | fixed 0.8 | 988 / 1070 | 92.3% | 35 | 3.5% | 0.8 |

Alpha scan (an extra analysis, not H2 itself): the smallest alpha the data supports.

| Run | Smallest alpha meeting H2's rule | ... and its one-sided bound | Coverage there |
|---|---|---|---|
| 1 | 12.0% | 12.0% | 98.3% |

Shift test, run 1: thresholds calibrated on every class of this run, applied to results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl (36 problems).

| Setting | Threshold | CrewRostering | EquipmentDispatch | GateAssignment | All |
|---|---|---|---|---|---|
| alpha 5% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 10% | 0.490 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| alpha 20% | 0.490 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| fixed | 0.800 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |

B0 on the same 1070 problems: answers 1022 (95.5%), wrong-accept rate 7.1% (73 wrong).
