# Meta x PyTorch Hackathon - Round 1 Guidelines

## Overview

- **Event**: Meta x PyTorch Hackathon by Scaler School of Technology
- **Theme**: Build OpenEnv environments (Reinforcement Learning)
- **Registration**: 14th March - 3rd April
- **Round 1**: 25th March - 8th April
- **Submission Window Opens**: 28th March
- **Finale**: 25th-26th April
- **Submission Deadline**: 8th April 2026, 11:59 PM (confirm timezone on dashboard)

---

## Team Structure

- **Solo**: Compete individually (locked for Round 1 only)
- **Team**: 2-3 members. Only team lead fills the team form.
- Once confirmed, teams cannot be changed.

---

## Round 1 Problem Statement

Build a complete, real-world OpenEnv environment that an AI agent can learn from through the standard `step()` / `reset()` / `state()` API.

### Key Requirements

1. **Must simulate a real-world task** (not games or toys)
2. **Implement full OpenEnv spec**: typed models, `step()/reset()/state()`, `openenv.yaml`
3. **Minimum 3 tasks** with agent graders (easy → medium → hard, scores/reward 0.0–1.0)
4. **Meaningful reward function** with partial progress signals
5. **Baseline inference script** with reproducible scores
6. **Deploy to Hugging Face Spaces** + working Dockerfile
7. **README** with environment description, action/observation spaces, setup instructions

---

## Evaluation Criteria

### Pre-Submission Checklist (All Must Pass)

| Criteria | Description |
|----------|-------------|
| **HF Space deploys** | Automated ping to Space URL must return 200 and respond to `reset()` |
| **OpenEnv spec compliance** | Validate `openenv.yaml`, typed models, `step()/reset()/state()` endpoints |
| **Dockerfile builds** | Automated docker build on submitted repo |
| **Baseline reproduces** | Run inference script — must complete without error and produce scores |
| **3+ tasks with graders** | Enumerate tasks, run each grader, verify scores/reward in 0.0–1.0 range |

---

## Mandatory Additional Instructions

### Environment Variables (Must be defined)

```bash
API_BASE_URL   # The API endpoint for the LLM
MODEL_NAME     # The model identifier to use for inference
HF_TOKEN       # Your Hugging Face API key
```

### Inference Script Requirements

- **Filename**: Must be named `inference.py` in the root directory
- **LLM Client**: Must use OpenAI Client for all LLM calls
- **Logging Format**: Must emit structured stdout logs following `[START]`, `[STEP]`, and `[END]` format (field names, ordering, and formatting are strict)

### Infrastructure Restrictions

- Runtime of inference script should be less than **20 minutes**
- Must work on a machine with **vCPU=2, memory=8GB**

---

## Quick Checklist (Must-Haves)

- HF Space returns 200 and responds to `reset()`
- `openenv.yaml` validates; `step()/reset()/state()` endpoints respond correctly
- Dockerfile builds in CI
- `inference.py` runs end-to-end and produces scores
- 3+ tasks with graders; reward in 0.0–1.0 range
- OpenAI client used for all LLM calls; logs follow strict `[START]/[STEP]/[END]` format

---

## Preparatory Course (4 Modules ~3.5 hours)

| Module | Title | Duration |
|--------|-------|----------|
| 1 | Why OpenEnv? | 45 min |
| 2 | Using Existing Environments | 50 min |
| 3 | Deploying Environments | 45 min |
| 4 | Building Your Own Environment | 60 min |

**Note**: Each module - read the README first, then open the notebook in Colab. No local setup needed.

[Course Repository](https://github.com/raun/openenv-course/tree/main)

---

## How to Submit

1. Complete Step 1 (Team/Solo selection)
2. Build your OpenEnv environment
3. Deploy to Hugging Face Spaces
4. Run pre-submission validation script
5. Submit via dashboard (only team leaders can submit)

---

## What Happens After Round 1

- Results announced: 10th April
- Finale: 25th-26th April

---

## Need Help?

- **Email**: help_openenvhackathon@scaler.com
- **Discord**: Join the community for announcements, mentor access, and team matching
- **Discord Link**: https://discord.gg/Dedhy5pkWD

---

## Example Problem Statement Format

> "Build a real-world task environment (e.g., incident triage or logistics scheduling) with clearly defined tasks, automated graders, and reward logic using the OpenEnv framework."

### Expected Deliverables:
- Create an environment an AI agent can interact with
- Define tasks with increasing difficulty
- Write graders that verify task completion
- Define reward logic for scoring
- Package using OpenEnv for automated evaluation

### Evaluation Areas:
- **Runtime correctness**: Runs without errors
- **Interface compliance**: Follows OpenEnv standard
- **Task design**: Clear, realistic, testable
- **Grading logic**: Reward system makes sense

---

## Resources

- [OpenEnv Course Repository](https://github.com/raun/openenv-course/tree/main)
- [Join Discord Community](https://discord.gg/Dedhy5pkWD)
- [Contact Support](mailto:help_openenvhackathon@scaler.com)

---

*Last Updated: April 3, 2026*
