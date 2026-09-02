---
license: mit
library_name: transformers
pipeline_tag: text-classification
base_model: microsoft/graphcodebert-base
tags:
  - code
  - solidity
  - smart-contracts
  - vulnerability-detection
  - graphcodebert
  - roberta
language:
  - en
metrics:
  - accuracy
  - f1
model-index:
  - name: graphcodebert-vulnerability-detector
    results:
      - task:
          type: text-classification
          name: Solidity vulnerability classification
        dataset:
          name: SmartBugs-Wild (subset, tool-consensus labels)
          type: smartbugs-wild
        metrics:
          - type: accuracy
            value: 0.5622
            name: Test accuracy
          - type: f1
            value: 0.4655
            name: Macro F1
---

# Graph CodeBERT — Solidity Vulnerability Detector

Fine-tuned [`microsoft/graphcodebert-base`](https://huggingface.co/microsoft/graphcodebert-base) for **Solidity smart-contract vulnerability type classification**.

Part of [SolidityGuard](https://github.com/tanaymitra54/solidity_guard_razorpay) — used as a first-pass detector alongside Slither and an LLM auditor.

## How it fits in SolidityGuard

1. **Input:** Solidity source  
2. **Detectors:** Slither / patterns + **this Graph CodeBERT model**  
3. **LLM agents:** Scanner → Analyzer → Exploit Gen / Fix Suggester  
4. **Output:** Audit findings with severity and confidence  

## Model

- Tokenizer → `max_length=512`  
- Graph CodeBERT encoder (~125M params)  
- Linear classification head → 12-class softmax → label + confidence  

## Training

1. SmartBugs-Wild contracts (capped at 5,000)  
2. Labels from SmartBugs-Results tool consensus (≥2 tools agree on a category; else `safe`)  
3. Split 70 / 15 / 15 (train / val / test) with light augmentation  
4. Fine-tune `microsoft/graphcodebert-base` with early stopping on validation macro-F1  
5. Best checkpoint published here  

## Intended use

- Input: Solidity source code (string)  
- Output: one of 12 labels + confidence  
- Best as a **screening** signal, not a sole security audit  

## Labels

| ID | Label | Typical severity hint |
|----|-------|------------------------|
| 0 | `safe` | — |
| 1 | `reentrancy` | Critical |
| 2 | `access_control` | Critical |
| 3 | `tx_origin_auth` | Critical |
| 4 | `integer_overflow` | Critical |
| 5 | `unsafe_delegatecall` | Critical |
| 6 | `weak_randomness` | Medium |
| 7 | `unbounded_loop` | Medium |
| 8 | `redundant_storage` | Low |
| 9 | `gas_optimization` | Low |
| 10 | `best_practice` | Low |
| 11 | `other` | Medium |

## Held-out test metrics

| Metric | Value |
|--------|-------|
| Accuracy | 0.562 |
| Macro F1 | 0.466 |
| F1 `safe` | 0.694 |
| F1 `integer_overflow` | 0.634 |
| F1 `reentrancy` | 0.461 |
| F1 `other` | 0.340 |
| F1 `access_control` | 0.200 |

Labels are noisy (static-analysis consensus), so scores are moderate by design.

## Quick start

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

repo = "tanaymitra01/graphcodebert-vulnerability-detector"
tok = AutoTokenizer.from_pretrained(repo)
model = AutoModelForSequenceClassification.from_pretrained(repo)
model.eval()

code = """
pragma solidity ^0.8.0;
contract Vault {
    mapping(address => uint) public bal;
    function withdraw() public {
        uint amount = bal[msg.sender];
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok);
        bal[msg.sender] = 0;
    }
}
"""
inputs = tok(code, return_tensors="pt", truncation=True, max_length=512)
with torch.no_grad():
    probs = torch.softmax(model(**inputs).logits, dim=-1)[0]
pred = int(probs.argmax())
print(model.config.id2label[pred], float(probs[pred]))
```

### With SolidityGuard

```bash
export GRAPHCODEBERT_PATH=tanaymitra01/graphcodebert-vulnerability-detector
```

## Where to get the weights

| Location | Path |
|----------|------|
| **Hugging Face (recommended)** | [`tanaymitra01/graphcodebert-vulnerability-detector`](https://huggingface.co/tanaymitra01/graphcodebert-vulnerability-detector) |
| GitHub LFS | [`training/checkpoints/best/`](https://github.com/tanaymitra54/solidity_guard_razorpay/tree/main/training/checkpoints/best) in the SolidityGuard repo |

## Files

- `model.safetensors` — weights  
- `config.json` — RobertaForSequenceClassification config + label maps  
- `label_map.json` — label list / id maps used in training  
- `README.md` — this model card  

## Limitations

- Tool-derived labels ≠ audited ground truth  
- Truncation at 512 tokens; large contracts lose context  
- Rare classes (e.g. access control) have low F1  
- Not a replacement for professional security review  

## Citation

```bibtex
@misc{solidityguard-graphcodebert,
  title  = {Graph CodeBERT Vulnerability Detector for Solidity},
  author = {Tanay Mitra},
  year   = {2026},
  url    = {https://huggingface.co/tanaymitra01/graphcodebert-vulnerability-detector}
}
```
