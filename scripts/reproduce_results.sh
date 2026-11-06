#!/usr/bin/env bash
# Rebuilds the saved analysis results from the saved run records, in the folders the repository uses.
# It needs no API key and makes no network or model calls (only the offline scripts in scripts/).
# Run it from the repository root. It takes about 20 minutes. Afterwards `git status` shows only the plot PDFs (new
# metadata), float noise below 1e-9 and "skipped" keys that newer versions of the scripts add.
set -euo pipefail

# E1/E2: B0 and B1 against the base paper
python scripts/compare_baselines.py \
    --repeat results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0223/records.jsonl \
    --repeat results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261105-1852/records.jsonl \
    --repeat results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261105-1907/records.jsonl \
    --repeat results/baseline_bedrock-deepseek.v3.2_canonical_200_r0_20261102-0247/records.jsonl \
    --repeat results/baseline_bedrock-deepseek.v3.2_canonical_200_r0_20261105-2045/records.jsonl \
    --repeat results/baseline_bedrock-deepseek.v3.2_canonical_200_r0_20261105-2126/records.jsonl \
    --paper docs/paper_sir.json --out-dir results/e1_e2

# E4 Gap 1: AUROC of the signals
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0153/records.jsonl \
    --sample \
    samples/canonical_200.json \
    --out \
    results/gap1/canonical_200
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    --out \
    results/gap1/canonical_587
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_constraint_pairs_60_r1_20261101-1430/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_constraint_pairs_60_r1_20261101-2337/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_constraint_pairs_60_r1_20261105-2035/records.jsonl \
    --out \
    results/gap1/constraint_pairs_60
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_linguistic_60_r1_20261101-1431/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_linguistic_60_r1_20261102-0045/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_linguistic_60_r1_20261105-2152/records.jsonl \
    --out \
    results/gap1/linguistic_60

# E4 Gap 2: calibrated threshold, with the run without Pollution and the OpsOR-Bench shift
python scripts/analyze_gap2.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0153/records.jsonl \
    --sample \
    samples/canonical_200.json \
    --subset \
    samples/canonical_100.json \
    --shift \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl \
    --alpha-scan \
    --out \
    results/gap2/canonical_200
python scripts/analyze_gap2.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    --shift \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl \
    --alpha-scan \
    --out \
    results/gap2/canonical_587
python scripts/analyze_gap2.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0153/records.jsonl \
    --sample \
    samples/canonical_200.json \
    --exclude-classes \
    Pollution \
    --shift \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl \
    --alpha-scan \
    --out \
    results/gap2/canonical_200_without_pollution
python scripts/analyze_gap2.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    --exclude-classes \
    Pollution \
    --shift \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl \
    --alpha-scan \
    --out \
    results/gap2/canonical_587_without_pollution

# E4 Gap 3: pipeline against B2 at equal tokens, and the plots
python scripts/analyze_e3.py \
    --pipeline results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl \
    --b2 results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0231/records.jsonl \
    --baseline results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0223/records.jsonl \
    --out results/gap3/canonical_200
python scripts/plot_e3.py --curve results/gap3/canonical_200/accuracy_cost.csv \
    --pipeline results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl \
    --b2 results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0231/records.jsonl \
    --out results/gap3/canonical_200

# E5: ablations (i) to (vii) on ablation_50
python scripts/ablation_table.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0153/records.jsonl \
    --no-parser-records results/pipeline_bedrock-openai.gpt-oss-120b-1-0_ablation_50_r1_20261102-1000/records.jsonl \
    --r2-records results/pipeline_bedrock-openai.gpt-oss-120b-1-0_ablation_50_r2_20261102-1001/records.jsonl \
    --out results/ablations/ablations.csv

# E6: efficiency and reliability (leaves out the v3-prompt, second-paraphraser and ap-southeast-2 runs)
python scripts/efficiency.py --sample samples/canonical_200.json --out-dir results/e6/canonical_200 \
    --runs \
    results/b2_bedrock-deepseek.v3.2_canonical_200_r1_20261102-2036 \
    results/b2_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261103-1042 \
    results/b2_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261103-1501 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0231 \
    results/b2_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261103-0755 \
    results/b2_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261103-0420 \
    results/b2_bedrock-zai.glm-4.7_canonical_200_r1_20261103-1243 \
    results/baseline_bedrock-deepseek.v3.2_canonical_200_r0_20261102-0247 \
    results/baseline_bedrock-deepseek.v3.2_canonical_200_r1_20261102-1258 \
    results/baseline_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261102-1258 \
    results/baseline_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261102-1258 \
    results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0223 \
    results/baseline_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261102-1259 \
    results/baseline_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261102-1258 \
    results/baseline_bedrock-zai.glm-4.7_canonical_200_r1_20261102-1258 \
    results/pipeline_bedrock-deepseek.v3.2_canonical_200_r1_20261102-1257 \
    results/pipeline_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261102-1258 \
    results/pipeline_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261102-1258 \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429 \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0153 \
    results/pipeline_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261102-1259 \
    results/pipeline_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261102-1258 \
    results/pipeline_bedrock-zai.glm-4.7_canonical_200_r1_20261102-1258 \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254
python scripts/efficiency.py --out-dir results/e6/canonical_unused \
    --runs \
    results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255 \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261103-1522

# Pre-registered H1: Gap 1 on the new problems and the six other models
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-deepseek.v3.2_canonical_200_r1_20261102-1257/records.jsonl \
    --baseline \
    results/baseline_bedrock-deepseek.v3.2_canonical_200_r1_20261102-1258/records.jsonl \
    --out \
    results/preregistered/h1/canonical_200_deepseek
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-zai.glm-4.7_canonical_200_r1_20261102-1258/records.jsonl \
    --baseline \
    results/baseline_bedrock-zai.glm-4.7_canonical_200_r1_20261102-1258/records.jsonl \
    --out \
    results/preregistered/h1/canonical_200_glm
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261102-1259/records.jsonl \
    --baseline \
    results/baseline_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261102-1259/records.jsonl \
    --out \
    results/preregistered/h1/canonical_200_gpt-oss-20b
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261102-1258/records.jsonl \
    --baseline \
    results/baseline_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261102-1258/records.jsonl \
    --out \
    results/preregistered/h1/canonical_200_kimi
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261102-1258/records.jsonl \
    --baseline \
    results/baseline_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261102-1258/records.jsonl \
    --out \
    results/preregistered/h1/canonical_200_mistral
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261102-1258/records.jsonl \
    --baseline \
    results/baseline_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261102-1258/records.jsonl \
    --out \
    results/preregistered/h1/canonical_200_qwen
python scripts/analyze_gap1.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --baseline \
    results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --out \
    results/preregistered/h1/canonical_unused

# Pre-registered H2: Gap 2 on the 1,070 unused problems, with and without Pollution
python scripts/analyze_gap2.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --baseline \
    results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --shift \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl \
    --alpha-scan \
    --out \
    results/preregistered/h2/canonical_unused
python scripts/analyze_gap2.py \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --baseline \
    results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --exclude-classes \
    Pollution \
    --shift \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_opsor_r1_20261101-2119/records.jsonl \
    --alpha-scan \
    --out \
    results/preregistered/h2/canonical_unused_without_pollution

# Pre-registered H3c: pipeline k = 1 combined with B2, with the sensitivity runs
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-deepseek.v3.2_canonical_200_r1_20261102-1257/records.jsonl \
    --b2 \
    results/b2_bedrock-deepseek.v3.2_canonical_200_r1_20261102-2036/records.jsonl \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_deepseek
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-deepseek.v3.2_canonical_200_r1_20261102-1257/records.jsonl \
    --b2 \
    results/b2_bedrock-deepseek.v3.2_canonical_200_r1_20261102-2036/records.jsonl \
    --skip-class \
    Pollution \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_deepseek_without_pollution
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-zai.glm-4.7_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-zai.glm-4.7_canonical_200_r1_20261103-1243/records.jsonl \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_glm
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-zai.glm-4.7_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-zai.glm-4.7_canonical_200_r1_20261103-1243/records.jsonl \
    --skip-class \
    Pollution \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_glm_without_pollution
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261102-1259/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261103-0755/records.jsonl \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_gpt-oss-20b
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261102-1259/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261103-0755/records.jsonl \
    --skip-class \
    Pollution \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_gpt-oss-20b_without_pollution
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261103-1501/records.jsonl \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_kimi
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261103-1501/records.jsonl \
    --skip-class \
    Pollution \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_kimi_without_pollution
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261103-1042/records.jsonl \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_mistral
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261103-1042/records.jsonl \
    --skip-class \
    Pollution \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_mistral_without_pollution
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261103-0420/records.jsonl \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_qwen
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261103-0420/records.jsonl \
    --skip-class \
    Pollution \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_200_qwen_without_pollution
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_587_rest_387_r1_20261102-1248/records.jsonl \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_587_rest_387
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_587_rest_387_r1_20261102-1248/records.jsonl \
    --skip-class \
    Pollution \
    --skip-problem \
    canonical-0648 \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_587_rest_387_sensitivity
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_587_rest_387_r1_20261102-1248/records.jsonl \
    --skip-class \
    Pollution \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_587_rest_387_without_pollution
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261103-1522/records.jsonl \
    --per-class \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_unused
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261103-1522/records.jsonl \
    --skip-class \
    Pollution \
    --preregistered \
    --out \
    results/preregistered/h3c/canonical_unused_without_pollution
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_587_rest_387_r1_20261102-1248/records.jsonl \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261103-1522/records.jsonl \
    --per-class \
    --preregistered \
    --out \
    results/preregistered/h3c/held_out_1457
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_587_rest_387_r1_20261102-1248/records.jsonl \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261103-1522/records.jsonl \
    --skip-class \
    Pollution \
    --skip-problem \
    canonical-0648 \
    --preregistered \
    --out \
    results/preregistered/h3c/held_out_1457_sensitivity
python scripts/explore_combination.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_587_rest_387_r1_20261102-1248/records.jsonl \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261103-1522/records.jsonl \
    --skip-class \
    Pollution \
    --preregistered \
    --out \
    results/preregistered/h3c/held_out_1457_without_pollution

# Pre-registered H3 and the sensitivity analysis: pipeline against B2
python scripts/analyze_e3.py \
    --pipeline results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261102-0231/records.jsonl \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_587_rest_387_r1_20261102-1248/records.jsonl \
    --out results/preregistered/h3/canonical_587
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-deepseek.v3.2_canonical_200_r1_20261102-1257/records.jsonl \
    --b2 \
    results/b2_bedrock-deepseek.v3.2_canonical_200_r1_20261102-2036/records.jsonl \
    --baseline \
    results/baseline_bedrock-deepseek.v3.2_canonical_200_r1_20261102-1258/records.jsonl \
    --out \
    results/preregistered/h3/canonical_200_deepseek
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-deepseek.v3.2_canonical_200_r1_20261102-1257/records.jsonl \
    --b2 \
    results/b2_bedrock-deepseek.v3.2_canonical_200_r1_20261102-2036/records.jsonl \
    --skip-class \
    Pollution \
    --out \
    results/preregistered/h3/canonical_200_deepseek_sensitivity
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-zai.glm-4.7_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-zai.glm-4.7_canonical_200_r1_20261103-1243/records.jsonl \
    --baseline \
    results/baseline_bedrock-zai.glm-4.7_canonical_200_r1_20261102-1258/records.jsonl \
    --out \
    results/preregistered/h3/canonical_200_glm
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-zai.glm-4.7_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-zai.glm-4.7_canonical_200_r1_20261103-1243/records.jsonl \
    --skip-class \
    Pollution \
    --out \
    results/preregistered/h3/canonical_200_glm_sensitivity
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261102-1259/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261103-0755/records.jsonl \
    --baseline \
    results/baseline_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261102-1259/records.jsonl \
    --out \
    results/preregistered/h3/canonical_200_gpt-oss-20b
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261102-1259/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-20b-1-0_canonical_200_r1_20261103-0755/records.jsonl \
    --skip-class \
    Pollution \
    --out \
    results/preregistered/h3/canonical_200_gpt-oss-20b_sensitivity
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261103-1501/records.jsonl \
    --baseline \
    results/baseline_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261102-1258/records.jsonl \
    --out \
    results/preregistered/h3/canonical_200_kimi
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-moonshotai.kimi-k2.5_canonical_200_r1_20261103-1501/records.jsonl \
    --skip-class \
    Pollution \
    --out \
    results/preregistered/h3/canonical_200_kimi_sensitivity
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261103-1042/records.jsonl \
    --baseline \
    results/baseline_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261102-1258/records.jsonl \
    --out \
    results/preregistered/h3/canonical_200_mistral
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-mistral.mistral-large-3-675b-instruct_canonical_200_r1_20261103-1042/records.jsonl \
    --skip-class \
    Pollution \
    --out \
    results/preregistered/h3/canonical_200_mistral_sensitivity
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261103-0420/records.jsonl \
    --baseline \
    results/baseline_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261102-1258/records.jsonl \
    --out \
    results/preregistered/h3/canonical_200_qwen
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261102-1258/records.jsonl \
    --b2 \
    results/b2_bedrock-qwen.qwen3-next-80b-a3b_canonical_200_r1_20261103-0420/records.jsonl \
    --skip-class \
    Pollution \
    --out \
    results/preregistered/h3/canonical_200_qwen_sensitivity
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_587_rest_387_r1_20261102-1248/records.jsonl \
    --skip-class \
    Pollution \
    --skip-problem \
    canonical-0648 \
    --out \
    results/preregistered/h3/canonical_587_rest_387_sensitivity
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261103-1522/records.jsonl \
    --baseline \
    results/baseline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --out \
    results/preregistered/h3/canonical_unused
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261103-1522/records.jsonl \
    --skip-class \
    Pollution \
    --out \
    results/preregistered/h3/canonical_unused_sensitivity
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_587_rest_387_r1_20261102-1248/records.jsonl \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261103-1522/records.jsonl \
    --out \
    results/preregistered/h3/held_out_1457
python scripts/analyze_e3.py \
    --pipeline \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_587_r1_20261101-2254/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261102-1255/records.jsonl \
    --b2 \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_587_rest_387_r1_20261102-1248/records.jsonl \
    results/b2_bedrock-openai.gpt-oss-120b-1-0_canonical_unused_r1_20261103-1522/records.jsonl \
    --skip-class \
    Pollution \
    --skip-problem \
    canonical-0648 \
    --out \
    results/preregistered/h3/held_out_1457_sensitivity

# Failure table (the labels in results/failures/labels.csv are set by hand and are only read here)
python scripts/failure_analysis.py table --labels results/failures/labels.csv \
    --records \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_canonical_200_r1_20261101-1429/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_constraint_pairs_60_r1_20261101-1430/records.jsonl \
    results/pipeline_bedrock-openai.gpt-oss-120b-1-0_linguistic_60_r1_20261101-1431/records.jsonl \
    --complete --out results/failures

# Paper tables (last, they read the results above)
python scripts/make_paper_tables.py
