"""
Scanner Agent - Fast first-pass detection using Slither + LLM pattern matching.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from agents.base import BaseAgent, Finding, LLMClient, get_logger

_log = get_logger("agents.scanner")

SCANNER_PROMPT = """You are a senior smart contract security scanner. Analyze this Solidity code for common vulnerability patterns.

Focus on detecting:
1. Reentrancy patterns (external calls before state updates)
2. Access control issues (missing onlyOwner/onlyAdmin on sensitive functions)
3. tx.origin authentication vulnerabilities
4. Integer overflow/underflow in Solidity <0.8
5. Unchecked return values from external calls
6. Unsafe delegatecall
7. Weak randomness (block.timestamp, blockhash)
8. Gas optimization issues (unbounded loops, storage in loops)

For each finding, output JSON in this format:
{
  "findings": [
    {
      "issue_type": "reentrancy",
      "line_number": 15,
      "severity": "Critical",
      "description": "State update after external call allows reentrancy",
      "confidence": 0.85
    }
  ]
}

Source code to analyze:
```solidity
{source_code}
```

Output only valid JSON. If no issues found, return {{"findings": []}}"""


class ScannerAgent(BaseAgent):
    """
    Fast first-pass detection using Slither static analysis + LLM pattern matching.

    Workflow:
    1. Run Slither for known vulnerability patterns (fast, deterministic)
    2. Run LLM scan for subtle logic bugs Slither might miss
    3. Merge and dedupe findings
    """

    name = "scanner"
    description = "Fast vulnerability scanner using Slither + LLM"

    def __init__(self, llm_client: Optional[LLMClient] = None, slither_path: str = "slither") -> None:
        super().__init__(llm_client)
        self.slither_path = slither_path

    async def process(
        self, source_code: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Run hybrid scan: Slither + LLM."""
        context = context or {}

        _log.info("scanner_start", source_lines=len(source_code.split("\n")))

        # Run both in parallel for speed
        slither_task = asyncio.create_task(self._run_slither(source_code))
        llm_task = asyncio.create_task(self._llm_scan(source_code))

        try:
            slither_findings = await slither_task
        except Exception as exc:
            _log.warning("slither_error", error=str(exc))
            slither_findings = []

        try:
            llm_findings = await llm_task
        except Exception as exc:
            _log.warning("llm_scan_error", error=str(exc))
            llm_findings = []

        # Merge findings
        merged = self._merge_findings(slither_findings, llm_findings)

        # Mark source
        for f in merged:
            f.source = "scanner"

        _log.info(
            "scanner_done",
            slither=len(slither_findings),
            llm=len(llm_findings),
            merged=len(merged),
        )

        return merged

    async def _run_slither(self, source_code: str) -> List[Finding]:
        """Run Slither static analysis on the contract."""
        findings: List[Finding] = []

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sol", delete=False) as f:
            f.write(source_code)
            temp_path = f.name

        try:
            result = subprocess.run(
                [self.slither_path, temp_path, "--json", "-"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.stdout:
                try:
                    slither_output = json.loads(result.stdout)
                    findings = self._parse_slither_output(slither_output)
                except json.JSONDecodeError:
                    pass

        except subprocess.TimeoutExpired:
            _log.warning("slither_timeout")
        except FileNotFoundError:
            _log.info("slither_not_found", note="Skipping static analysis")
        except Exception as exc:
            _log.warning("slither_error", error=str(exc))
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        return findings

    def _parse_slither_output(self, slither_output: Dict[str, Any]) -> List[Finding]:
        """Parse Slither JSON output into Finding objects."""
        findings: List[Finding] = []

        detectors = slither_output.get("results", {}).get("detectors", [])

        severity_map = {
            "high": "Critical",
            "medium": "Medium",
            "low": "Low",
            "informational": "Info",
            "optimization": "Low",
        }

        confidence_map = {
            "high": 0.9,
            "medium": 0.7,
            "low": 0.5,
        }

        for detector in detectors:
            impact = detector.get("impact", "Informational").lower()
            confidence = detector.get("confidence", "Low").lower()

            finding = Finding(
                issue_type=detector.get("check", "unknown"),
                line_number=self._extract_line_from_slither(detector),
                severity=severity_map.get(impact, "Medium"),
                description=detector.get("description", ""),
                confidence=confidence_map.get(confidence, 0.5),
                metadata={"slither_id": detector.get("id")},
            )
            findings.append(finding)

        return findings

    def _extract_line_from_slither(self, detector: Dict[str, Any]) -> Optional[int]:
        """Extract line number from Slither detector output."""
        elements = detector.get("elements", [])
        if elements:
            line = elements[0].get("source_mapping", {}).get("lines", [])
            if line:
                return line[0]
        return None

    async def _llm_scan(self, source_code: str) -> List[Finding]:
        """Run LLM pattern scan for subtle vulnerabilities."""
        prompt = SCANNER_PROMPT.format(source_code=source_code)

        try:
            response = await self.llm.generate_json(prompt)

            findings: List[Finding] = []
            for item in response.get("findings", []):
                finding = Finding(
                    issue_type=item.get("issue_type", "unknown"),
                    line_number=item.get("line_number"),
                    severity=item.get("severity", "Medium"),
                    description=item.get("description", ""),
                    confidence=item.get("confidence", 0.5),
                )
                findings.append(finding)

            return findings

        except Exception as exc:
            _log.warning("llm_scan_parse_error", error=str(exc))
            return []

    def _merge_findings(
        self, slither_findings: List[Finding], llm_findings: List[Finding]
    ) -> List[Finding]:
        """Merge and deduplicate findings from multiple sources."""
        seen: set = set()
        merged: List[Finding] = []

        for finding in slither_findings + llm_findings:
            line_range = range(
                max(1, (finding.line_number or 0) - 3),
                (finding.line_number or 0) + 3,
            )
            key = (finding.issue_type.lower(), tuple(line_range))

            if key not in seen:
                seen.add(key)
                merged.append(finding)

        return merged


# Fast pattern matching for common issues (no LLM needed)
def quick_pattern_scan(source_code: str) -> List[Finding]:
    """
    Quick deterministic scan for common vulnerability patterns.
    This runs instantly without LLM, useful for fast feedback.
    """
    findings: List[Finding] = []
    lines = source_code.split("\n")

    # tx.origin detection
    for i, line in enumerate(lines):
        if "tx.origin" in line and ("require" in line or "if" in line):
            findings.append(
                Finding(
                    issue_type="tx_origin_auth",
                    line_number=i + 1,
                    severity="Critical",
                    description="tx.origin used for authorization - vulnerable to phishing attacks",
                    confidence=0.9,
                    source="pattern_scan",
                )
            )

    # Reentrancy pattern: external call before state update
    call_line: Optional[int] = None
    for i, line in enumerate(lines):
        if "call{" in line or ".call(" in line or ".delegatecall" in line:
            call_line = i + 1
            for j in range(i + 1, min(i + 10, len(lines))):
                if "balances[" in lines[j] and "=" in lines[j]:
                    if call_line:
                        findings.append(
                            Finding(
                                issue_type="reentrancy",
                                line_number=j + 1,
                                severity="Critical",
                                description="State update after external call - potential reentrancy",
                                confidence=0.75,
                                source="pattern_scan",
                            )
                        )
                    break

    # Unchecked return value
    for i, line in enumerate(lines):
        if ("call{" in line or ".call(" in line or ".send(" in line) and "require" not in line:
            if i > 0 and "=" in line and "require" not in lines[i - 1]:
                findings.append(
                    Finding(
                        issue_type="unchecked_return_value",
                        line_number=i + 1,
                        severity="Medium",
                        description="Unchecked return value from external call",
                        confidence=0.8,
                        source="pattern_scan",
                    )
                )

    return findings
