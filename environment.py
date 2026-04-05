from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from graders import grade_action


@dataclass
class EnvironmentState:
    task_id: str
    step_count: int
    max_steps: int
    score_so_far: float
    done: bool


class SolidityGuardEnv:
    def __init__(self, data_path: str = "data/manifest.json") -> None:
        self.data_path = data_path
        self._load_manifest()
        self._index = 0
        self._current_sample: Optional[Dict[str, Any]] = None
        self._state: Optional[EnvironmentState] = None

    def _load_manifest(self) -> None:
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Manifest not found: {self.data_path}")
        with open(self.data_path, "r", encoding="utf-8") as handle:
            self._manifest = json.load(handle)
        if not isinstance(self._manifest, list) or not self._manifest:
            raise ValueError("Manifest must be a non-empty list")

    def reset(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        if task_id:
            candidates = [item for item in self._manifest if item["task_id"] == task_id]
        else:
            candidates = self._manifest

        if not candidates:
            raise ValueError("No samples available for the requested task")

        self._current_sample = candidates[self._index % len(candidates)]
        self._index += 1

        source_path = self._current_sample["source_path"]
        with open(source_path, "r", encoding="utf-8") as handle:
            source_code = handle.read()

        observation = {
            "source_code": source_code,
            "metadata": self._current_sample.get("metadata", {}),
            "task_id": self._current_sample["task_id"],
        }

        self._state = EnvironmentState(
            task_id=self._current_sample["task_id"],
            step_count=0,
            max_steps=1,
            score_so_far=0.0,
            done=False,
        )

        return observation

    def step(self, action: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self._current_sample is None or self._state is None:
            raise RuntimeError("Call reset() before step().")

        if self._state.done:
            return {
                "reward": self._state.score_so_far,
                "done": True,
                "details": {"message": "Episode already completed"},
            }

        expected = self._current_sample.get("labels", [])
        reward, details = grade_action(action, expected)

        self._state.step_count += 1
        self._state.score_so_far = reward
        self._state.done = True

        return {
            "reward": reward,
            "done": True,
            "details": details,
        }

    def state(self) -> Dict[str, Any]:
        if self._state is None:
            raise RuntimeError("Call reset() before state().")
        return {
            "task_id": self._state.task_id,
            "step_count": self._state.step_count,
            "max_steps": self._state.max_steps,
            "score_so_far": self._state.score_so_far,
            "done": self._state.done,
        }
