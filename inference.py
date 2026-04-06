from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

from environment import SolidityGuardEnv
from multi_agent import MultiAgentSystem


def _log(tag: str, payload: Dict[str, Any]) -> None:
    print(f"[{tag}] {json.dumps(payload, ensure_ascii=True)}")


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

    client = OpenAI(base_url=api_base_url, api_key=hf_token)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a Solidity security reviewer."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=800,
    )

    content = response.choices[0].message.content or "[]"
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = []
    if isinstance(parsed, list):
        return parsed
    return []


def _build_prompt(source_code: str, task_id: str) -> str:
    return (
        "Review the Solidity contract and return a JSON array of findings. "
        "Each finding must include: issue_type, line_number, description, severity. "
        "OPTIONALLY include: exploit_path (step-by-step attack explanation), "
        "recommended_fix (suggested code changes), confidence (0.0-1.0). "
        f"Task: {task_id}.\n\n"
        f"Contract:\n{source_code}"
    )


def run() -> int:
    env = SolidityGuardEnv()
    multi_agent = MultiAgentSystem()
    tasks = [
        "task_1_best_practices",
        "task_2_gas_optimization",
        "task_3_security",
    ]

    _log("START", {"task_count": len(tasks), "multi_agent_enabled": True})
    total_score = 0.0

    for task_id in tasks:
        observation = env.reset(task_id=task_id)
        
        # Check if multi-agent mode is enabled via env var
        use_multi_agent = os.getenv("MULTI_AGENT_MODE", "false").lower() == "true"
        
        if use_multi_agent:
            # Use multi-agent system
            actions = multi_agent.process(observation["source_code"], task_id)
            _log("STEP", {"task_id": task_id, "agent_mode": "multi_agent", "findings": len(actions)})
        else:
            # Use standard LLM inference
            prompt = _build_prompt(observation["source_code"], task_id)
            actions = _call_model(prompt)
            _log("STEP", {"task_id": task_id, "agent_mode": "single_llm", "findings": len(actions)})

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
                "agent_mode": "multi_agent" if use_multi_agent else "single_llm",
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
