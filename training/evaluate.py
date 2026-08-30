"""
Evaluate fine-tuned Graph CodeBERT on Solidity vulnerability detection.

Runs inference on test set, computes metrics, and generates a detailed report.

Usage:
    python training/evaluate.py --model training/checkpoints/best
    python training/evaluate.py --model training/checkpoints/best --manifest data/manifest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(Path(__file__).parent.parent))

from training.dataset import (
    VULN_LABELS,
    VULN_ID2LABEL,
    VulnerabilityClassificationDataset,
    load_manifest,
    split_data,
)
from torch.utils.data import DataLoader


def load_model(model_path: str) -> Tuple[Any, Any, Dict[str, int]]:
    """Load fine-tuned model and tokenizer."""
    logger_msg = f"Loading model from {model_path}"
    print(logger_msg)

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.eval()

    # Load label map
    label_map_path = Path(model_path) / "label_map.json"
    if label_map_path.exists():
        with open(label_map_path) as f:
            label_map = json.load(f)
        label2id = {v: i for i, v in enumerate(label_map["labels"])}
    else:
        label2id = {v: i for i, v in enumerate(VULN_LABELS)}

    return model, tokenizer, label2id


@torch.no_grad()
def predict(
    model: Any,
    tokenizer: Any,
    samples: List[Any],
    max_length: int = 512,
    batch_size: int = 8,
) -> List[Dict[str, Any]]:
    """Run inference on a list of ContractSample objects."""
    device = next(model.parameters()).device
    dataset = VulnerabilityClassificationDataset(samples, tokenizer, max_length)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    all_preds: List[int] = []
    all_probs: List[List[float]] = []
    all_labels: List[int] = []

    for batch in loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"]

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)
        preds = torch.argmax(logits, dim=-1)

        all_preds.extend(preds.cpu().tolist())
        all_probs.extend(probs.cpu().tolist())
        all_labels.extend(labels.tolist())

    results: List[Dict[str, Any]] = []
    for i, sample in enumerate(samples):
        pred_id = all_preds[i]
        true_id = all_labels[i]
        results.append({
            "id": sample.id,
            "contract_name": sample.contract_name,
            "true_label": VULN_ID2LABEL.get(true_id, f"class_{true_id}"),
            "predicted_label": VULN_ID2LABEL.get(pred_id, f"class_{pred_id}"),
            "confidence": max(all_probs[i]),
            "probabilities": {
                VULN_ID2LABEL.get(j, f"class_{j}"): round(p, 4)
                for j, p in enumerate(all_probs[i])
                if p > 0.01  # Only show significant probabilities
            },
            "correct": pred_id == true_id,
        })

    return results


def compute_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute classification metrics from prediction results."""
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    accuracy = correct / max(total, 1)

    # Per-class metrics
    class_metrics: Dict[str, Dict[str, float]] = {}
    for label in VULN_LABELS:
        tp = sum(1 for r in results if r["predicted_label"] == label and r["true_label"] == label)
        fp = sum(1 for r in results if r["predicted_label"] == label and r["true_label"] != label)
        fn = sum(1 for r in results if r["predicted_label"] != label and r["true_label"] == label)
        support = tp + fn

        if support > 0 or tp + fp > 0:
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 2 * precision * recall / max(precision + recall, 1e-8)
            class_metrics[label] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "support": support,
            }

    # Macro averages
    if class_metrics:
        macro_precision = sum(m["precision"] for m in class_metrics.values()) / len(class_metrics)
        macro_recall = sum(m["recall"] for m in class_metrics.values()) / len(class_metrics)
        macro_f1 = sum(m["f1"] for m in class_metrics.values()) / len(class_metrics)
    else:
        macro_precision = macro_recall = macro_f1 = 0.0

    # Confidence stats
    confidences = [r["confidence"] for r in results]
    avg_confidence = sum(confidences) / max(len(confidences), 1)

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "avg_confidence": round(avg_confidence, 4),
        "per_class": class_metrics,
    }


def print_report(metrics: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
    """Print a formatted evaluation report."""
    print("\n" + "=" * 70)
    print("SOLIDITYGUARD - GRAPH CODEBERT EVALUATION REPORT")
    print("=" * 70)

    print(f"\nTotal samples: {metrics['total']}")
    print(f"Correct predictions: {metrics['correct']}")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print(f"Macro Precision: {metrics['macro_precision']:.4f}")
    print(f"Macro Recall: {metrics['macro_recall']:.4f}")
    print(f"Avg Confidence: {metrics['avg_confidence']:.4f}")

    print("\nPer-Class Metrics:")
    print("-" * 70)
    print(f"{'Class':<20} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
    print("-" * 70)
    for label, m in sorted(metrics["per_class"].items()):
        print(f"{label:<20} {m['precision']:>10.4f} {m['recall']:>10.4f} {m['f1']:>10.4f} {m['support']:>10}")

    # Show misclassifications
    misclassified = [r for r in results if not r["correct"]]
    if misclassified:
        print(f"\nMisclassifications ({len(misclassified)}/{metrics['total']}):")
        print("-" * 70)
        for r in misclassified:
            print(f"  {r['contract_name']}: true={r['true_label']}, pred={r['predicted_label']} (conf={r['confidence']:.3f})")

    print("\n" + "=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned Graph CodeBERT")
    parser.add_argument("--model", required=True, help="Path to fine-tuned model directory")
    parser.add_argument("--manifest", default="data/manifest.json", help="Path to manifest.json")
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--output", default=None, help="Save results to JSON file")
    args = parser.parse_args()

    # Load model
    model, tokenizer, label2id = load_model(args.model)

    # Load data
    samples = load_manifest(args.manifest)
    train, val, test = split_data(samples)

    split_map = {"train": train, "val": val, "test": test}
    eval_samples = split_map[args.split]
    print(f"Evaluating on {args.split} split ({len(eval_samples)} samples)")

    # Predict
    results = predict(model, tokenizer, eval_samples, batch_size=args.batch_size)

    # Compute metrics
    metrics = compute_metrics(results)

    # Print report
    print_report(metrics, results)

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump({"metrics": metrics, "predictions": results}, f, indent=2)
        print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
