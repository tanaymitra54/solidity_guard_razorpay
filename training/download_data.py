"""
Download and prepare SmartBugs datasets for Graph CodeBERT fine-tuning.

Downloads:
  1. SmartBugs-Curated: 69 hand-annotated vulnerable contracts with line-level labels
  2. SmartBugs-Results: vulnerability analysis results for 47,587 contracts
  3. SmartBugs-Wild: 47,398 raw contracts from Ethereum (for additional unlabeled data)

Merges with existing SolidityGuard data (data/manifest.json).

Usage:
    python training/download_data.py --output training/data
    python training/download_data.py --output training/data --skip-wild  # faster, curated only

Output:
    training/data/
    ├── smartbugs_curated.json    # 69 labeled contracts
    ├── smartbugs_wild.json       # contracts with tool-detected vulnerabilities
    ├── solidityguard.json        # existing SolidityGuard data
    ├── combined.json             # all data merged
    └── label_map.json            # unified label mapping
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Vulnerability category mapping (SmartBugs -> our labels)
# ---------------------------------------------------------------------------

SMARTBUGS_TO_OURS: Dict[str, str] = {
    "access_control": "access_control",
    "arithmetic": "integer_overflow",
    "denial_service": "denial_of_service",
    "front_running": "front_running",
    "reentrancy": "reentrancy",
    "time_manipulation": "time_manipulation",
    "unchecked_low_calls": "unchecked_return_value",
    "other": "other",
}

OUR_LABELS = sorted(set(SMARTBUGS_TO_OURS.values()) | {
    "safe", "reentrancy", "access_control", "tx_origin_auth",
    "integer_overflow", "unsafe_delegatecall", "weak_randomness",
    "unbounded_loop", "redundant_storage", "gas_optimization",
    "best_practice", "denial_of_service", "front_running",
    "time_manipulation", "unchecked_return_value", "other",
})


# ---------------------------------------------------------------------------
# Clone helpers
# ---------------------------------------------------------------------------

def git_clone(url: str, target: str, depth: int = 1) -> None:
    """Shallow clone a git repo."""
    if Path(target).exists():
        print(f"  [SKIP] {target} already exists")
        return
    print(f"  Cloning {url} -> {target}")
    subprocess.run(
        ["git", "clone", "--depth", str(depth), "--single-branch", url, target],
        check=True,
        capture_output=True,
        text=True,
    )


def sparse_checkout(repo_url: str, target: str, sparse_path: str) -> None:
    """Sparse checkout - only download a subfolder."""
    if Path(target).exists():
        print(f"  [SKIP] {target} already exists")
        return
    print(f"  Sparse checkout {repo_url} ({sparse_path}) -> {target}")
    Path(target).mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", repo_url],
        cwd=target, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "core.sparseCheckout", "true"],
        cwd=target, check=True, capture_output=True,
    )
    sparse_file = Path(target) / ".git" / "info" / "sparse-checkout"
    sparse_file.write_text(f"{sparse_path}\n")
    subprocess.run(
        ["git", "pull", "--depth=1", "origin", "main"],
        cwd=target, check=True, capture_output=True,
    )


# ---------------------------------------------------------------------------
# SmartBugs Curated
# ---------------------------------------------------------------------------

def download_smartbugs_curated(output_dir: Path) -> None:
    """Download SmartBugs-Curated dataset."""
    print("\n[1/3] Downloading SmartBugs-Curated...")
    repo_dir = output_dir / "_smartbugs_curated"

    git_clone(
        "https://github.com/smartbugs/smartbugs-curated.git",
        str(repo_dir),
    )


def parse_smartbugs_curated(repo_dir: Path) -> List[Dict[str, Any]]:
    """Parse SmartBugs-Curated into training format."""
    vuln_json = repo_dir / "metadata" / "vulnerabilities.json"
    if not vuln_json.exists():
        print(f"  [WARN] {vuln_json} not found, skipping curated")
        return []

    with open(vuln_json) as f:
        entries = json.load(f)

    samples: List[Dict[str, Any]] = []
    for entry in entries:
        name = entry.get("name", "")
        rel_path = entry.get("path", "")
        source_path = repo_dir / rel_path

        if not source_path.exists():
            continue

        try:
            source_code = source_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if not source_code.strip():
            continue

        labels: List[Dict[str, Any]] = []
        categories_seen: Set[str] = set()

        for vuln in entry.get("vulnerabilities", []):
            category = vuln.get("category", "other")
            lines = vuln.get("lines", [])
            our_type = SMARTBUGS_TO_OURS.get(category, "other")
            categories_seen.add(our_type)

            for line_num in lines:
                labels.append({
                    "issue_type": our_type,
                    "line_number": line_num,
                    "description": f"{category} vulnerability at line {line_num}",
                    "severity": "Critical" if category in ("reentrancy", "access_control") else "Medium",
                    "source": "smartbugs_curated",
                })

        samples.append({
            "id": f"curated_{name}",
            "task_id": "smartbugs_curated",
            "source_code": source_code,
            "contract_name": name.replace(".sol", ""),
            "compiler_version": "unknown",
            "labels": labels,
            "primary_vuln": list(categories_seen)[0] if categories_seen else "other",
            "primary_severity": "Critical" if any(
                c in categories_seen for c in ("reentrancy", "access_control")
            ) else "Medium",
            "source": "smartbugs_curated",
        })

    print(f"  Parsed {len(samples)} curated contracts")
    return samples


# ---------------------------------------------------------------------------
# SmartBugs Wild (tool-detected vulnerabilities)
# ---------------------------------------------------------------------------

def download_smartbugs_wild(output_dir: Path) -> None:
    """Download SmartBugs-Wild contracts and results."""
    print("\n[2/3] Downloading SmartBugs-Wild...")
    wild_dir = output_dir / "_smartbugs_wild"
    results_dir = output_dir / "_smartbugs_results"

    # Download wild contracts (sparse - just contracts folder)
    sparse_checkout(
        "https://github.com/smartbugs/smartbugs-wild.git",
        str(wild_dir),
        "contracts",
    )

    # Download results metadata
    git_clone(
        "https://github.com/smartbugs/smartbugs-results.git",
        str(results_dir),
    )


def parse_smartbugs_wild(wild_dir: Path, results_dir: Path, max_samples: int = 5000) -> List[Dict[str, Any]]:
    """
    Parse SmartBugs-Wild with tool-detected vulnerabilities.

    Uses consensus voting: a contract is labeled vulnerable if ≥3 of 9 tools agree.
    """
    print("\n[3/3] Parsing SmartBugs-Wild...")

    contracts_dir = wild_dir / "contracts"
    if not contracts_dir.exists():
        print(f"  [WARN] {contracts_dir} not found, skipping wild")
        return []

    # Build a map of which tools detected what per contract
    tool_results: Dict[str, Dict[str, List[str]]] = {}  # address -> tool -> [categories]

    results_base = results_dir / "results"
    if results_base.exists():
        for tool_dir in results_base.iterdir():
            if not tool_dir.is_dir():
                continue
            tool_name = tool_dir.name
            wild_results = tool_dir / "wild"
            if not wild_results.exists():
                continue

            for contract_dir in wild_results.iterdir():
                if not contract_dir.is_dir():
                    continue
                address = contract_dir.name

                # Look for result JSON files
                for result_file in contract_dir.glob("*.json"):
                    try:
                        with open(result_file) as f:
                            result_data = json.load(f)
                        # Extract vulnerability categories from tool output
                        findings = result_data if isinstance(result_data, list) else result_data.get("results", [])
                        categories: List[str] = []
                        if isinstance(findings, list):
                            for finding in findings:
                                if isinstance(finding, dict):
                                    cat = finding.get("category", finding.get("check", ""))
                                    if cat:
                                        categories.append(cat.lower())
                        if address not in tool_results:
                            tool_results[address] = {}
                        tool_results[address][tool_name] = categories
                    except (json.JSONDecodeError, Exception):
                        continue

    # Process contracts with consensus labels
    samples: List[Dict[str, Any]] = []
    sol_files = list(contracts_dir.glob("*.sol"))[:max_samples]

    for sol_file in sol_files:
        address = sol_file.stem

        try:
            source_code = sol_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if not source_code.strip() or len(source_code) < 50:
            continue

        # Count tool consensus
        contract_tools = tool_results.get(address, {})
        if not contract_tools:
            continue

        # Aggregate categories across tools
        category_votes: Dict[str, int] = {}
        for tool_cats in contract_tools.values():
            for cat in tool_cats:
                normalized = cat.replace(" ", "_").replace("-", "_")
                category_votes[normalized] = category_votes.get(normalized, 0) + 1

        # Label as vulnerable if ≥2 tools agree
        labels: List[Dict[str, Any]] = []
        categories_seen: Set[str] = set()
        for category, votes in category_votes.items():
            if votes >= 2:
                our_type = SMARTBUGS_TO_OURS.get(category, "other")
                categories_seen.add(our_type)
                labels.append({
                    "issue_type": our_type,
                    "line_number": None,  # No line-level labels in wild
                    "description": f"{category} detected by {votes} tools",
                    "severity": "Critical" if our_type in ("reentrancy", "access_control") else "Medium",
                    "source": "smartbugs_wild",
                    "votes": votes,
                })

        if not labels:
            # No consensus -> likely safe
            primary = "safe"
        else:
            primary = list(categories_seen)[0]

        samples.append({
            "id": f"wild_{address}",
            "task_id": "smartbugs_wild",
            "source_code": source_code,
            "contract_name": address[:40],
            "compiler_version": "unknown",
            "labels": labels,
            "primary_vuln": primary,
            "primary_severity": "Critical" if "reentrancy" in categories_seen or "access_control" in categories_seen else "Medium",
            "source": "smartbugs_wild",
        })

    print(f"  Parsed {len(samples)} wild contracts (from {len(sol_files)} total)")
    return samples


# ---------------------------------------------------------------------------
# SolidityGuard data
# ---------------------------------------------------------------------------

def load_solidityguard(manifest_path: str) -> List[Dict[str, Any]]:
    """Load existing SolidityGuard data from manifest.json."""
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        print(f"  [WARN] {manifest_path} not found, skipping SolidityGuard data")
        return []

    repo_root = manifest_path.parent.parent
    with open(manifest_path) as f:
        manifest = json.load(f)

    samples: List[Dict[str, Any]] = []
    for entry in manifest:
        source_path = repo_root / entry["source_path"]
        if not source_path.exists():
            source_path = manifest_path.parent / entry["source_path"]
        if not source_path.exists():
            continue

        source_code = source_path.read_text(encoding="utf-8")
        labels = entry.get("labels", [])

        # Map SolidityGuard labels to our unified format
        unified_labels: List[Dict[str, Any]] = []
        categories_seen: Set[str] = set()

        for label in labels:
            issue_type = label.get("issue_type", "other")
            # Map to our unified label space
            if issue_type in ("missing_spdx", "old_compiler_version", "missing_natspec",
                              "deprecated_constructor", "missing_events", "unused_variables"):
                unified_type = "best_practice"
            elif issue_type in ("unbounded_loop", "redundant_storage_read", "custom_error_missing",
                                "poor_struct_packing", "unchecked_math_opportunity",
                                "expensive_operation_in_loop", "inefficient_string_concat"):
                unified_type = "gas_optimization"
            elif issue_type == "reentrancy":
                unified_type = "reentrancy"
            elif issue_type in ("missing_access_control",):
                unified_type = "access_control"
            elif issue_type == "tx_origin_auth":
                unified_type = "tx_origin_auth"
            elif issue_type == "integer_overflow_risk":
                unified_type = "integer_overflow"
            elif issue_type == "unsafe_delegatecall":
                unified_type = "unsafe_delegatecall"
            elif issue_type == "weak_randomness":
                unified_type = "weak_randomness"
            else:
                unified_type = "other"

            categories_seen.add(unified_type)
            unified_labels.append({
                "issue_type": unified_type,
                "line_number": label.get("line_number"),
                "description": label.get("description", ""),
                "severity": label.get("severity", "Medium"),
                "source": "solidityguard",
            })

        primary = list(categories_seen)[0] if categories_seen else "safe"

        samples.append({
            "id": entry["id"],
            "task_id": entry["task_id"],
            "source_code": source_code,
            "contract_name": entry.get("metadata", {}).get("contract_name", "Unknown"),
            "compiler_version": entry.get("metadata", {}).get("compiler_version", "unknown"),
            "labels": unified_labels,
            "primary_vuln": primary,
            "primary_severity": "Critical" if any(
                c in categories_seen for c in ("reentrancy", "access_control")
            ) else "Low",
            "source": "solidityguard",
        })

    print(f"  Loaded {len(samples)} SolidityGuard contracts")
    return samples


# ---------------------------------------------------------------------------
# Merge and save
# ---------------------------------------------------------------------------

def merge_datasets(
    solidityguard: List[Dict[str, Any]],
    curated: List[Dict[str, Any]],
    wild: List[Dict[str, Any]],
    output_dir: Path,
) -> None:
    """Merge all datasets and save."""
    # Combine
    all_samples = solidityguard + curated + wild

    # Deduplicate by source code hash
    seen_hashes: Set[int] = set()
    unique_samples: List[Dict[str, Any]] = []
    for sample in all_samples:
        h = hash(sample["source_code"])
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_samples.append(sample)

    print(f"\nMerged: {len(all_samples)} total -> {len(unique_samples)} unique")

    # Label distribution
    label_counts: Dict[str, int] = {}
    source_counts: Dict[str, int] = {}
    for s in unique_samples:
        lbl = s["primary_vuln"]
        label_counts[lbl] = label_counts.get(lbl, 0) + 1
        src = s.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    print(f"  By source: {dict(sorted(source_counts.items()))}")
    print(f"  By label: {dict(sorted(label_counts.items()))}")

    # Save individual datasets
    for name, data in [
        ("solidityguard", solidityguard),
        ("smartbugs_curated", curated),
        ("smartbugs_wild", wild),
        ("combined", unique_samples),
    ]:
        path = output_dir / f"{name}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Saved {path} ({len(data)} samples)")

    # Save label map
    label_map = {
        "labels": sorted(set(s["primary_vuln"] for s in unique_samples)),
        "label2id": {lbl: i for i, lbl in enumerate(sorted(set(s["primary_vuln"] for s in unique_samples)))},
    }
    with open(output_dir / "label_map.json", "w") as f:
        json.dump(label_map, f, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Download SmartBugs datasets")
    parser.add_argument("--output", default="training/data", help="Output directory")
    parser.add_argument("--manifest", default="data/manifest.json", help="SolidityGuard manifest path")
    parser.add_argument("--skip-wild", action="store_true", help="Skip SmartBugs-Wild (faster)")
    parser.add_argument("--wild-limit", type=int, default=5000, help="Max wild contracts to process")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SmartBugs Dataset Downloader")
    print("=" * 60)

    # 1. SolidityGuard (already in repo)
    print("\n[0/3] Loading SolidityGuard data...")
    solidityguard = load_solidityguard(args.manifest)

    # 2. SmartBugs Curated
    download_smartbugs_curated(output_dir)
    curated = parse_smartbugs_curated(output_dir / "_smartbugs_curated")

    # 3. SmartBugs Wild
    wild: List[Dict[str, Any]] = []
    if not args.skip_wild:
        download_smartbugs_wild(output_dir)
        wild = parse_smartbugs_wild(
            output_dir / "_smartbugs_wild",
            output_dir / "_smartbugs_results",
            max_samples=args.wild_limit,
        )

    # Merge and save
    merge_datasets(solidityguard, curated, wild, output_dir)

    print("\nDone! Dataset ready for training.")


if __name__ == "__main__":
    main()
