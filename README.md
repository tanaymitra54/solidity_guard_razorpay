# SolidityGuard

SolidityGuard is an OpenEnv RL environment that trains agents to review Solidity smart contracts for best practices, gas optimizations, and security vulnerabilities.

## Quick Start

### Requirements
- Python 3.11+
- `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN` set in the environment

### Install
```bash
pip install -r requirements.txt
```

### Run Inference
```bash
python inference.py
```

### Run API Server
```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

### Expected Output
Structured logs with `[START]`, `[STEP]`, and `[END]` tags. The final score is reported in the `[END]` log.

## Environment Overview

### Observation
- `source_code`: Solidity code string
- `metadata`: contract name, compiler version, file path
- `task_id`: active task

### Action
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
- Task 1: Best practices and syntax
- Task 2: Gas optimization
- Task 3: Security vulnerabilities

## Files
- `openenv.yaml`: Environment spec
- `environment.py`: Core env logic (`reset/step/state`)
- `graders.py`: Reward logic and grading
- `data/manifest.json`: Dataset manifest
- `inference.py`: Baseline runner and logging
- `app.py`: FastAPI endpoints for reset/step/state
- `Dockerfile`: Container build

## Notes
- Runtime should stay under 20 minutes on 2 vCPU / 8 GB.
- Docker build must succeed for submission.