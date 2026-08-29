"""
Mock inference test to demonstrate the logging format without requiring LLM credentials.
This simulates what happens during a real inference run.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from environment import SolidityGuardEnv


def _log(tag: str, payload: Dict[str, Any]) -> None:
    print(f"[{tag}] {json.dumps(payload, ensure_ascii=False)}")


def _mock_model_response(task_id: str) -> List[Dict[str, Any]]:
    """Mock LLM responses for each task."""
    
    mock_responses = {
        "task_1_best_practices": [
            {
                "issue_type": "missing_spdx",
                "line_number": 1,
                "description": "Missing SPDX license identifier",
                "severity": "Low",
                "recommended_fix": "Add // SPDX-License-Identifier: MIT at the top of the file",
                "confidence": 0.95
            },
            {
                "issue_type": "old_compiler_version",
                "line_number": 2,
                "description": "Compiler version below 0.8.x",
                "severity": "Low",
                "recommended_fix": "Update pragma to ^0.8.0 or higher",
                "confidence": 0.90
            }
        ],
        "task_2_gas_optimization": [
            {
                "issue_type": "unbounded_loop",
                "line_number": 8,
                "description": "Loop iterating over dynamic array without bounds",
                "severity": "Medium",
                "recommended_fix": "Add maximum iteration limit or use pagination",
                "confidence": 0.85
            }
        ],
        "task_3_security": [
            {
                "issue_type": "reentrancy",
                "line_number": 13,
                "description": "State updated after external call, vulnerable to reentrancy",
                "severity": "Critical",
                "exploit_path": "1. Attacker calls withdraw() with malicious contract\n2. During transfer, malicious contract calls withdraw() again\n3. Balance not yet updated, can drain contract\n4. Multiple withdrawals before balance update completes",
                "recommended_fix": "Move balance update before external call (checks-effects-interactions pattern) or use ReentrancyGuard",
                "confidence": 0.95
            }
        ]
    }
    
    return mock_responses.get(task_id, [])


def run() -> int:
    env = SolidityGuardEnv()
    tasks = [
        "task_1_best_practices",
        "task_2_gas_optimization",
        "task_3_security",
    ]

    _log("START", {"task_count": len(tasks)})
    total_score = 0.0

    for task_id in tasks:
        observation = env.reset(task_id=task_id)
        
        # Mock LLM response instead of calling actual API
        actions = _mock_model_response(task_id)

        step_result = env.step(actions)
        state = env.state()

        total_score += step_result["reward"]

        _log(
            "STEP",
            {
                "task_id": task_id,
                "reward": step_result["reward"],
                "details": step_result.get("details", {}),
                "state": state,
            },
        )

    final_score = round(total_score / len(tasks), 4)
    _log("END", {"final_score": final_score})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception as exc:
        _log("END", {"final_score": 0.0, "error": str(exc)})
        sys.exit(1)
