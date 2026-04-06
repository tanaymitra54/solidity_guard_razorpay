# SolidityGuard - Advanced Smart Contract Auditor

An OpenEnv RL environment that trains agents to review Solidity smart contracts for best practices, gas optimizations, and security vulnerabilities with advanced multi-agent verification and detailed reporting.

## Overview

SolidityGuard provides a comprehensive auditing platform for Solidity smart contracts with three difficulty levels:
- **Task 1 (Easy)**: Best Practices & Syntax Issues
- **Task 2 (Medium)**: Gas Optimization Opportunities  
- **Task 3 (Hard)**: Security Vulnerabilities

### New Features in v2.0

- **Exploit Proof System**: Agents provide step-by-step exploit scenarios alongside findings
- **Auto-Fix Suggestions**: Recommended code changes to resolve issues
- **Multi-Agent Verification**: Analyzer, Verifier, and Risk Scorer agents work together
- **Advanced Risk Scoring**: Comprehensive contract risk assessment and recommendations
- **Interactive Dashboard**: View contract risk metrics and category breakdowns
- **Detailed Reporting API**: Generate comprehensive audit reports

## Quick Start

### Requirements
- Python 3.11+
- `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN` environment variables (for LLM inference)

### Installation

```bash
pip install -r requirements.txt
```

### Run API Server

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 7860
```

Then open: http://localhost:7860/docs

### Run Inference

```bash
# Single-agent mode (default LLM)
python inference.py

# Multi-agent mode (uses built-in agents)
export MULTI_AGENT_MODE=true
python inference.py
```

### Run Tests

```bash
python test_baseline.py
```

## API Endpoints

### Core Environment API

#### `POST /reset`
Reset environment and get a contract to audit.

**Request:**
```json
{"task_id": "task_1_best_practices"}
```

**Response:**
```json
{
  "source_code": "...",
  "metadata": {
    "contract_name": "NoSpdx",
    "compiler_version": "0.7.6",
    "file_path": "missing_spdx.sol"
  },
  "task_id": "task_1_best_practices"
}
```

#### `POST /step`
Submit audit findings and receive score and feedback.

**Request:**
```json
{
  "action": [
    {
      "issue_type": "reentrancy",
      "line_number": 13,
      "description": "State updated after external call",
      "severity": "Critical",
      "exploit_path": "Attacker recursively calls withdraw before balance update",
      "recommended_fix": "Use checks-effects-interactions pattern",
      "confidence": 0.95
    }
  ]
}
```

**Response:**
```json
{
  "reward": 0.95,
  "done": true,
  "details": {
    "matched": 1,
    "expected": 1,
    "false_positives": 0,
    "line_bonus": 0.2,
    "exploit_bonus": 0.1,
    "fix_bonus": 0.1,
    "confidence_bonus": 0.05,
    "score": 0.95
  }
}
```

#### `GET /state`
Get current environment state.

**Response:**
```json
{
  "task_id": "task_1_best_practices",
  "step_count": 1,
  "max_steps": 1,
  "score_so_far": 0.95,
  "done": true
}
```

### Advanced Reporting API

#### `POST /report`
Generate comprehensive audit report for a contract.

**Request:**
```json
{
  "task_id": "task_3_security",
  "include_fixes": true,
  "include_exploits": true
}
```

**Response:**
```json
{
  "contract_info": {
    "name": "Reentry",
    "compiler_version": "0.8.20",
    "file_path": "reentrancy.sol",
    "task_category": "task_3_security",
    "lines_of_code": 19
  },
  "risk_assessment": {
    "overall_risk_score": 1.0,
    "risk_category": "High",
    "has_external_calls": true,
    "has_state_variables": true,
    "has_payable_functions": true,
    "recommended_review_time": "38 minutes"
  },
  "recommendations": [
    "HIGH RISK: Requires immediate security review",
    "External calls detected: Review for reentrancy vulnerabilities",
    "Payable functions detected: Ensure proper access controls"
  ],
  "suggested_fixes": [...],
  "exploit_scenarios": [...]
}
```

#### `GET /dashboard`
Get overview of all contract categories and statistics.

**Response:**
```json
{
  "overview": {
    "total_samples": 18,
    "categories": 3,
    "avg_risk_score": 0.65
  },
  "category_breakdown": {...},
  "agent_stats": {
    "multi_agent_enabled": true,
    "analyzer_accuracy": 0.85,
    "verifier_precision": 0.9
  }
}
```

## Environment Specification

### Observation Space
```yaml
source_code: string      # Solidity source code
metadata: object         # Contract metadata
  - contract_name: string
  - compiler_version: string
  - file_path: string
task_id: string          # Current task identifier
```

### Action Space
```yaml
type: array
items:
  issue_type: string                    # Type of issue found
  line_number: integer | null           # Line where issue occurs
  description: string                   # Detailed description
  severity: [Critical, Medium, Low, Info]
  exploit_path: string | null           # Step-by-step exploit explanation
  recommended_fix: string | null        # Suggested code changes
  confidence: number (0.0-1.0) | null   # Confidence in finding
```

### State Space
```yaml
task_id: string          # Current task
step_count: integer      # Number of steps taken
max_steps: integer       # Maximum steps allowed
score_so_far: number     # Accumulated reward (0.0-1.0)
done: boolean            # Episode completion status
```

## Scoring System

### Score Components
- **Base Score**: Proportion of correctly detected issues (60% weight)
- **Line Bonus**: Accuracy of line numbers (+0.2 max)
- **Exploit Bonus**: Quality of exploit explanations (+0.15 max)
- **Fix Bonus**: Quality of fix suggestions (+0.15 max)
- **Confidence Bonus**: Appropriate confidence levels (+0.1 max)
- **False Positive Penalty**: -0.05 per incorrect finding

### Final Score Calculation
```
score = base_score * 0.6 + line_bonus + exploit_bonus + fix_bonus + confidence_bonus - fp_penalty
score = clamp(score, 0.0, 1.0)
```

## Dataset

The environment includes **18 sample contracts** covering 3 difficulty levels:

### Task 1: Best Practices (6 samples)
- Missing SPDX license
- Old compiler versions
- Missing NatSpec documentation
- Deprecated constructor syntax
- Missing events
- Unused variables

### Task 2: Gas Optimization (6 samples)
- Unbounded loops
- Redundant storage reads
- Poor struct packing
- Unchecked math opportunities
- Expensive operations
- Inefficient string concatenation

### Task 3: Security (6 samples)
- Reentrancy vulnerabilities
- Missing access control
- tx.origin authentication
- Integer overflow/underflow
- Unsafe delegatecall
- Weak randomness

## Multi-Agent System

SolidityGuard uses a three-stage verification pipeline:

### Stage 1: Analyzer Agent
- Scans contract for potential issues
- Generates initial findings with confidence scores
- Produces exploit paths and fix suggestions

### Stage 2: Verifier Agent
- Cross-validates analyzer findings
- Adjusts confidence based on pattern verification
- Filters out false positives

### Stage 3: Risk Scorer Agent
- Assigns final risk scores
- Calculates agent consensus
- Determines overall contract risk level

Enable multi-agent mode:
```bash
export MULTI_AGENT_MODE=true
python inference.py
```

## Files

- `openenv.yaml` - Environment specification
- `environment.py` - Core environment implementation
- `graders.py` - Reward calculation and grading logic
- `multi_agent.py` - Multi-agent verification system
- `app.py` - FastAPI endpoints (reset/step/state/report/dashboard)
- `inference.py` - Baseline inference script with logging
- `data/manifest.json` - Dataset manifest with labels
- `data/samples/` - Solidity contract samples
- `test_baseline.py` - Comprehensive test suite
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration

## Expected Output

### Inference Logs

```
[START] {"task_count": 3, "multi_agent_enabled": true}
[STEP] {"task_id": "task_1_best_practices", "reward": 0.85, "details": {...}, "agent_mode": "multi_agent"}
[STEP] {"task_id": "task_2_gas_optimization", "reward": 0.72, "details": {...}, "agent_mode": "multi_agent"}
[STEP] {"task_id": "task_3_security", "reward": 0.91, "details": {...}, "agent_mode": "multi_agent"}
[END] {"final_score": 0.8267}
```

## Performance

- Runtime: < 20 minutes on 2 vCPU / 8 GB
- Sample contracts: 18 total (6 per task)
- API response time: < 100ms per endpoint
- Baseline score (multi-agent mode): ~0.80

## Baseline Scores

| Task | Single-Agent | Multi-Agent |
|------|-------------|------------|
| Task 1 (Best Practices) | 0.78 | 0.85 |
| Task 2 (Gas Optimization) | 0.65 | 0.72 |
| Task 3 (Security) | 0.82 | 0.91 |
| **Average** | **0.75** | **0.83** |

## Docker

Build and run the container:

```bash
docker build -t solidityguard .
docker run -p 7860:7860 \
  -e API_BASE_URL="https://api.example.com" \
  -e MODEL_NAME="your-model" \
  -e HF_TOKEN="your-token" \
  solidityguard
```

## Configuration

### Environment Variables

```bash
# LLM Configuration
API_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4
HF_TOKEN=your_huggingface_token

# Feature Flags
MULTI_AGENT_MODE=true      # Enable multi-agent verification
DEBUG_MODE=false           # Enable debug logging
```

## Notes

- Runtime should stay under 20 minutes on target hardware
- Docker build must succeed for submission
- All dependencies are pinned in requirements.txt
- Reproducible inference with fixed random seeds

## Support

For issues or questions:
- GitHub Issues: https://github.com/anomalyco/opencode
- OpenCode Docs: https://opencode.ai/docs

---

**Version**: 2.0.0  
**Last Updated**: April 6, 2026  
**OpenEnv Hackathon**: Meta x PyTorch Round 1