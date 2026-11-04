# Gap 2 (H2): results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl

**Sensitivity analysis without Pollution.** Not the H2 result itself; report it next to the full one.

H2 (alpha = 10%, at least 50% answered): **not supported**

| Run | Alpha | Answered | Coverage | Wrong accepted | Wrong-accept rate [exact 95%] | All-classes threshold |
|---|---|---|---|---|---|---|
| 1 | 5% | 182 / 1060 | 17.2% | 15 | 8.2% [4.7%, 13.2%] | answer nothing |
| 1 | 10% | 498 / 1060 | 47.0% | 71 | 14.3% [11.3%, 17.6%] | 0.490 |
| 1 | 20% | 1044 / 1060 | 98.5% | 73 | 7.0% [5.5%, 8.7%] | 0.490 |
| 1 | fixed 0.8 | 983 / 1060 | 92.7% | 30 | 3.1% | 0.8 |

Alpha scan (an extra analysis, not H2 itself): the smallest alpha the data supports.

| Run | Smallest alpha meeting H2's rule | ... and its one-sided bound | Coverage there |
|---|---|---|---|
| 1 | 11.0% | 11.0% | 98.3% |

Shift test, run 1: thresholds calibrated on every class of this run except Pollution, applied to results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl (36 problems).

| Setting | Threshold | CrewRostering | EquipmentDispatch | GateAssignment | All |
|---|---|---|---|---|---|
| alpha 5% | answer nothing | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/12 answered, n/a wrong | 0/36 answered, n/a wrong |
| alpha 10% | 0.490 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| alpha 20% | 0.490 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |
| fixed | 0.800 | 12/12 answered, 0.0% wrong | 12/12 answered, 0.0% wrong | 10/12 answered, 0.0% wrong | 34/36 answered, 0.0% wrong |

B0 on the same 1060 problems: answers 1013 (95.6%), wrong-accept rate 6.3% (64 wrong).
