"""
Base classes and LLM client for the multi-agent system.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from openai import AsyncOpenAI
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------

class StructuredLogger:
    """Lightweight structured logger for the multi-agent pipeline."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def _emit(self, level: str, event: str, **extra: Any) -> None:
        payload = {"event": event, **extra}
        text = json.dumps(payload, default=str)
        getattr(self._logger, level)(text)

    def info(self, event: str, **extra: Any) -> None:
        self._emit("info", event, **extra)

    def warning(self, event: str, **extra: Any) -> None:
        self._emit("warning", event, **extra)

    def error(self, event: str, **extra: Any) -> None:
        self._emit("error", event, **extra)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger for a module."""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
        )
    return StructuredLogger(name)


# ---------------------------------------------------------------------------
# Request context
# ---------------------------------------------------------------------------

@dataclass
class RequestContext:
    """Traces a single audit request through the pipeline."""
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    start_time: float = field(default_factory=time.time)
    agent_calls: int = 0
    llm_calls: int = 0

    def elapsed(self) -> float:
        return round(time.time() - self.start_time, 3)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    """A security finding from an agent."""
    issue_type: str
    line_number: Optional[int] = None
    severity: str = "Medium"  # Critical, Medium, Low, Info
    description: str = ""
    exploit_scenario: Optional[str] = None
    exploit_poc: Optional[str] = None  # Foundry test code
    suggested_fix: Optional[str] = None
    confidence: float = 0.5
    source: str = "unknown"  # Which agent found this
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuditResult(BaseModel):
    """Complete audit result from the multi-agent pipeline."""
    findings: List[Finding]
    contract_info: Dict[str, Any] = field(default_factory=dict)
    agent_metrics: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_time_seconds: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "Critical")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "Medium")

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "Low")


# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------

class LLMClient:
    """
    LLM client wrapper supporting both OpenAI API and local vLLM endpoints.

    For H100 deployment, set LLM_BASE_URL to your vLLM server.
    For development, it can use OpenAI API directly.
    """

    _log = get_logger("agents.llm")

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "Qwen/Qwen2.5-72B-Instruct",
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ) -> None:
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://router.huggingface.co/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("HF_TOKEN", "")
        self.model = model or os.getenv("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "dummy-key",
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = True,
        retries: int = 3,
    ) -> str:
        """Generate a response from the LLM with retry logic."""
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error: Optional[Exception] = None
        for attempt in range(retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"} if json_mode else None,
                )
                result = response.choices[0].message.content or ""
                self._log.info(
                    "llm_call_success",
                    model=self.model,
                    attempt=attempt + 1,
                    tokens=len(result),
                )
                return result
            except Exception as e:
                last_error = e
                self._log.warning(
                    "llm_call_retry",
                    model=self.model,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"LLM call failed after {retries} retries: {last_error}")

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate and parse JSON response."""
        response = await self.generate(prompt, system_prompt, json_mode=True)
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end > start:
                    try:
                        return json.loads(response[start:end].strip())
                    except json.JSONDecodeError:
                        pass
            raise ValueError(
                f"Failed to parse JSON response: {e}\nResponse: {response[:500]}"
            )


# ---------------------------------------------------------------------------
# Base agent
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""

    name: str = "base_agent"
    description: str = "Base agent class"

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm = llm_client or LLMClient()
        self._log = get_logger(f"agents.{self.name}")

    @abstractmethod
    async def process(
        self, source_code: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Process source code and return findings."""
        ...

    def _extract_line_numbers(self, source_code: str, pattern: str) -> List[int]:
        """Find line numbers containing a pattern."""
        lines = source_code.split("\n")
        return [i + 1 for i, line in enumerate(lines) if pattern in line]

    def _get_line_content(self, source_code: str, line_number: int, context: int = 2) -> str:
        """Get code around a line number."""
        lines = source_code.split("\n")
        start = max(0, line_number - context - 1)
        end = min(len(lines), line_number + context)
        return "\n".join(f"{i+1}: {lines[i]}" for i in range(start, end))
