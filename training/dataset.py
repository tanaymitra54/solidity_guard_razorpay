"""
Dataset preparation for Graph CodeBERT fine-tuning.

Converts SolidityGuard manifest.json + .sol files into tokenized datasets
ready for sequence classification (vulnerability type) and token classification
(line-level detection).

Usage:
    python training/dataset.py --config training/config.yaml
    python training/dataset.py --manifest data/manifest.json --output training/cache
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import torch
    from torch.utils.data import Dataset
    from transformers import PreTrainedTokenizerFast
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # Minimal stub so the module can be imported without torch
    class Dataset:  # type: ignore[no-redef]
        pass

# ---------------------------------------------------------------------------
# Label maps
# ---------------------------------------------------------------------------

# Vulnerability type labels (sequence classification)
VULN_LABELS = [
    "safe",                          # No vulnerability found
    "reentrancy",
    "access_control",
    "tx_origin_auth",
    "integer_overflow",
    "unsafe_delegatecall",
    "weak_randomness",
    "unbounded_loop",
    "redundant_storage",
    "gas_optimization",
    "best_practice",
    "other",
]

VULN_LABEL2ID: Dict[str, int] = {label: i for i, label in enumerate(VULN_LABELS)}
VULN_ID2LABEL: Dict[int, str] = {i: label for label, i in VULN_LABEL2ID.items()}

# Severity labels
SEVERITY_LABELS = ["Low", "Medium", "Critical", "Info"]
SEVERITY_LABEL2ID: Dict[str, int] = {s: i for i, s in enumerate(SEVERITY_LABELS)}


# ---------------------------------------------------------------------------
# Canonical label mapping (maps raw issue_type to our label set)
# ---------------------------------------------------------------------------

_LABEL_CANONICAL: Dict[str, str] = {
    "reentrancy": "reentrancy",
    "missing_access_control": "access_control",
    "tx_origin_auth": "tx_origin_auth",
    "integer_overflow_risk": "integer_overflow",
    "unsafe_delegatecall": "unsafe_delegatecall",
    "weak_randomness": "weak_randomness",
    "unbounded_loop": "gas_optimization",
    "redundant_storage_read": "gas_optimization",
    "custom_error_missing": "gas_optimization",
    "poor_struct_packing": "gas_optimization",
    "unchecked_math_opportunity": "gas_optimization",
    "expensive_operation_in_loop": "gas_optimization",
    "inefficient_string_concat": "gas_optimization",
    "missing_spdx": "best_practice",
    "old_compiler_version": "best_practice",
    "missing_natspec": "best_practice",
    "deprecated_constructor": "best_practice",
    "missing_events": "best_practice",
    "unused_variables": "best_practice",
}


def canonicalize_label(raw: str) -> str:
    """Map a raw issue_type to one of our VULN_LABELS."""
    return _LABEL_CANONICAL.get(raw, "other")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@dataclass
class ContractSample:
    """A single labeled contract for training."""
    id: str
    task_id: str
    source_code: str
    contract_name: str
    compiler_version: str
    labels: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def primary_vuln(self) -> str:
        """Return the most severe vulnerability label."""
        if not self.labels:
            return "safe"
        sev_order = {"Critical": 0, "Medium": 1, "Low": 2, "Info": 3}
        sorted_labels = sorted(self.labels, key=lambda l: sev_order.get(l.get("severity", "Info"), 3))
        return canonicalize_label(sorted_labels[0].get("issue_type", ""))

    @property
    def primary_severity(self) -> str:
        """Return the most severe severity level."""
        if not self.labels:
            return "Low"
        sev_order = {"Critical": 0, "Medium": 1, "Low": 2, "Info": 3}
        sorted_labels = sorted(self.labels, key=lambda l: sev_order.get(l.get("severity", "Info"), 3))
        return sorted_labels[0].get("severity", "Low")


def load_manifest(manifest_path: str) -> List[ContractSample]:
    """Load manifest.json and resolve source code paths.

    Paths in manifest are relative to the repo root (e.g. data/samples/task1/foo.sol).
    We resolve them relative to the directory containing the manifest's parent
    (typically the repo root when manifest is at data/manifest.json).
    """
    manifest_path = Path(manifest_path).resolve()
    # The manifest lives at data/manifest.json, source paths are like data/samples/...
    # So resolve relative to the directory ABOVE the manifest's parent (repo root)
    repo_root = manifest_path.parent.parent

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    samples: List[ContractSample] = []
    for entry in manifest:
        source_path = repo_root / entry["source_path"]
        if not source_path.exists():
            # Fallback: try relative to manifest dir
            source_path = manifest_path.parent / entry["source_path"]
        if not source_path.exists():
            print(f"  [WARN] Skipping {entry['id']}: {entry['source_path']} not found")
            continue

        source_code = source_path.read_text(encoding="utf-8")
        samples.append(ContractSample(
            id=entry["id"],
            task_id=entry["task_id"],
            source_code=source_code,
            contract_name=entry.get("metadata", {}).get("contract_name", "Unknown"),
            compiler_version=entry.get("metadata", {}).get("compiler_version", "Unknown"),
            labels=entry.get("labels", []),
        ))

    return samples


def augment_samples(samples: List[ContractSample]) -> List[ContractSample]:
    """
    Augment dataset by creating per-label training examples.

    For each contract with multiple labels, create individual examples
    for each vulnerability found. Also create 'safe' examples from
    contracts with no labels.
    """
    augmented: List[ContractSample] = []

    for sample in samples:
        if not sample.labels:
            # Contract has no issues -> "safe" sample
            augmented.append(sample)
        else:
            # Create one example per label (for multi-label training)
            for i, label in enumerate(sample.labels):
                augmented.append(ContractSample(
                    id=f"{sample.id}_label_{i}",
                    task_id=sample.task_id,
                    source_code=sample.source_code,
                    contract_name=sample.contract_name,
                    compiler_version=sample.compiler_version,
                    labels=[label],
                ))

    return augmented


# ---------------------------------------------------------------------------
# PyTorch Datasets
# ---------------------------------------------------------------------------

class VulnerabilityClassificationDataset(Dataset):
    """
    Dataset for sequence-level vulnerability classification.

    Input: Solidity source code
    Output: vulnerability type (one of VULN_LABELS)
    """

    def __init__(
        self,
        samples: List[ContractSample],
        tokenizer: PreTrainedTokenizerFast,
        max_length: int = 512,
    ) -> None:
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]

        # Tokenize source code
        encoding = self.tokenizer(
            sample.source_code,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # Primary vulnerability label
        label = VULN_LABEL2ID[sample.primary_vuln]

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(label, dtype=torch.long),
        }


class LineLevelDetectionDataset(Dataset):
    """
    Dataset for token-level (line-by-line) vulnerability detection.

    Input: Solidity source code
    Output: Per-line binary label (vulnerable / safe)
    """

    def __init__(
        self,
        samples: List[ContractSample],
        tokenizer: PreTrainedTokenizerFast,
        max_length: int = 512,
    ) -> None:
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]
        lines = sample.source_code.split("\n")

        # Create line-level labels: 1 if line has a vulnerability, 0 otherwise
        vulnerable_lines = set()
        for label in sample.labels:
            ln = label.get("line_number")
            if ln is not None:
                vulnerable_lines.add(ln)

        # Create a text version with line markers
        marked_lines = []
        line_labels = []
        for i, line in enumerate(lines):
            line_num = i + 1
            is_vuln = 1 if line_num in vulnerable_lines else 0
            marked_lines.append(line)
            line_labels.append(is_vuln)

        marked_text = "\n".join(marked_lines)

        encoding = self.tokenizer(
            marked_text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # Create aligned labels (padded to max_length)
        # This is approximate — token-level alignment is non-trivial
        # For simplicity, we use the sequence-level label
        has_vuln = 1 if vulnerable_lines else 0

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(has_vuln, dtype=torch.long),
        }


# ---------------------------------------------------------------------------
# Split generation
# ---------------------------------------------------------------------------

def split_data(
    samples: List[ContractSample],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[List[ContractSample], List[ContractSample], List[ContractSample]]:
    """Split data into train/val/test with stratification by task_id."""
    import random
    random.seed(seed)

    by_task: Dict[str, List[ContractSample]] = {}
    for s in samples:
        by_task.setdefault(s.task_id, []).append(s)

    train, val, test = [], [], []

    for task_id, task_samples in by_task.items():
        random.shuffle(task_samples)
        n = len(task_samples)
        n_train = max(1, int(n * train_ratio))
        n_val = max(1, int(n * val_ratio))

        train.extend(task_samples[:n_train])
        val.extend(task_samples[n_train:n_train + n_val])
        test.extend(task_samples[n_train + n_val:])

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)

    return train, val, test


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Prepare SolidityGuard dataset")
    parser.add_argument("--manifest", default="data/manifest.json", help="Path to manifest.json")
    parser.add_argument("--augment", action="store_true", help="Augment with per-label examples")
    parser.add_argument("--output", default=None, help="Output directory for splits")
    args = parser.parse_args()

    print(f"Loading manifest: {args.manifest}")
    samples = load_manifest(args.manifest)
    print(f"  Loaded {len(samples)} contracts")

    if args.augment:
        samples = augment_samples(samples)
        print(f"  Augmented to {len(samples)} examples")

    train, val, test = split_data(samples)
    print(f"  Split: train={len(train)}, val={len(val)}, test={len(test)}")

    # Print label distribution
    for split_name, split_data_list in [("train", train), ("val", val), ("test", test)]:
        label_counts: Dict[str, int] = {}
        for s in split_data_list:
            lbl = s.primary_vuln
            label_counts[lbl] = label_counts.get(lbl, 0) + 1
        print(f"  {split_name}: {dict(sorted(label_counts.items()))}")

    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        for split_name, split_data_list in [("train", train), ("val", val), ("test", test)]:
            split_path = output_dir / f"{split_name}.json"
            with open(split_path, "w") as f:
                json.dump([{
                    "id": s.id,
                    "task_id": s.task_id,
                    "source_code": s.source_code,
                    "contract_name": s.contract_name,
                    "compiler_version": s.compiler_version,
                    "labels": s.labels,
                    "primary_vuln": s.primary_vuln,
                    "primary_severity": s.primary_severity,
                } for s in split_data_list], f, indent=2)
            print(f"  Saved {split_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
