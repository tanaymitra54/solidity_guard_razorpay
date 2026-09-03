---
title: SolidityGuard
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: mit
short_description: Solidity smart contract security review environment
---

# SolidityGuard-Tanay

SolidityGuard is an OpenEnv RL environment that trains AI agents to review Solidity smart contracts for security vulnerabilities, gas optimizations, and best practices. It provides a multi-agent audit pipeline, structured reward scoring, and a dataset of real-world Solidity samples.

## Architecture

```mermaid
flowchart LR
  subgraph Client
    A[Agent or Script]
  end
  subgraph API
    B[FastAPI app.py]
  end
  subgraph Core
    C[environment.py]
    D[graders.py]
  end
  subgraph Agents
    E[Scanner]
    F[Analyzer]
    G[ExploitGen]
    H[FixSuggester]
    I[Orchestrator]
  end
  subgraph Data
    J[data/samples]
    K[data/manifest.json]
  end

  A <-->|/reset /step /state /audit| B
  B --> C
  C --> D
  C --> J
  C --> K
  D --> B
  B --> I
  I --> E
  I --> F
  I --> G
  I --> H
```

## What the project does

- **Multi-Agent Pipeline**: Scanner (pattern matching + Slither) → Analyzer (LLM deep analysis) → ExploitGen (Foundry PoC exploits) → FixSuggester (targeted patches)
- **4 Difficulty Tiers**: Best practices (easy) → Gas optimization (medium) → Security (hard) → Comprehensive audit (hard)
- **Advanced Scoring**: 5-component reward function (base match, line accuracy, exploit explanation, fix quality, confidence calibration)
- **21 Real-World Samples**: Solidity contracts covering 15+ vulnerability types across 4 tiers
- **Structured Logging**: JSON-formatted logs with request IDs for full pipeline traceability

## Competitive Comparison

| Feature | SolidityGuard | Slither | Mythril | MythX | Securify2 |
|---------|:---:|:---:|:---:|:---:|:---:|
| **Multi-Agent Architecture** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **LLM-Powered Analysis** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Auto-Generated Exploit PoCs** | ✅ Foundry tests | ❌ | ❌ | ❌ | ❌ |
| **Auto-Fix Suggestions** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Gas Optimization Detection** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Security Vulnerability Detection** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Best Practices Detection** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **RL Training Environment** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **OpenEnv Spec Compliant** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Self-Hosted / No API Cost** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Open Source** | ✅ MIT | ✅ | ✅ | ❌ | ✅ |
| **Audit Cost** | Free | Free | Free | $50-500/mo | Free |

## Task Taxonomy

| Task | Difficulty | Focus | Samples | Issue Types |
|------|:---:|-------|:---:|-------------|
| Task 1 | Easy | Best Practices & Syntax | 6 | SPDX, NatSpec, compiler version, deprecated patterns |
| Task 2 | Medium | Gas Optimization | 6 | Unbounded loops, storage reads, struct packing, custom errors |
| Task 3 | Hard | Security Vulnerabilities | 6 | Reentrancy, access control, tx.origin, delegatecall, randomness |
| Task 4 | Hard | Comprehensive Audit | 3 | Cross-category: combines best practices + gas + security issues |

## Dataset Statistics

```
Total Samples:  21
Total Issues:   49
Severity Distribution:
  Critical:     18 (36.7%)
  Medium:       13 (26.5%)
  Low:          18 (36.7%)

Task Breakdown:
  task_1_best_practices:    6 samples, 14 issues
  task_2_gas_optimization:  6 samples,  9 issues
  task_3_security:          6 samples,  9 issues
  task_4_comprehensive:     3 samples, 17 issues
```

## Quick Start

### Requirements
- Python 3.11+
- `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN` environment variables (for LLM inference)

### Install
```bash
pip install -r requirements.txt
```

### Run API Server
```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Run Inference
```bash
python inference.py
```

### Run Multi-Agent Audit (No LLM Required)
```python
from multi_agent import MultiAgentSystem

system = MultiAgentSystem()
source = open("data/samples/task3/reentrancy.sol").read()
findings = system.process(source, "task_3_security")
for f in findings:
    print(f"{f['issue_type']} (risk={f['risk_score']})")
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health with uptime and dataset info |
| POST | `/reset` | Initialize environment with a task |
| POST | `/step` | Submit findings and receive score |
| GET | `/state` | Get current environment state |
| POST | `/report` | Generate comprehensive audit report |
| POST | `/audit` | Run full multi-agent pipeline on a contract |
| GET | `/dashboard` | Real-time analytics (computed from dataset) |
| GET | `/` | Cyberpunk landing page |
| GET | `/demo` | Interactive live demo |

## Scoring System

The 5-component reward function:

| Component | Weight | Max Bonus | Description |
|-----------|:---:|:---:|-------------|
| Base Score | 60% | 0.6 | Matched findings / expected findings |
| Line Accuracy | — | +0.2 | Bonus for exact or near-exact line numbers |
| Exploit Explanation | — | +0.15 | Bonus for detailed attack scenarios (50+ chars) |
| Fix Suggestion | — | +0.15 | Bonus for actionable fix recommendations (20+ chars) |
| Confidence Calibration | — | +0.1 | Bonus for appropriate confidence levels |
| False Positive Penalty | — | -0.05 each | Deduction for each unmatched finding |

All scores are clamped to [0.0, 1.0] for stable RL reward signals.

## Structured Logging

All agents emit JSON-formatted logs with request tracing:

```json
{"event": "pipeline_start", "request_id": "a1b2c3d4e5f6", "task_id": "task_3_security", "source_lines": 42}
{"event": "scanner_start", "source_lines": 42}
{"event": "llm_call_success", "model": "Qwen/Qwen2.5-72B-Instruct", "attempt": 1, "tokens": 512}
{"event": "pipeline_done", "request_id": "a1b2c3d4e5f6", "total_findings": 3, "critical": 1, "elapsed": 4.2}
```

## Graph CodeBERT Fine-Tuning

SolidityGuard includes a complete fine-tuning pipeline for Microsoft Graph CodeBERT on the Solidity vulnerability detection task.

### One-Command Launch (H100 Server)

```bash
git clone https://github.com/tanaymitra54/solidity_guard_razorpay.git
cd solidity_guard_razorpay
bash training/run.sh
```

This will:
1. Install dependencies (PyTorch, Transformers, etc.)
2. Download **SmartBugs-Wild only** (default limit 5000; override with `WILD_LIMIT=...`)
3. Prepare train/val/test splits
4. Pull `microsoft/graphcodebert-base` from HuggingFace (~500MB)
5. Fine-tune for 20 epochs with early stopping
6. Evaluate on the held-out wild test split

After training, copy `training/checkpoints/best/` to the serving host and set `GRAPHCODEBERT_PATH`. The scanner uses it as a first-pass detector (Slither + Graph CodeBERT + LLM).
### Manual Steps

```bash
# Prepare dataset
python training/dataset.py --manifest data/manifest.json --augment --output training/cache

# Fine-tune (downloads model on first run)
python training/train.py --config training/config.yaml

# Evaluate
python training/evaluate.py --model training/checkpoints/best --split test
```

### Training Config (`training/config.yaml`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model_name` | `microsoft/graphcodebert-base` | HuggingFace model ID |
| `epochs` | 20 | Training epochs |
| `batch_size` | 16 | Batch size (H100: can go to 32) |
| `learning_rate` | 2e-5 | AdamW learning rate |
| `max_length` | 512 | Max token length |
| `early_stopping_patience` | 5 | Stop if no improvement for N epochs |

### Model Output

```
training/checkpoints/
├── best/              # Best model by val F1
│   ├── config.json
│   ├── model.safetensors
│   ├── tokenizer.json
│   └── label_map.json
├── final/             # Last epoch model
├── training_history.json
├── test_results.json
└── config.json
```

### Fine-Tuning Architecture

```
Input: Solidity source code (max 512 tokens)
  ↓
Graph CodeBERT (microsoft/graphcodebert-base)
  ↓  [CLS] token embedding (768-dim)
  ↓
Dropout (0.1)
  ↓
Linear (768 → 12 classes)
  ↓
Output: vulnerability type prediction
  ↓
Classes: safe, reentrancy, access_control, tx_origin_auth,
         integer_overflow, unsafe_delegatecall, weak_randomness,
         unbounded_loop, redundant_storage, gas_optimization,
         best_practice, other
```

## File Structure

```
ContractSLM/
├── server/
│   └── app.py              # FastAPI endpoints (health, reset, step, audit, dashboard)
├── agents/
│   ├── base.py             # BaseAgent, Finding, LLMClient, structured logging
│   ├── orchestrator.py     # Multi-agent pipeline coordinator
│   ├── scanner.py          # Pattern matching + Slither + LLM scanning
│   ├── analyzer.py         # Deep LLM-powered analysis
│   ├── exploit_gen.py      # Foundry PoC exploit generation
│   ├── fix_suggester.py    # Targeted fix generation
│   └── __init__.py
├── training/
│   ├── dataset.py          # Dataset prep: manifest → train/val/test splits
│   ├── train.py            # Graph CodeBERT fine-tuning pipeline
│   ├── evaluate.py         # Evaluation with metrics + report
│   ├── config.yaml         # Hyperparameters for H100
│   ├── run.sh              # One-command launch script
│   └── __init__.py
├── environment.py          # OpenEnv core (reset/step/state)
├── graders.py              # 5-component reward scoring
├── multi_agent.py          # Static multi-agent system (no LLM)
├── inference.py            # LLM inference with [START]/[STEP]/[END] logging
├── openenv.yaml            # OpenEnv spec
├── requirements.txt        # Dependencies (serving + training)
├── Dockerfile              # Container config
├── data/
│   ├── manifest.json       # 21 samples with labels
│   └── samples/
│       ├── task1/          # 6 best practices contracts
│       ├── task2/          # 6 gas optimization contracts
│       ├── task3/          # 6 security vulnerability contracts
│       └── task4/          # 3 comprehensive audit contracts
└── README.md
```

## Environment Variables

| Variable | Required | Description |
|----------|:---:|-------------|
| `API_BASE_URL` | For LLM | LLM API endpoint (default: HF router) |
| `MODEL_NAME` | For LLM | Model identifier (default: Qwen2.5-72B) |
| `HF_TOKEN` | For LLM | Hugging Face API key |
| `LLM_BASE_URL` | Optional | Override LLM endpoint for agents |
| `LLM_API_KEY` | Optional | Override API key for agents |
| `GRAPHCODEBERT_PATH` | Optional | Fine-tuned checkpoint dir (default: `training/checkpoints/best`) |
| `GRAPHCODEBERT_THRESHOLD` | Optional | Min confidence to emit a finding (default: `0.5`) |

## Deployment

### Hugging Face Spaces
1. Create a Space with `sdk: docker`
2. Link to this GitHub repo
3. Set environment variables in Space Settings
4. The server starts on port 7860 automatically

### Local Development
```bash
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Notes

- Runtime: ~150s (target: <20 minutes on 2 vCPU / 8 GB)
- All scores are clamped to [0.0, 1.0] for RL stability
- The multi-agent system works without LLM (static analysis mode)
- Dashboard data is computed in real-time from the dataset (no hardcoded metrics)
