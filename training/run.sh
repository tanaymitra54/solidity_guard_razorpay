#!/bin/bash
# ============================================================================
# SolidityGuard - Graph CodeBERT Fine-Tuning Pipeline (Full End-to-End)
# ============================================================================
#
# ONE COMMAND DOES EVERYTHING:
#   cd ContractSLM
#   bash training/run.sh
#
# What this does:
#   1. Installs Python dependencies
#   2. Downloads SmartBugs-Curated (69 labeled contracts)
#   3. Downloads SmartBugs-Wild (47K contracts with tool consensus labels)
#   4. Merges with SolidityGuard data (21 contracts)
#   5. Prepares train/val/test splits
#   6. Pulls Graph CodeBERT from HuggingFace (~500MB)
#   7. Fine-tunes for 20 epochs with early stopping
#   8. Evaluates on test set
#   9. Reports metrics
#
# Requirements:
#   - Python 3.11+
#   - CUDA GPU (H100 recommended, works on any GPU)
#   - ~10GB disk for repos + model
#   - ~30 min total runtime on H100
#
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=============================================="
echo " SolidityGuard - Graph CodeBERT Pipeline"
echo " Full End-to-End Fine-Tuning"
echo "=============================================="
echo ""
echo "Working directory: $(pwd)"
echo ""

# --- Check GPU ---
echo "[Step 1/9] Checking GPU..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    echo ""
else
    echo "WARNING: nvidia-smi not found. Will use CPU (very slow)."
    echo ""
fi

# --- Check Python ---
echo "[Step 2/9] Checking Python..."
python3 --version
echo ""

# --- Install dependencies ---
echo "[Step 3/9] Installing Python dependencies..."
pip install -q torch transformers datasets scikit-learn pyyaml accelerate 2>/dev/null || \
pip install torch transformers datasets scikit-learn pyyaml accelerate
echo "  Dependencies installed."
echo ""

# --- Download datasets ---
echo "[Step 4/9] Downloading datasets..."
echo "  This will clone SmartBugs repos (first run only, ~500MB)..."
echo ""
python3 training/download_data.py \
    --output training/data \
    --manifest data/manifest.json \
    --wild-limit 5000
echo ""

# --- Prepare splits ---
echo "[Step 5/9] Preparing train/val/test splits..."
python3 training/dataset.py \
    --combined training/data/combined.json \
    --augment \
    --output training/cache
echo ""

# --- Show dataset summary ---
echo "[Step 6/9] Dataset summary..."
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

# Label distribution
for name, data in [('train', train), ('val', val), ('test', test)]:
    labels = {}
    for s in data:
        lbl = s.get('primary_vuln', 'unknown')
        labels[lbl] = labels.get(lbl, 0) + 1
    print(f'  {name}: {dict(sorted(labels.items()))}')
"
echo ""

# --- Fine-tune ---
echo "[Step 7/9] Fine-tuning Graph CodeBERT..."
echo "  Model: microsoft/graphcodebert-base"
echo "  (Downloads from HuggingFace on first run — ~500MB)"
echo "  Training starts now..."
echo ""
python3 training/train.py --config training/config.yaml
echo ""

# --- Evaluate ---
echo "[Step 8/9] Evaluating on test set..."
python3 training/evaluate.py \
    --model training/checkpoints/best \
    --manifest data/manifest.json \
    --split test \
    --output training/checkpoints/evaluation_results.json
echo ""

# --- Final summary ---
echo "[Step 9/9] Pipeline complete!"
echo ""
echo "=============================================="
echo " RESULTS"
echo "=============================================="
echo ""
echo "Dataset:"
echo "  SmartBugs-Curated: 69 labeled contracts"
echo "  SmartBugs-Wild:    ~5000 contracts (tool consensus)"
echo "  SolidityGuard:     21 contracts"
echo ""
echo "Model outputs:"
echo "  Best model:    training/checkpoints/best/"
echo "  Final model:   training/checkpoints/final/"
echo "  Test results:  training/checkpoints/test_results.json"
echo "  Eval report:   training/checkpoints/evaluation_results.json"
echo "  Train history: training/checkpoints/training_history.json"
echo ""
echo "To use the fine-tuned model:"
echo "  python training/evaluate.py --model training/checkpoints/best --split test"
echo ""
echo "=============================================="
