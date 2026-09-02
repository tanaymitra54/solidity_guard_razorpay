#!/bin/bash
# ============================================================================
# SolidityGuard - Graph CodeBERT Fine-Tuning (SmartBugs-Wild only)
# ============================================================================
#
# ONE COMMAND ON THE GPU BOX:
#   cd ContractSLM
#   bash training/run.sh
#
# What this does:
#   1. Installs Python dependencies
#   2. Downloads SmartBugs-Wild (capped, default 5000) — not Curated / not full 47k
#   3. Prepares train/val/test splits
#   4. Pulls microsoft/graphcodebert-base from HuggingFace
#   5. Fine-tunes with early stopping
#   6. Evaluates on the held-out wild test split
#
# After training, copy training/checkpoints/best/ onto the serving host and set:
#   GRAPHCODEBERT_PATH=training/checkpoints/best
#
# Optional env overrides:
#   WILD_LIMIT=5000
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

WILD_LIMIT="${WILD_LIMIT:-5000}"

echo "=============================================="
echo " SolidityGuard - Graph CodeBERT"
echo " SmartBugs-Wild only (limit=${WILD_LIMIT})"
echo "=============================================="
echo ""
echo "Working directory: $(pwd)"
echo ""

echo "[Step 1/8] Checking GPU..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    echo ""
else
    echo "WARNING: nvidia-smi not found. Will use CPU (very slow)."
    echo ""
fi

echo "[Step 2/8] Checking Python..."
python3 --version
echo ""

echo "[Step 3/8] Installing Python dependencies..."
pip install -q torch transformers datasets scikit-learn pyyaml accelerate 2>/dev/null || \
pip install torch transformers datasets scikit-learn pyyaml accelerate
echo "  Dependencies installed."
echo ""

echo "[Step 4/8] Downloading SmartBugs-Wild (limit=${WILD_LIMIT})..."
python3 training/download_data.py \
    --output training/data \
    --wild-only \
    --wild-limit "${WILD_LIMIT}"
echo ""

echo "[Step 5/8] Preparing train/val/test splits..."
python3 training/dataset.py \
    --combined training/data/combined.json \
    --augment \
    --output training/cache
echo ""

echo "[Step 6/8] Dataset summary..."
python3 -c "
import json
with open('training/cache/train.json') as f:
    train = json.load(f)
with open('training/cache/val.json') as f:
    val = json.load(f)
with open('training/cache/test.json') as f:
    test = json.load(f)
print(f'  Train: {len(train)} examples')
print(f'  Val:   {len(val)} examples')
print(f'  Test:  {len(test)} examples')
print(f'  Total: {len(train) + len(val) + len(test)} examples')
for name, data in [('train', train), ('val', val), ('test', test)]:
    labels = {}
    for s in data:
        lbl = s.get('primary_vuln', 'unknown')
        labels[lbl] = labels.get(lbl, 0) + 1
    print(f'  {name}: {dict(sorted(labels.items()))}')
"
echo ""

echo "[Step 7/8] Fine-tuning Graph CodeBERT..."
echo "  Model: microsoft/graphcodebert-base"
python3 training/train.py --config training/config.yaml
echo ""

echo "[Step 8/8] Evaluating on wild test split (from training cache)..."
# evaluate.py still expects a manifest; train.py already wrote test_results.json.
# Prefer the checkpoint metrics from training.
if [[ -f training/checkpoints/test_results.json ]]; then
    python3 -c "
import json
m=json.load(open('training/checkpoints/test_results.json'))
print('  accuracy:', m.get('accuracy'))
print('  f1_macro:', m.get('f1_macro'))
print('  f1_per_class:', json.dumps(m.get('f1_per_class', {}), indent=2))
"
else
    echo "  WARNING: training/checkpoints/test_results.json missing"
fi
echo ""

echo "=============================================="
echo " DONE"
echo "=============================================="
echo ""
echo "Dataset: SmartBugs-Wild only (limit=${WILD_LIMIT})"
echo "Best model: training/checkpoints/best/"
echo ""
echo "On the serving host:"
echo "  export GRAPHCODEBERT_PATH=training/checkpoints/best"
echo "  # optional: GRAPHCODEBERT_THRESHOLD=0.5"
echo ""
