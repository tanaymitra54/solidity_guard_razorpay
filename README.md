---
title: ContractSLM
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: mit
short_description: Solidity smart contract security review environment
---

# SolidityGuard

SolidityGuard is an OpenEnv RL environment that trains agents to review Solidity smart contracts for best practices, gas optimizations, and security vulnerabilities.

## Overview

SolidityGuard provides a comprehensive auditing platform for Solidity smart contracts with four tasks:
- **Task 1 (Easy)**: Best Practices & Syntax Issues
- **Task 2 (Medium)**: Gas Optimization Opportunities  
- **Task 3 (Hard)**: Security Vulnerabilities
- **Task 4 (Hard)**: Comprehensive Audit (cross-category)

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
uvicorn app:app --host 0.0.0.0 --port 7860
```

### Run Inference
```bash
python inference.py
```

### Expected Output
Structured logs with `[START]`, `[STEP]`, and `[END]` tags. The final score is reported in the `[END]` log.

## Environment Specification

### Observation Space
- `source_code`: Solidity code string
- `metadata`: contract name, compiler version, file path
- `task_id`: active task

### Action Space
JSON array of findings:
```json
[
  {
    "issue_type": "reentrancy",
    "line_number": 13,
    "description": "State updated after external call",
    "severity": "Critical"
  }
]
```

### Tasks
- Task 1: Best practices and syntax (missing SPDX, old compiler, missing NatSpec, deprecated constructor)
- Task 2: Gas optimization (unbounded loops, redundant storage reads, custom errors)
- Task 3: Security vulnerabilities (reentrancy, missing access control, tx.origin auth)
- Task 4: Comprehensive audit across best practices, gas, and security

## API Endpoints

### POST /reset
Reset environment and get a contract to audit.
```json
{"task_id": "task_1_best_practices"}
```

### POST /step
Submit audit findings and receive score.
```json
{"action": [{"issue_type": "reentrancy", "line_number": 13, "description": "...", "severity": "Critical"}]}
```

### GET /state
Get current environment state.

### GET /health
Health check endpoint.

## Files
- `openenv.yaml` - Environment spec
- `environment.py` - Core env logic (`reset/step/state`)
- `graders.py` - Reward logic and grading
- `data/manifest.json` - Dataset manifest
- `data/samples/` - Solidity contract samples
- `inference.py` - Baseline runner and logging
- `app.py` - FastAPI endpoints for reset/step/state
- `Dockerfile` - Container build

## Notes
- Runtime should stay under 20 minutes on 2 vCPU / 8 GB.
- Docker build must succeed for submission.
- Use Hugging Face Inference Providers for LLM inference.
