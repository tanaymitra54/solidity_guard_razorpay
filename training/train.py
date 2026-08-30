"""
Fine-tune Microsoft Graph CodeBERT for Solidity vulnerability detection.

This script:
1. Loads Graph CodeBERT from HuggingFace (pulls on first run)
2. Prepares the SolidityGuard dataset
3. Fine-tunes for vulnerability type classification
4. Saves the model + tokenizer for inference

Usage on H100 server:
    cd ContractSLM
    python training/train.py --config training/config.yaml
    python training/train.py  # uses defaults

Environment:
    - GPU: CUDA-capable (H100 recommended)
    - RAM: 16GB+ recommended
    - Disk: 5GB for model + checkpoints
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from training.dataset import (
    VULN_LABELS,
    VULN_ID2LABEL,
    VulnerabilityClassificationDataset,
    load_manifest,
    load_combined_data,
    augment_samples,
    split_data,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("training")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class TrainConfig:
    """Training configuration."""
    # Model
    model_name: str = "microsoft/graphcodebert-base"
    num_labels: int = len(VULN_LABELS)
    max_length: int = 512

    # Data
    manifest_path: str = "data/manifest.json"
    augment: bool = True
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    seed: int = 42

    # Training
    epochs: int = 20
    batch_size: int = 8
    gradient_accumulation_steps: int = 2
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    max_grad_norm: float = 1.0

    # Output
    output_dir: str = "training/checkpoints"
    logging_steps: int = 5
    eval_steps: int = 10
    save_best: bool = True
    early_stopping_patience: int = 5

    # Device
    device: str = "auto"

    @classmethod
    def from_yaml(cls, path: str) -> "TrainConfig":
        """Load config from YAML file."""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def resolve_device(self) -> torch.device:
        if self.device == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            return torch.device("cpu")
        return torch.device(self.device)


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

class Trainer:
    """Handles the fine-tuning loop with evaluation and checkpointing."""

    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        config: TrainConfig,
        device: torch.device,
    ) -> None:
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.config = config
        self.device = device

        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )

        total_steps = len(train_loader) * config.epochs // config.gradient_accumulation_steps
        warmup_steps = int(total_steps * config.warmup_ratio)
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=warmup_steps,
            num_training_steps=total_steps,
        )

        self.best_val_f1 = 0.0
        self.steps_no_improve = 0
        self.global_step = 0

    def train(self) -> Dict[str, Any]:
        """Run the full training loop."""
        logger.info(f"Starting training for {self.config.epochs} epochs")
        logger.info(f"  Device: {self.device}")
        logger.info(f"  Train samples: {len(self.train_loader.dataset)}")
        logger.info(f"  Val samples: {len(self.val_loader.dataset)}")
        logger.info(f"  Batch size: {self.config.batch_size}")
        logger.info(f"  Gradient accum steps: {self.config.gradient_accumulation_steps}")
        logger.info(f"  Effective batch size: {self.config.batch_size * self.config.gradient_accumulation_steps}")

        history: List[Dict[str, Any]] = []
        start_time = time.time()

        for epoch in range(self.config.epochs):
            # --- Train ---
            self.model.train()
            total_loss = 0.0
            correct = 0
            total = 0
            epoch_start = time.time()

            for step, batch in enumerate(self.train_loader):
                batch = {k: v.to(self.device) for k, v in batch.items()}
                outputs = self.model(**batch)
                loss = outputs.loss / self.config.gradient_accumulation_steps
                loss.backward()
                total_loss += loss.item() * self.config.gradient_accumulation_steps

                preds = torch.argmax(outputs.logits, dim=-1)
                correct += (preds == batch["labels"]).sum().item()
                total += batch["labels"].size(0)

                if (step + 1) % self.config.gradient_accumulation_steps == 0:
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(), self.config.max_grad_norm
                    )
                    self.optimizer.step()
                    self.scheduler.step()
                    self.optimizer.zero_grad()
                    self.global_step += 1

                    if self.global_step % self.config.logging_steps == 0:
                        avg_loss = total_loss / (step + 1)
                        acc = correct / total
                        lr = self.scheduler.get_last_lr()[0]
                        logger.info(
                            f"  Epoch {epoch+1} Step {self.global_step}: "
                            f"loss={avg_loss:.4f} acc={acc:.4f} lr={lr:.2e}"
                        )

            train_loss = total_loss / max(len(self.train_loader), 1)
            train_acc = correct / max(total, 1)
            epoch_time = time.time() - epoch_start

            # --- Evaluate ---
            val_metrics = self.evaluate()
            val_loss = val_metrics["loss"]
            val_acc = val_metrics["accuracy"]
            val_f1 = val_metrics["f1_macro"]

            logger.info(
                f"Epoch {epoch+1}/{self.config.epochs} "
                f"[{epoch_time:.1f}s] "
                f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
                f"val_loss={val_loss:.4f} val_acc={val_acc:.4f} val_f1={val_f1:.4f}"
            )

            history.append({
                "epoch": epoch + 1,
                "train_loss": train_loss,
                "train_acc": train_acc,
                "val_loss": val_loss,
                "val_acc": val_acc,
                "val_f1": val_f1,
                "time": epoch_time,
            })

            # --- Checkpoint ---
            if val_f1 > self.best_val_f1:
                self.best_val_f1 = val_f1
                self.steps_no_improve = 0
                if self.config.save_best:
                    self.save_checkpoint("best")
                    logger.info(f"  New best model (F1={val_f1:.4f}) saved")
            else:
                self.steps_no_improve += 1
                if self.steps_no_improve >= self.config.early_stopping_patience:
                    logger.info(f"  Early stopping at epoch {epoch+1} (no improvement for {self.config.early_stopping_patience} epochs)")
                    break

        total_time = time.time() - start_time
        logger.info(f"Training complete in {total_time:.1f}s")
        logger.info(f"Best validation F1: {self.best_val_f1:.4f}")

        # Save final model
        self.save_checkpoint("final")

        # Save training history
        output_dir = Path(self.config.output_dir)
        history_path = output_dir / "training_history.json"
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        logger.info(f"Training history saved to {history_path}")

        return {
            "best_val_f1": self.best_val_f1,
            "total_time": total_time,
            "epochs_trained": len(history),
            "history": history,
        }

    @torch.no_grad()
    def evaluate(self) -> Dict[str, float]:
        """Evaluate on validation set."""
        self.model.eval()
        total_loss = 0.0
        all_preds: List[int] = []
        all_labels: List[int] = []

        for batch in self.val_loader:
            batch = {k: v.to(self.device) for k, v in batch.items()}
            outputs = self.model(**batch)
            total_loss += outputs.loss.item()

            preds = torch.argmax(outputs.logits, dim=-1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(batch["labels"].cpu().tolist())

        avg_loss = total_loss / max(len(self.val_loader), 1)

        # Compute metrics
        correct = sum(p == l for p, l in zip(all_preds, all_labels))
        accuracy = correct / max(len(all_labels), 1)

        # Per-class F1
        f1_per_class: Dict[str, float] = {}
        for label_id in range(self.config.num_labels):
            tp = sum(1 for p, l in zip(all_preds, all_labels) if p == label_id and l == label_id)
            fp = sum(1 for p, l in zip(all_preds, all_labels) if p == label_id and l != label_id)
            fn = sum(1 for p, l in zip(all_preds, all_labels) if p != label_id and l == label_id)

            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 2 * precision * recall / max(precision + recall, 1e-8)

            label_name = VULN_ID2LABEL.get(label_id, f"class_{label_id}")
            if tp + fp + fn > 0:  # Only report classes that appear
                f1_per_class[label_name] = round(f1, 4)

        # Macro F1
        f1_macro = sum(f1_per_class.values()) / max(len(f1_per_class), 1)

        return {
            "loss": avg_loss,
            "accuracy": accuracy,
            "f1_macro": f1_macro,
            "f1_per_class": f1_per_class,
        }

    def save_checkpoint(self, name: str) -> None:
        """Save model checkpoint."""
        output_dir = Path(self.config.output_dir) / name
        output_dir.mkdir(parents=True, exist_ok=True)

        self.model.save_pretrained(str(output_dir))
        self.model.config.id2label = VULN_ID2LABEL
        self.model.config.label2id = {v: k for k, v in VULN_ID2LABEL.items()}
        self.model.config.save_pretrained(str(output_dir))

        # Save label map
        label_map_path = output_dir / "label_map.json"
        with open(label_map_path, "w") as f:
            json.dump({
                "labels": VULN_LABELS,
                "id2label": {str(k): v for k, v in VULN_ID2LABEL.items()},
                "label2id": VULN_LABELS,
            }, f, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune Graph CodeBERT for Solidity auditing")
    parser.add_argument("--config", default=None, help="Path to config YAML")
    parser.add_argument("--model-name", default=None, help="Override model name")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--manifest", default=None, help="Override manifest path")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    # Load config
    if args.config and Path(args.config).exists():
        config = TrainConfig.from_yaml(args.config)
    else:
        config = TrainConfig()

    # CLI overrides
    if args.model_name:
        config.model_name = args.model_name
    if args.epochs:
        config.epochs = args.epochs
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.lr:
        config.learning_rate = args.lr
    if args.manifest:
        config.manifest_path = args.manifest
    if args.output_dir:
        config.output_dir = args.output_dir

    device = config.resolve_device()
    logger.info(f"Device: {device}")
    if device.type == "cuda":
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")

    # --- Load tokenizer & model ---
    logger.info(f"Loading model: {config.model_name}")
    logger.info("  (Model will be downloaded from HuggingFace on first run)")

    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.model_name,
        num_labels=config.num_labels,
        id2label=VULN_ID2LABEL,
        label2id={v: k for k, v in VULN_ID2LABEL.items()},
        ignore_mismatched_sizes=True,
    )
    model.to(device)

    param_count = sum(p.numel() for p in model.parameters())
    trainable_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"  Parameters: {param_count:,} total, {trainable_count:,} trainable")

    # --- Load data ---
    # Try combined data first, fall back to manifest
    combined_path = Path(config.manifest_path).parent.parent / "training" / "data" / "combined.json"
    if combined_path.exists():
        logger.info(f"Loading combined dataset from {combined_path}")
        samples = load_combined_data(str(combined_path))
    else:
        logger.info(f"Loading dataset from {config.manifest_path}")
        samples = load_manifest(config.manifest_path)
    logger.info(f"  Loaded {len(samples)} contracts")

    if config.augment:
        samples = augment_samples(samples)
        logger.info(f"  Augmented to {len(samples)} training examples")

    train_samples, val_samples, test_samples = split_data(
        samples, config.train_ratio, config.val_ratio, config.seed
    )
    logger.info(f"  Split: train={len(train_samples)}, val={len(val_samples)}, test={len(test_samples)}")

    # --- Create datasets ---
    train_dataset = VulnerabilityClassificationDataset(
        train_samples, tokenizer, config.max_length
    )
    val_dataset = VulnerabilityClassificationDataset(
        val_samples, tokenizer, config.max_length
    )
    test_dataset = VulnerabilityClassificationDataset(
        test_samples, tokenizer, config.max_length
    )

    train_loader = DataLoader(
        train_dataset, batch_size=config.batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        val_dataset, batch_size=config.batch_size, shuffle=False, num_workers=0
    )

    # --- Train ---
    trainer = Trainer(model, train_loader, val_loader, config, device)
    results = trainer.train()

    # --- Final evaluation on test set ---
    logger.info("\nFinal evaluation on test set:")
    test_loader = DataLoader(test_dataset, batch_size=config.batch_size, shuffle=False)
    trainer.val_loader = test_loader
    test_metrics = trainer.evaluate()
    logger.info(f"  Test Accuracy: {test_metrics['accuracy']:.4f}")
    logger.info(f"  Test F1 (macro): {test_metrics['f1_macro']:.4f}")
    logger.info(f"  Per-class F1: {json.dumps(test_metrics['f1_per_class'], indent=2)}")

    # Save test results
    output_dir = Path(config.output_dir)
    test_results_path = output_dir / "test_results.json"
    with open(test_results_path, "w") as f:
        json.dump(test_metrics, f, indent=2)
    logger.info(f"  Test results saved to {test_results_path}")

    # Save config
    config_path = output_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump({
            "model_name": config.model_name,
            "num_labels": config.num_labels,
            "max_length": config.max_length,
            "labels": VULN_LABELS,
            "epochs": config.epochs,
            "batch_size": config.batch_size,
            "learning_rate": config.learning_rate,
            "best_val_f1": results["best_val_f1"],
            "test_f1": test_metrics["f1_macro"],
        }, f, indent=2)

    logger.info("\n=== Training Complete ===")
    logger.info(f"  Best val F1: {results['best_val_f1']:.4f}")
    logger.info(f"  Test F1: {test_metrics['f1_macro']:.4f}")
    logger.info(f"  Model saved to: {config.output_dir}/best/")


if __name__ == "__main__":
    main()
