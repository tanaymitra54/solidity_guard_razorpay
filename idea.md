# SolidityGuard - OpenEnv RL Environment

## Project Title
**SolidityGuard** - An OpenEnv RL Environment for Smart Contract Security Review

## Problem Statement
Build an AI agent that learns to review Solidity smart contracts for security vulnerabilities, gas optimization issues, and best practices using the OpenEnv framework.

## Why This Project?
- Real-world utility: Smart contracts hold billions in crypto assets
- Unique & differentiated: Most RL envs are generic code review, Solidity is specialized
- Measurable success: Graders can verify against known vulnerability patterns
- High impact: Automated security review is in high demand in Web3

---

## Environment Design

### Observation Space
- **Input**: Solidity source code (string)
- **Metadata**: Contract name, compiler version, file path

### Action Space
- **Output**: Review comments with severity levels (Critical/Medium/Low/Info)
- **Format**: JSON with `issue_type`, `line_number`, `description`, `severity`

---

## 3 Tasks (Difficulty Levels)

| Task | Difficulty | Focus Area | Examples | Max Score |
|------|------------|------------|----------|-----------|
| Task 1 | Easy | Syntax & Best Practices | Missing SPDX license, old compiler version, missing NatSpec | 0.33 |
| Task 2 | Medium | Gas Optimization | Unchecked external calls, inefficient loops, redundant storage reads | 0.33 |
| Task 3 | Hard | Security Vulnerabilities | Reentrancy, integer overflow, access control issues, tx.origin usage | 0.34 |

---

## Grading System

### Task 1: Syntax & Best Practices (0-0.33)
Grader checks for:
- [ ] SPDX license identifier present
- [ ] Compiler version specified (>=0.8.0)
- [ ] NatSpec comments on public functions
- [ ] No deprecated Solidity features

### Task 2: Gas Optimization (0-0.33)
Grader checks for:
- [ ] Cache storage variables in memory where possible
- [ ] Use of custom errors instead of require strings
- [ ] Loop optimization (avoid unbounded loops)
- [ ] Unchecked external call handling

### Task 3: Security Vulnerabilities (0-0.34)
Grader checks for:
- [ ] Reentrancy guards on sensitive functions
- [ ] Integer overflow/underflow protection
- [ ] Access control on sensitive functions
- [ ] Safe usage of low-level calls
- [ ] No tx.origin usage for authorization

---

## Reward Function

- **Partial Progress**: Points awarded for each correct issue detected
- **Penalty**: Points deducted for false positives (wrongly reported issues)
- **Explanation Bonus**: Extra points for accurate line numbers and helpful descriptions
- **Final Score**: 0.0 to 1.0 scale

---

## Tech Stack

- Python 3.x
- OpenEnv framework
- OpenAI Client for LLM inference
- Hugging Face Spaces + Docker
- Environment variables: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`

---

## Deliverables

1. `openenv.yaml` - Environment specification
2. `environment.py` - Main env implementation with step/reset/state
3. `inference.py` - LLM inference script with [START]/[STEP]/[END] logging
4. `Dockerfile` - Container configuration
5. `README.md` - Setup instructions and documentation
6. Deployed on Hugging Face Spaces

---

## Timeline

| Day | Task |
|-----|------|
| Day 1 | Setup + study OpenEnv templates |
| Day 2 | Design env spec + grader functions |
| Day 3 | Implement step/reset/state methods |
| Day 4 | Create inference.py with logging |
| Day 5 | Deploy to HF Spaces + validate |
| Day 6 | Polish + write README |
| Day 7 | Final validation + submit (Deadline: 8th April) |

---

## Production-Ready Execution Plan

### Objective
Build **SolidityGuard**, a compliant OpenEnv RL environment where an agent audits Solidity contracts for security, gas optimization, and best practices. Must pass all hackathon validators: OpenEnv spec, graders, Docker build, Hugging Face Space, and reproducible `inference.py` with strict logging.

### Scope & Constraints
- Real-world task; no games or toy problems
- Must implement OpenEnv spec: typed models + `reset()/step()/state()` + `openenv.yaml`
- Must include 3 tasks (easy/medium/hard) with graders and rewards in 0.0–1.0
- `inference.py` must exist in repo root, use OpenAI client, and emit strict `[START]/[STEP]/[END]` logs
- Runtime < 20 minutes on 2 vCPU / 8 GB
- Deploy to Hugging Face Spaces + Dockerfile must build

### Environment Design Summary

**Observation**
- `source_code: str`
- `metadata`: contract name, compiler version, file path (optional)
- `task_id`: which task is active

**Action**
- JSON list of findings:
  - `issue_type` (string enum)
  - `line_number` (int or null)
  - `description` (string)
  - `severity` (Critical/Medium/Low/Info)

**State**
- `task_id`
- `step_count`
- `max_steps`
- `score_so_far`
- `done`

### Task Definitions (3 Levels)

**Task 1 (Easy): Best Practices / Syntax**
- SPDX license presence
- compiler version >= 0.8.x
- NatSpec for public functions
- deprecated patterns detection

**Task 2 (Medium): Gas Optimization**
- cache storage vars
- custom errors instead of require strings
- avoid unbounded loops
- safe/efficient external calls

**Task 3 (Hard): Security Vulnerabilities**
- reentrancy detection
- missing access control
- unsafe low-level calls
- no `tx.origin` auth

### Grader Logic
- Partial credit per correct finding
- Penalty for false positives
- Bonus for accurate line numbers (bounded)
- Normalize per task to 0.0–1.0
- Aggregate score across tasks

### Dataset Plan
- 12–20 Solidity snippets total (4–6 per task)
- Each snippet has a ground-truth label set for issues
- Mix of clean and vulnerable examples
- Add control samples with no issues to penalize false positives

### Implementation Plan (Step-By-Step)

**Phase 0 — Scope Lock (0.5 day)**
- Freeze task rubrics
- Lock dataset size + sourcing method
- Define baseline score targets

**Phase 1 — Spec & Schema (1 day)**
- Define typed models for observation/action/state
- Draft `openenv.yaml` with tasks and endpoints
- Validate schema alignment

**Phase 2 — Environment Core (1–2 days)**
- Implement `reset()` to provide a task-specific sample
- Implement `step()` to grade action JSON and produce reward
- Implement `state()` to surface current status
- Ensure deterministic responses

**Phase 3 — Graders + Reward (1–2 days)**
- Implement task graders
- Add partial credit and penalty logic
- Normalize to 0–1
- Unit-test grader outputs

**Phase 4 — Inference Pipeline (1 day)**
- Implement `inference.py`
- Use OpenAI client with `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`
- Emit strict `[START]/[STEP]/[END]` logs with required fields
- Ensure runtime < 20 min

**Phase 5 — Packaging & Deployment (1 day)**
- Dockerfile builds and runs inference
- Deploy to Hugging Face Spaces
- Confirm `/reset` returns 200

**Phase 6 — Validation & Hardening (0.5–1 day)**
- Run pre-submission validation script
- Add input size checks
- Add timeouts and safe error handling
- Pin dependencies for reproducibility

**Phase 7 — Documentation & Release (0.5 day)**
- README with setup, schema, tasks, baseline scores
- Troubleshooting steps
- Submission checklist

### Required Files
- `openenv.yaml`
- `environment.py` (or equivalent)
- `inference.py` (root)
- `Dockerfile`
- `README.md`
- `dataset/` or `samples/` (Solidity snippets + labels)

### Success Criteria
- HF Space deploys and responds to `/reset`
- Docker build passes
- `inference.py` completes under 20 minutes
- Strict log format compliance
- All graders return normalized scores

---

## Sample Test Cases

### Test Case 1: Reentrancy Vulnerability
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vulnerable {
    mapping(address => uint) balances;
    
    function withdraw() public {
        uint bal = balances[msg.sender];
        require(bal > 0);
        
        (bool success, ) = msg.sender.call{value: bal}("");
        require(success);
        
        balances[msg.sender] = 0;
    }
}
```
**Expected**: Agent should detect reentrancy vulnerability (Task 3)

### Test Case 2: Missing Access Control
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AdminContract {
    mapping(address => bool) admins;
    
    function setAdmin(address addr, bool status) public {
        admins[addr] = status;
    }
}
```
**Expected**: Agent should identify missing access control (Task 3)

---

## References

- OpenEnv Framework: https://github.com/raun/openenv-course
- Common Smart Contract Vulnerabilities: Slither, Mythril
- Gas Optimization: Solidity docs, OpenZeppelin

---

*Last Updated: April 3, 2026*
