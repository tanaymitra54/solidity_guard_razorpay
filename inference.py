from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

from environment import SolidityGuardEnv


def _log(tag: str, payload: Dict[str, Any]) -> None:
    print(f"[{tag}] {json.dumps(payload, ensure_ascii=False)}")


def _load_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _call_model(prompt: str) -> List[Dict[str, Any]]:
    from openai import OpenAI

    api_base_url = _load_env_var("API_BASE_URL")
    model_name = _load_env_var("MODEL_NAME")
    hf_token = _load_env_var("HF_TOKEN")

    try:
        client = OpenAI(base_url=api_base_url, api_key=hf_token)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a Solidity security reviewer. Always respond with valid JSON array only, no explanations."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
        )

        content = response.choices[0].message.content or "[]"
    except Exception:
        content = "[]"
    
    if content.startswith("```"):
        parts = content.split("```")
        if len(parts) >= 3:
            content = parts[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
    
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = []
    if isinstance(parsed, list):
        return parsed
    return []


def _build_prompt(source_code: str, task_id: str) -> str:
    task_info = {
        "task_1_best_practices": "Find syntax and best-practice issues: missing SPDX license, old compiler version (<0.8.x), missing NatSpec comments, deprecated constructor syntax.",
        "task_2_gas_optimization": "Find gas optimization opportunities: unbounded loops, redundant storage reads, missing custom errors (use custom errors instead of require strings).",
        "task_3_security": "Find security vulnerabilities: reentrancy bugs, missing access control, tx.origin usage for authorization, integer overflow/underflow.",
    }
    return (
        "Review the Solidity contract and return a JSON array of findings. "
        "Each finding must include: issue_type, line_number, description, severity (Critical/Medium/Low/Info). "
        f"Focus on: {task_info.get(task_id, task_id)}\n\n"
        f"Contract:\n{source_code}"
    )


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
        prompt = _build_prompt(observation["source_code"], task_id)
        actions = _call_model(prompt)

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