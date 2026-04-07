#!/usr/bin/env python3
"""
Comprehensive baseline test for SolidityGuard environment.
Tests all core functionality before adding new features.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from environment import SolidityGuardEnv


def test_environment_basic_flow():
    """Test basic reset -> step -> state flow for all tasks."""
    print("=" * 60)
    print("TESTING BASIC ENVIRONMENT FLOW")
    print("=" * 60)
    
    tasks = [
        "task_1_best_practices", 
        "task_2_gas_optimization", 
        "task_3_security"
    ]
    
    for task_id in tasks:
        print(f"\n[{task_id}]")
        env = SolidityGuardEnv()
        
        # Test reset
        obs = env.reset(task_id=task_id)
        assert "source_code" in obs
        assert "metadata" in obs
        assert "task_id" in obs
        assert obs["task_id"] == task_id
        print(f"  [OK] Reset OK - Contract: {obs['metadata']['contract_name']}")
        
        # Test state after reset
        state = env.state()
        assert state["step_count"] == 0
        assert state["done"] is False
        print(f"  [OK] Initial state OK")
        
        # Test step with empty action
        result = env.step([])
        assert "reward" in result
        assert "done" in result
        assert "details" in result
        print(f"  [OK] Empty step OK - Reward: {result['reward']}")
        
        # Test final state
        final_state = env.state()
        assert final_state["done"] is True
        assert final_state["step_count"] == 1
        print(f"  [OK] Final state OK")


def test_grading_system():
    """Test the grading system with various scenarios."""
    print("\n" + "=" * 60)
    print("TESTING GRADING SYSTEM")
    print("=" * 60)
    
    # Test Task 1 with perfect match
    env = SolidityGuardEnv()
    obs = env.reset(task_id="task_1_best_practices")
    print(f"Testing with contract: {obs['metadata']['contract_name']}")
    
    perfect_action = [
        {
            "issue_type": "missing_spdx",
            "line_number": 1,
            "description": "Missing SPDX license identifier",
            "severity": "Low"
        },
        {
            "issue_type": "old_compiler_version", 
            "line_number": 2,
            "description": "Compiler version below 0.8.x",
            "severity": "Low"
        }
    ]
    result = env.step(perfect_action)
    print(f"\nPerfect match score: {result['reward']:.4f}")
    print(f"Details: {result['details']}")
    assert result['reward'] >= 0.75  # Should be high (base * 0.6 + line_bonus)
    
    # Test with empty action (should get 0 score)
    env2 = SolidityGuardEnv()
    obs2 = env2.reset(task_id="task_3_security")
    empty_result = env2.step([])
    print(f"\nEmpty action score: {empty_result['reward']}")
    print(f"Details: {empty_result['details']}")
    assert empty_result['reward'] == 0.0
    assert empty_result['details']['matched'] == 0
    
    # Test partial match with correct structure
    env3 = SolidityGuardEnv()
    obs3 = env3.reset(task_id="task_1_best_practices")
    
    # Only include the first expected issue
    partial_action = [
        {
            "issue_type": "missing_spdx",
            "line_number": 1,
            "description": "Missing SPDX license identifier", 
            "severity": "Low"
        }
    ]
    partial_result = env3.step(partial_action)
    print(f"\nPartial match score: {partial_result['reward']}")
    print(f"Details: {partial_result['details']}")
    assert 0.0 < partial_result['reward'] < 1.0
    assert partial_result['details']['matched'] == 1
    
    print("[OK] Grading system working correctly")


def test_all_samples():
    """Test that all samples in the manifest load correctly."""
    print("\n" + "=" * 60)
    print("TESTING ALL DATASET SAMPLES")
    print("=" * 60)
    
    env = SolidityGuardEnv()
    
    # Load manifest to count samples
    with open("data/manifest.json", "r") as f:
        manifest = json.load(f)
    
    task_counts = {}
    for item in manifest:
        task = item["task_id"]
        task_counts[task] = task_counts.get(task, 0) + 1
    
    print(f"Found {len(manifest)} total samples:")
    for task, count in task_counts.items():
        print(f"  {task}: {count} samples")
    
    # Test cycling through samples for each task
    for task_id in ["task_1_best_practices", "task_2_gas_optimization", "task_3_security"]:
        sample_count = task_counts.get(task_id, 0)
        print(f"\nTesting {sample_count} samples for {task_id}:")
        
        for i in range(sample_count):
            obs = env.reset(task_id=task_id)
            contract_name = obs["metadata"]["contract_name"]
            print(f"  Sample {i+1}: {contract_name}")
            
    print("[OK] All samples load correctly")


def main():
    """Run all baseline tests."""
    try:
        test_environment_basic_flow()
        test_grading_system()
        test_all_samples()
        
        print("\n" + "=" * 60)
        print("SUCCESS: ALL BASELINE TESTS PASSED!")
        print("Environment is stable and ready for feature additions.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR: TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())