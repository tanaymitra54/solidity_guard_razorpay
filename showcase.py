#!/usr/bin/env python3
"""
SolidityGuard Feature Showcase
Demonstrates all v2.0 features: exploit proofs, auto-fix, multi-agent, reporting.
"""

from __future__ import annotations

import json
import os
from environment import SolidityGuardEnv
from multi_agent import MultiAgentSystem


def showcase_exploit_proofs():
    """Demo 1: Exploit Proof System"""
    print("\n" + "="*70)
    print("DEMO 1: EXPLOIT PROOF SYSTEM")
    print("="*70)
    
    env = SolidityGuardEnv()
    
    # Get a security vulnerability contract
    for _ in range(10):
        obs = env.reset(task_id="task_3_security")
        if obs['metadata']['contract_name'] == 'Reentry':
            break
    
    print(f"\nContract: {obs['metadata']['contract_name']}")
    print("Finding: Reentrancy Vulnerability\n")
    
    # Submit with exploit explanation
    action = [
        {
            "issue_type": "reentrancy",
            "line_number": 14,
            "description": "State update after external call allows reentrancy",
            "severity": "Critical",
            "exploit_path": "1) Attacker deploys malicious contract with fallback function "
                           "2) Calls withdraw() which transfers funds via call{} "
                           "3) Fallback function is triggered and calls withdraw() again "
                           "4) Process repeats until contract is drained",
            "recommended_fix": "Move balance update before external call (checks-effects-interactions pattern)",
            "confidence": 0.95
        }
    ]
    
    result = env.step(action)
    print(f"Score: {result['reward']:.4f}")
    print(f"Exploit bonus: +{result['details'].get('exploit_bonus', 0):.3f}")
    print(f"Details: {json.dumps(result['details'], indent=2)}")


def showcase_auto_fix():
    """Demo 2: Auto-Fix Suggestions"""
    print("\n" + "="*70)
    print("DEMO 2: AUTO-FIX SUGGESTIONS")
    print("="*70)
    
    env = SolidityGuardEnv()
    
    # Get a best practices contract
    for _ in range(10):
        obs = env.reset(task_id="task_1_best_practices")
        if obs['metadata']['contract_name'] == 'NoSpdx':
            break
    
    print(f"\nContract: {obs['metadata']['contract_name']}")
    print("Finding: Missing SPDX License Identifier\n")
    
    # Submit with fix suggestion
    action = [
        {
            "issue_type": "missing_spdx",
            "line_number": 1,
            "description": "Missing SPDX license identifier",
            "severity": "Low",
            "recommended_fix": 'Add "// SPDX-License-Identifier: MIT" as the first line of the file',
            "confidence": 0.99
        },
        {
            "issue_type": "old_compiler_version",
            "line_number": 2,
            "description": "Compiler version below 0.8.x",
            "severity": "Low",
            "recommended_fix": 'Update "pragma solidity ^0.7.6;" to "pragma solidity ^0.8.0;"',
            "confidence": 0.90
        }
    ]
    
    result = env.step(action)
    print(f"Score: {result['reward']:.4f}")
    print(f"Fix bonus: +{result['details'].get('fix_bonus', 0):.3f}")
    print(f"Details: {json.dumps(result['details'], indent=2)}")


def showcase_multi_agent():
    """Demo 3: Multi-Agent Verification"""
    print("\n" + "="*70)
    print("DEMO 3: MULTI-AGENT VERIFICATION SYSTEM")
    print("="*70)
    
    multi_agent = MultiAgentSystem()
    env = SolidityGuardEnv()
    
    # Get a security vulnerability contract
    for _ in range(10):
        obs = env.reset(task_id="task_3_security")
        if obs['metadata']['contract_name'] == 'OriginAuth':
            break
    
    print(f"\nContract: {obs['metadata']['contract_name']}")
    print("Running multi-agent pipeline...\n")
    
    # Run multi-agent analysis
    findings = multi_agent.process(obs['source_code'], "task_3_security")
    
    print("Multi-Agent Findings:")
    for i, finding in enumerate(findings, 1):
        print(f"\n{i}. {finding['issue_type'].upper()}")
        print(f"   Severity: {finding['severity']}")
        print(f"   Line: {finding.get('line_number', 'N/A')}")
        print(f"   Analyzer Confidence: {finding.get('analyzer_confidence', 0):.2f}")
        print(f"   Verifier Confidence: {finding.get('verifier_confidence', 0):.2f}")
        print(f"   Agent Consensus: {finding.get('agent_consensus', 0):.2f}")
        print(f"   Risk Score: {finding.get('risk_score', 0):.3f}")
        if finding.get('recommended_fix'):
            print(f"   Fix: {finding['recommended_fix']}")
    
    # Score with environment
    if findings:
        result = env.step(findings)
        print(f"\nEnvironment Score: {result['reward']:.4f}")


def showcase_enhanced_scoring():
    """Demo 4: Enhanced Scoring with All Bonuses"""
    print("\n" + "="*70)
    print("DEMO 4: ENHANCED SCORING SYSTEM")
    print("="*70)
    
    env = SolidityGuardEnv()
    
    # Get security contract
    for _ in range(10):
        obs = env.reset(task_id="task_3_security")
        if obs['metadata']['contract_name'] == 'Reentry':
            break
    
    print(f"\nContract: {obs['metadata']['contract_name']}")
    print("Testing scoring with all bonus types...\n")
    
    # Perfect finding with all bells and whistles
    perfect_action = [
        {
            "issue_type": "reentrancy",
            "line_number": 14,  # Exact line number for bonus
            "description": "State update after external call allows reentrancy",
            "severity": "Critical",
            "exploit_path": "Attacker creates contract with fallback that re-enters withdraw, draining funds via recursive calls",
            "recommended_fix": "Move balances[msg.sender] = 0 before the external call to follow checks-effects-interactions pattern",
            "confidence": 0.85
        }
    ]
    
    result = env.step(perfect_action)
    
    print("Score Breakdown:")
    details = result['details']
    print(f"  Base Score (matched/expected): {details['matched']}/{details['expected']} = {details['matched']/details['expected']:.2f}")
    print(f"  Line Accuracy Bonus: +{details.get('line_bonus', 0):.3f}")
    print(f"  Exploit Explanation Bonus: +{details.get('exploit_bonus', 0):.3f}")
    print(f"  Fix Suggestion Bonus: +{details.get('fix_bonus', 0):.3f}")
    print(f"  Confidence Level Bonus: +{details.get('confidence_bonus', 0):.3f}")
    print(f"  False Positive Penalty: -{details['false_positives'] * 0.05:.3f}")
    print(f"\nFinal Score: {result['reward']:.4f}")


def showcase_dataset():
    """Demo 5: Dataset Overview"""
    print("\n" + "="*70)
    print("DEMO 5: EXPANDED DATASET (18 SAMPLES)")
    print("="*70)
    
    with open("data/manifest.json", "r") as f:
        manifest = json.load(f)
    
    task_groups = {}
    for item in manifest:
        task = item['task_id']
        if task not in task_groups:
            task_groups[task] = []
        task_groups[task].append(item)
    
    for task_id in ["task_1_best_practices", "task_2_gas_optimization", "task_3_security"]:
        samples = task_groups.get(task_id, [])
        print(f"\n{task_id} ({len(samples)} samples):")
        
        for item in samples:
            contract = item['metadata']['contract_name']
            issue_count = len(item['labels'])
            issue_types = ", ".join(set(l['issue_type'] for l in item['labels']))
            print(f"  • {contract}: {issue_count} issues ({issue_types})")


def main():
    """Run all feature demonstrations."""
    print("\n" + "="*70)
    print("SOLIDITYGUARD v2.0 - FEATURE SHOWCASE")
    print("Advanced Smart Contract Auditor with Multi-Agent Verification")
    print("="*70)
    
    try:
        showcase_exploit_proofs()
        showcase_auto_fix()
        showcase_multi_agent()
        showcase_enhanced_scoring()
        showcase_dataset()
        
        print("\n" + "="*70)
        print("SHOWCASE COMPLETE")
        print("="*70)
        print("\nSummary:")
        print("[OK] Exploit Proofs: Agents explain HOW vulnerabilities can be exploited")
        print("[OK] Auto-Fix: Recommended code changes for each finding")
        print("[OK] Multi-Agent: Analyzer -> Verifier -> Risk Scorer pipeline")
        print("[OK] Enhanced Scoring: Base + Line + Exploit + Fix + Confidence bonuses")
        print("[OK] Expanded Dataset: 18 realistic Solidity samples (6 per task)")
        print("[OK] Advanced APIs: /report and /dashboard endpoints")
        print("\nReady for hackathon submission!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\nError during showcase: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())