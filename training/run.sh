#!/bin/bash
# ============================================================================
# SolidityGuard - Graph CodeBERT Fine-Tuning Pipeline
# ============================================================================
#
# One-command launch for H100 GPU server.
#
# Usage:
#   cd ContractSLM
#   bash training/run.sh
#
# What this does:
#   1. Installs Python dependencies
#   2. Prepares the dataset
#   3. Fine-tunes Graph CodeBERT (downloads model on first run)
#   4. Evaluates on test set
#   5. Reports metrics
#
# ============================================================================

set -e

echo "=============================================="
echo " SolidityGuard - Graph CodeBERT Fine-Tuning"
echo "=============================================="
echo ""

# --- Check GPU ---
echo "[1/5] Checking GPU..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    echo ""
else
    echo "WARNING: nvidia-smi not found. Training will use CPU (slow)."
    echo ""
fi

# --- Install dependencies ---
echo "[2/5] Installing dependencies..."
pip install -q torch transformers datasets scikit-learn pyyaml accelerate 2>/dev/null
echo "  Done."
echo ""

# --- Prepare dataset ---
echo "[3/5] Preparing dataset..."
python training/dataset.py \
    --manifest data/manifest.json \
    --augment \
    --output training/cache
echo ""

# --- Fine-tune ---
echo "[4/5] Fine-tuning Graph CodeBERT..."
echo "  (Model downloads from HuggingFace on first run — ~500MB)"
echo ""
python training/train.py --config training/config.yaml
echo ""

# --- Evaluate ---
echo "[5/5] Evaluating on test set..."
python training/evaluate.py \
    --model training/checkpoints/best \
    --manifest data/manifest.json \
    --split test \
    --output training/checkpoints/evaluation_results.json
echo ""

echo "=============================================="
echo " Pipeline Complete!"
echo "=============================================="
echo ""
echo "Outputs:"
echo "  Model:      training/checkpoints/best/"
echo "  Metrics:    training/checkpoints/test_results.json"
echo "  Eval:       training/checkpoints/evaluation_results.json"
echo "  History:    training/checkpoints/training_history.json"
echo ""
