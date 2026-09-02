"""
Graph CodeBERT vulnerability detector for the audit pipeline.

Loads a fine-tuned checkpoint (sequence classification) and emits a Finding
when top-1 class is not "safe" and confidence >= threshold.

Env:
  GRAPHCODEBERT_PATH       local dir or HF Hub ID
                           default: training/checkpoints/best
                           example: tanaymitra01/graphcodebert-vulnerability-detector
  GRAPHCODEBERT_THRESHOLD  default: 0.5
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agents.base import Finding, get_logger

_log = get_logger("agents.graphcodebert")

DEFAULT_PATH = "training/checkpoints/best"
DEFAULT_THRESHOLD = 0.5

_SEVERITY: Dict[str, str] = {
    "reentrancy": "Critical",
    "access_control": "Critical",
    "tx_origin_auth": "Critical",
    "integer_overflow": "Critical",
    "unsafe_delegatecall": "Critical",
    "weak_randomness": "Medium",
    "unbounded_loop": "Medium",
    "redundant_storage": "Low",
    "gas_optimization": "Low",
    "best_practice": "Low",
    "other": "Medium",
}

_lock = threading.Lock()
_detector: Optional["GraphCodeBERTDetector"] = None


class GraphCodeBERTDetector:
    """Lazy-loaded Graph CodeBERT classifier."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> None:
        self.model_path = model_path or os.getenv("GRAPHCODEBERT_PATH", DEFAULT_PATH)
        self.threshold = (
            threshold
            if threshold is not None
            else float(os.getenv("GRAPHCODEBERT_THRESHOLD", str(DEFAULT_THRESHOLD)))
        )
        self._model: Any = None
        self._tokenizer: Any = None
        self._id2label: Dict[int, str] = {}
        self._device: Any = None
        self._load_error: Optional[str] = None
        self._tried_load = False

    @property
    def loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    def status(self) -> Dict[str, Any]:
        """Health-friendly status (does not force a load)."""
        path = Path(self.model_path)
        exists = path.exists()
        is_hub_id = (not exists) and ("/" in self.model_path) and not self.model_path.startswith(".")
        warning = self._load_error
        if warning is None and not exists and not is_hub_id and not self.loaded:
            warning = f"checkpoint missing: {path}"
        return {
            "enabled": True,
            "loaded": self.loaded,
            "path": str(self.model_path),
            "path_exists": exists or is_hub_id,
            "hub_id": is_hub_id,
            "threshold": self.threshold,
            "warning": warning,
        }

    def _ensure_loaded(self) -> bool:
        if self.loaded:
            return True
        if self._tried_load:
            return False

        with _lock:
            if self.loaded:
                return True
            if self._tried_load:
                return False
            self._tried_load = True

            model_ref = self.model_path
            local_path = Path(model_ref)
            is_local = local_path.exists()
            # Allow Hugging Face Hub IDs like "user/repo" when no local path exists.
            is_hub_id = (not is_local) and ("/" in model_ref) and not model_ref.startswith(".")
            if not is_local and not is_hub_id:
                self._load_error = f"checkpoint missing: {model_ref}"
                _log.warning("gcb_not_loaded", error=self._load_error)
                return False

            try:
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                load_from = str(local_path) if is_local else model_ref
                self._tokenizer = AutoTokenizer.from_pretrained(load_from)
                self._model = AutoModelForSequenceClassification.from_pretrained(load_from)
                self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self._model.to(self._device)
                self._model.eval()

                # Prefer local checkpoint label map, else model config / hub files
                label_map_path = local_path / "label_map.json" if is_local else None
                if label_map_path is not None and label_map_path.exists():
                    import json

                    with open(label_map_path) as f:
                        lm = json.load(f)
                    raw = lm.get("id2label") or {
                        str(i): lab for i, lab in enumerate(lm.get("labels", []))
                    }
                    self._id2label = {int(k): v for k, v in raw.items()}
                else:
                    # Try downloading label_map.json from the Hub when using a remote ID
                    if is_hub_id:
                        try:
                            import json
                            from huggingface_hub import hf_hub_download

                            lm_file = hf_hub_download(repo_id=model_ref, filename="label_map.json")
                            with open(lm_file) as f:
                                lm = json.load(f)
                            raw = lm.get("id2label") or {
                                str(i): lab for i, lab in enumerate(lm.get("labels", []))
                            }
                            self._id2label = {int(k): v for k, v in raw.items()}
                        except Exception:
                            self._id2label = {}
                    if not self._id2label:
                        cfg = getattr(self._model, "config", None)
                        if cfg and getattr(cfg, "id2label", None):
                            self._id2label = {int(k): v for k, v in cfg.id2label.items()}
                        else:
                            from training.dataset import VULN_ID2LABEL

                            self._id2label = dict(VULN_ID2LABEL)

                self._load_error = None
                _log.info("gcb_loaded", path=load_from, device=str(self._device))
                return True
            except Exception as exc:
                self._model = None
                self._tokenizer = None
                self._load_error = str(exc)
                _log.warning("gcb_load_failed", error=str(exc))
                return False

    def predict(self, source_code: str) -> Optional[Tuple[str, float]]:
        """Return (label, confidence) for top-1, or None if unavailable."""
        if not self._ensure_loaded():
            return None
        import torch

        enc = self._tokenizer(
            source_code,
            max_length=512,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        enc = {k: v.to(self._device) for k, v in enc.items()}
        with torch.no_grad():
            logits = self._model(**enc).logits
            probs = torch.softmax(logits, dim=-1)[0]
            conf, idx = torch.max(probs, dim=-1)
        label = self._id2label.get(int(idx.item()), "other")
        return label, float(conf.item())

    def scan(self, source_code: str) -> List[Finding]:
        """Top-1 finding if not safe and confidence >= threshold."""
        result = self.predict(source_code)
        if result is None:
            return []
        label, confidence = result
        if label == "safe" or confidence < self.threshold:
            return []
        return [
            Finding(
                issue_type=label,
                line_number=None,
                severity=_SEVERITY.get(label, "Medium"),
                description=(
                    f"Graph CodeBERT predicted '{label}' "
                    f"(confidence={confidence:.3f})"
                ),
                confidence=confidence,
                source="graphcodebert",
                metadata={"model_path": self.model_path},
            )
        ]


def get_detector() -> GraphCodeBERTDetector:
    global _detector
    if _detector is None:
        with _lock:
            if _detector is None:
                _detector = GraphCodeBERTDetector()
    return _detector


def gcb_status() -> Dict[str, Any]:
    return get_detector().status()


def scan_with_graphcodebert(source_code: str) -> List[Finding]:
    return get_detector().scan(source_code)


if __name__ == "__main__":
    # ponytail: one runnable check — fails if status shape breaks
    d = GraphCodeBERTDetector(model_path="/nonexistent/gcb-checkpoint")
    st = d.status()
    assert st["loaded"] is False
    assert st["path_exists"] is False
    assert st["warning"]
    assert d.scan("contract C {}") == []
    print("graphcodebert self-check OK", st)
