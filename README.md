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

<div align="center">

# SolidityGuard

**Slither + Graph CodeBERT + LLM agents — one OpenEnv you can score, demo, and train.**

[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-compliant-0ea5e9)](./openenv.yaml)
[![Docker](https://img.shields.io/badge/Docker-HF%20Spaces-2496ED?logo=docker&logoColor=white)](./Dockerfile)
[![Model](https://img.shields.io/badge/HF-Graph%20CodeBERT-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co/tanaymitra01/graphcodebert-vulnerability-detector)

Paste Solidity → multi-agent audit → findings with severity, confidence, Foundry PoCs & fixes — **plus** a clamped RL reward in `[0, 1]`.

[**Live demo**](#-demo-in-60-seconds) · [**GitHub**](https://github.com/tanaymitra54/solidity_guard_razorpay) · [**Model card**](https://huggingface.co/tanaymitra01/graphcodebert-vulnerability-detector) · [**Author: Tanay Mitra**](https://github.com/tanaymitra54)

</div>

---

## At a glance

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'pie1': '#ef4444', 'pie2': '#f59e0b', 'pie3': '#22c55e'}}}%%
pie showData
    title In-repo label severity (49 issues)
    "Critical" : 18
    "Medium" : 13
    "Low" : 18
```

```mermaid
%%{init: {'theme': 'neutral'}}%%
xychart-beta
    title "Samples per task (21 contracts)"
    x-axis ["Best practices", "Gas", "Security", "Comprehensive"]
    y-axis "Samples" 0 --> 8
    bar [6, 6, 6, 3]
```

| Signal | Value |
|--------|------:|
| Labeled contracts (OpenEnv) | **21** |
| Labeled issues | **49** |
| Task tiers | **4** |
| GCB train cap (Wild) | **5,000** |
| GCB held-out accuracy | **~56%** |
| GCB held-out macro-F1 | **~0.47** |
| Reward range | **[0.0, 1.0]** |

> **Honest scope:** Graph CodeBERT is a **screening** model on tool-consensus Wild labels — not a human audit replacement. It runs **beside** Slither & patterns; missing weights never crash the API.

---

## Why this wins

```mermaid
quadrantChart
    title Where SolidityGuard sits
    x-axis "Detectors only" --> "Detectors + agents + RL"
    y-axis "Closed / paid" --> "Open / self-hosted"
    quadrant-1 Prize zone
    quadrant-2 Research tools
    quadrant-3 Legacy scanners
    quadrant-4 Cloud SaaS
    SolidityGuard: [0.85, 0.88]
    Slither: [0.25, 0.82]
    Mythril: [0.30, 0.75]
    Securify2: [0.28, 0.70]
    MythX: [0.55, 0.25]
```

| Market gap | SolidityGuard |
|------------|---------------|
| Static tools = detectors only | Detectors **+** LLM explain / PoC / fix |
| MythX = paid cloud | Self-hosted, **MIT**, Docker / HF Spaces |
| ChatGPT paste = no grader | OpenEnv `reset` / `step` → reward **∈ [0, 1]** |
| No learned first-pass on your stack | Fine-tuned **Graph CodeBERT** in the scanner |

### Feature matrix

| Feature | SolidityGuard | Slither | Mythril | MythX | Securify2 |
|---------|:---:|:---:|:---:|:---:|:---:|
| Multi-agent pipeline | ✅ | ❌ | ❌ | ❌ | ❌ |
| LLM explain / fix | ✅ | ❌ | ❌ | ◐ | ❌ |
| Fine-tuned Graph CodeBERT | ✅ | ❌ | ❌ | ❌ | ❌ |
| Foundry-style PoC drafts | ✅ | ❌ | ❌ | ❌ | ❌ |
| Gas + practices + security | ✅ | ✅ | ◐ | ✅ | ◐ |
| RL / OpenEnv rewards | ✅ | ❌ | ❌ | ❌ | ❌ |
| Self-hosted MIT | ✅ | ✅ | ✅ | ❌ | ✅ |

*◐ = partial*

---

## System map

```mermaid
flowchart TB
    subgraph Clients
        UI[Browser /demo]
        AG[RL agent / inference.py]
        CURL[curl / Swagger]
    end

    subgraph API["FastAPI · port 7860"]
        H["/health /dashboard"]
        R["/reset /step /state"]
        A["/audit /report"]
    end

    subgraph Agents
        ORCH[Orchestrator]
        SC[Scanner]
        GCB[Graph CodeBERT]
        AN[Analyzer]
        EX[ExploitGen]
        FX[FixSuggester]
    end

    subgraph Core
        ENV[environment.py]
        GR[graders.py]
        DATA[(manifest + samples)]
        CKPT[(HF Hub / checkpoints/best)]
    end

    UI --> H
    UI --> A
    CURL --> A
    AG --> R
    R --> ENV
    ENV --> GR
    ENV --> DATA
    A --> ORCH
    ORCH --> SC
    ORCH --> AN
    ORCH --> EX
    ORCH --> FX
    SC --> GCB
    GCB --> CKPT
```

### Audit request lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant API as FastAPI
    participant O as Orchestrator
    participant S as Scanner + GCB
    participant A as Analyzer
    participant E as Exploit / Fix

    C->>API: POST /audit {source_code}
    API->>O: analyze(source)
    O->>S: patterns ∥ Slither ∥ Graph CodeBERT
    S-->>O: merged findings
    O->>A: deep LLM pass
    A-->>O: verified findings
    par Critical path
        O->>E: Foundry PoC draft
        O->>E: fix suggestion
    end
    E-->>O: PoCs + patches
    O-->>API: AuditResult + metrics
    API-->>C: JSON
```

### OpenEnv RL loop

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Loaded: POST /reset
    Loaded --> Scored: POST /step(findings)
    Scored --> Loaded: next episode
    Scored --> Idle: done

    note right of Loaded
      observation:
      source_code, metadata, task_id
    end note
    note right of Scored
      reward ∈ [0, 1]
      from graders.py
    end note
```

---

## Pipeline (one contract)

```mermaid
flowchart LR
    SOL[Solidity source] --> P[Pattern scan]
    SOL --> SL[Slither]
    SOL --> GCB[Graph CodeBERT<br/>12-class]
    P --> M[Merge · dedupe]
    SL --> M
    GCB --> M
    M --> AN[Analyzer LLM]
    AN --> EX[ExploitGen]
    AN --> FX[FixSuggester]
    M --> OUT[AuditResult]
    AN --> OUT
    EX --> OUT
    FX --> OUT
```

```mermaid
mindmap
  root((SolidityGuard))
    Scanner
      Patterns
      Slither
      Graph CodeBERT
    Analyzer
      LLM deep pass
    Remediation
      Foundry PoC
      Fix sketch
    OpenEnv
      reset / step
      5-part grader
```

---

## Tasks & dataset

| Task | Difficulty | Focus | n |
|------|:---:|-------|:-:|
| `task_1_best_practices` | Easy | SPDX, NatSpec, pragma, deprecated patterns | 6 |
| `task_2_gas_optimization` | Medium | Loops, storage, packing, custom errors | 6 |
| `task_3_security` | Hard | Reentrancy, access control, `tx.origin`, delegatecall, randomness | 6 |
| `task_4_comprehensive_audit` | Hard | Mixed cross-category | 3 |

```mermaid
flowchart LR
    T1[Task 1 Easy<br/>Best practices] --> T2[Task 2 Medium<br/>Gas]
    T2 --> T3[Task 3 Hard<br/>Security]
    T3 --> T4[Task 4 Hard<br/>Comprehensive]
```

---

## Scoring (RL-stable)

```mermaid
flowchart TB
    F[Submitted findings] --> B[Base match<br/>max 0.6]
    F --> L[Line accuracy<br/>+0.2]
    F --> E[Exploit text<br/>+0.15]
    F --> X[Fix text<br/>+0.15]
    F --> C[Confidence<br/>+0.1]
    F --> P[FP penalty<br/>−0.05 each]
    B --> S[Sum]
    L --> S
    E --> S
    X --> S
    C --> S
    P --> S
    S --> CLAMP["clamp → [0.0, 1.0]"]
```

| Component | Cap | Role |
|-----------|:---:|------|
| Base match | 0.6 | Matched / expected |
| Line accuracy | +0.2 | Near-exact lines |
| Exploit text | +0.15 | Attack narrative |
| Fix text | +0.15 | Actionable patch |
| Confidence | +0.1 | Calibrated scores |
| False positive | −0.05 ea. | Extra unmatched |

---

## Graph CodeBERT training

```mermaid
flowchart TD
    W[SmartBugs-Wild ~47k] --> CAP["Cap WILD_LIMIT = 5000"]
    META[Tool results<br/>consensus ≥ 2] --> LAB[Labels]
    CAP --> MERGE[combined.json]
    LAB --> MERGE
    MERGE --> SPLIT[70% / 15% / 15%]
    SPLIT --> FT[Fine-tune graphcodebert-base]
    FT --> BEST[checkpoints/best]
    BEST --> HUB[Hugging Face Hub]
    BEST --> LFS[Git LFS]
```

```mermaid
flowchart LR
    SRC[Solidity text] --> TOK[Tokenizer · 512]
    TOK --> ENC[Graph CodeBERT]
    ENC --> CLS["[CLS] 768-d"]
    CLS --> LIN[Linear → 12]
    LIN --> OUT[label + confidence]
```

**Classes:** `safe` · `reentrancy` · `access_control` · `tx_origin_auth` · `integer_overflow` · `unsafe_delegatecall` · `weak_randomness` · `unbounded_loop` · `redundant_storage` · `gas_optimization` · `best_practice` · `other`

```bash
bash training/run.sh
# WILD_LIMIT=2000 bash training/run.sh

export GRAPHCODEBERT_PATH=tanaymitra01/graphcodebert-vulnerability-detector
# or: export GRAPHCODEBERT_PATH=training/checkpoints/best
```

---

## Quick start

```bash
git clone https://github.com/tanaymitra54/solidity_guard_razorpay.git
cd solidity_guard_razorpay
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GRAPHCODEBERT_PATH=tanaymitra01/graphcodebert-vulnerability-detector
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

| URL | What |
|-----|------|
| http://localhost:7860 | Landing |
| http://localhost:7860/demo | Interactive audit |
| http://localhost:7860/docs | Swagger |
| http://localhost:7860/health | GCB + dataset status |

---

## Demo in 60 seconds

```bash
curl -s http://localhost:7860/health | python3 -m json.tool

curl -s -X POST http://localhost:7860/audit \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "pragma solidity ^0.8.0; contract V { mapping(address=>uint) b; function withdraw() public { uint x=b[msg.sender]; msg.sender.call{value:x}(\"\"); b[msg.sender]=0; } }",
    "generate_exploits": false,
    "generate_fixes": false
  }'
```

Or paste `data/samples/task3/reentrancy.sol` into **`/demo`**. Findings with `"source": "graphcodebert"` mean the neural pass fired (confidence ≥ threshold, default `0.5`).

---

## API

| Method | Path | Role |
|--------|------|------|
| GET | `/` | Landing |
| GET | `/demo` | Live audit UI |
| GET | `/health` | Uptime · dataset · GCB |
| GET | `/dashboard` | Analytics |
| GET | `/state` | Env state |
| POST | `/reset` | OpenEnv episode |
| POST | `/step` | Findings → reward |
| POST | `/audit` | Full pipeline |
| POST | `/report` | Rich report |
| GET | `/docs` | OpenAPI |

---

## Environment

| Variable | Need | Meaning |
|----------|:---:|---------|
| `GRAPHCODEBERT_PATH` | Optional | Hub id or local checkpoint |
| `GRAPHCODEBERT_THRESHOLD` | Optional | Default `0.5` |
| `API_BASE_URL` · `MODEL_NAME` · `HF_TOKEN` | LLM | Agents / inference |
| `LLM_BASE_URL` · `LLM_API_KEY` | Optional | Overrides |
| `WILD_LIMIT` | Training | Default `5000` |

---

## Repo layout

```
solidity_guard_razorpay/
├── server/app.py                 # FastAPI :7860
├── agents/                       # orchestrator · scanner · graphcodebert · …
├── training/                     # run.sh · download · train · checkpoints/best
├── environment.py · graders.py · inference.py · openenv.yaml
├── data/manifest.json · samples/task{1,2,3,4}/
└── Dockerfile
```

---

## Deploy

```mermaid
flowchart LR
    GH[GitHub] --> SP[HF Space · Docker]
    HF[Hub weights] --> SP
    SP --> PUB[Public :7860]
```

1. Create Space with `sdk: docker`  
2. Link this repo  
3. Set `GRAPHCODEBERT_PATH` (+ LLM secrets if needed)  
4. Serve on **7860**

---

## Notes

- `inference.py` targets **&lt; 20 min** on modest CPU with `[START]` / `[STEP]` / `[END]`  
- `multi_agent.py` works **without** an LLM  
- Wild labels = tool consensus → GCB is for **screening**  
- Caches gitignored; weights on **Git LFS** + **Hugging Face**

---

## Citation

```bibtex
@misc{solidityguard2026,
  title  = {SolidityGuard: OpenEnv RL Environment for Smart Contract Security Review},
  author = {Tanay Mitra},
  year   = {2026},
  url    = {https://github.com/tanaymitra54/solidity_guard_razorpay}
}
```

<div align="center">

**SolidityGuard** · MIT · Built by [Tanay Mitra](https://github.com/tanaymitra54)

</div>
