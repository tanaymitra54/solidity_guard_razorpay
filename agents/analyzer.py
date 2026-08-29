"""
Deep Analyzer Agent - LLM-powered deep analysis with cross-function reasoning.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.base import BaseAgent, Finding, LLMClient


ANALYZER_PROMPT = """You are an elite smart contract security auditor with 10+ years of experience. Perform a deep security analysis of this Solidity contract.

Focus on:
1. **Logic errors**: Incorrect conditions, unintended state transitions, business logic flaws
2. **Access control**: Missing modifiers, privilege escalation paths, role manipulation
3. **Economic attacks**: Price manipulation, MEV vulnerabilities, flash loan exploits
4. **Integration risks**: External call risks, oracle manipulation, cross-contract vulnerabilities
5. **State management**: Storage collisions, uninitialized variables, improper state updates
6. **Edge cases**: Unexpected inputs, boundary conditions, race conditions

For each finding, provide detailed analysis:
{{
  "findings": [
    {{
      "issue_type": "specific_vulnerability_name",
      "line_number": 15,
      "severity": "Critical",
      "description": "Clear explanation of what's wrong and why it matters",
      "exploit_scenario": "Step-by-step attack description: 1) Attacker does X, 2) This triggers Y...",
      "confidence": 0.85
    }}
  ]
}}

Previous findings from scanner (verify these and add new ones):
{scanner_findings}

Source code:
```solidity
{source_code}
```

Output only valid JSON. Be thorough but only report real vulnerabilities with high confidence."""


class AnalyzerAgent(BaseAgent):
    """
    LLM-powered deep analysis agent with cross-function reasoning.

    This agent:
    1. Analyzes the entire contract holistically
    2. Traces data flow across functions
    3. Identifies complex vulnerability patterns
    4. Verifies scanner findings and adds new ones
    """

    name = "analyzer"
    description = "Deep LLM-powered vulnerability analysis"

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(llm_client)

    async def process(
        self, source_code: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Perform deep analysis on the contract."""
        context = context or {}

        # Get scanner findings from context if available
        scanner_findings = context.get("scanner_findings", [])
        scanner_summary = self._summarize_findings(scanner_findings)

        # Run deep analysis
        prompt = ANALYZER_PROMPT.format(
            source_code=source_code,
            scanner_findings=scanner_summary,
        )

        try:
            response = await self.llm.generate_json(prompt)

            findings = []
            for item in response.get("findings", []):
                finding = Finding(
                    issue_type=item.get("issue_type", "unknown"),
                    line_number=item.get("line_number"),
                    severity=item.get("severity", "Medium"),
                    description=item.get("description", ""),
                    exploit_scenario=item.get("exploit_scenario"),
                    confidence=item.get("confidence", 0.5),
                    source="analyzer",
                )
                findings.append(finding)

            # Cross-verify scanner findings
            verified = self._verify_scanner_findings(scanner_findings, findings)

            # Merge verified scanner findings with new findings
            all_findings = verified + [f for f in findings if f not in verified]

            return all_findings

        except Exception as e:
            print(f"[Analyzer] Error: {e}")
            return []

    def _summarize_findings(self, findings: List[Finding]) -> str:
        """Create a summary of scanner findings for the prompt."""
        if not findings:
            return "No prior findings."

        summary_lines = []
        for f in findings[:10]:  # Limit to prevent token explosion
            summary_lines.append(
                f"- {f.issue_type} (line {f.line_number}, {f.severity}): {f.description[:100]}"
            )

        return "\n".join(summary_lines)

    def _verify_scanner_findings(
        self, scanner_findings: List[Finding], analyzer_findings: List[Finding]
    ) -> List[Finding]:
        """
        Cross-verify scanner findings with analyzer results.
        If analyzer found similar issues, boost confidence.
        If analyzer didn't find them, slightly reduce confidence.
        """
        verified = []

        for scanner_f in scanner_findings:
            # Check if analyzer found something similar
            similar = self._find_similar_finding(scanner_f, analyzer_findings)

            if similar:
                # Boost confidence if analyzer agrees
                scanner_f.confidence = min(1.0, scanner_f.confidence + 0.1)
                scanner_f.metadata["verified_by"] = "analyzer"
                verified.append(scanner_f)
            else:
                # Slightly reduce confidence if analyzer didn't find it
                scanner_f.confidence = max(0.3, scanner_f.confidence - 0.1)
                scanner_f.metadata["unverified"] = True
                verified.append(scanner_f)

        return verified

    def _find_similar_finding(
        self, finding: Finding, candidates: List[Finding]
    ) -> Optional[Finding]:
        """Find a similar finding in the candidate list."""
        for candidate in candidates:
            # Same issue type and nearby line number
            if finding.issue_type.lower() == candidate.issue_type.lower():
                if finding.line_number and candidate.line_number:
                    if abs(finding.line_number - candidate.line_number) <= 5:
                        return candidate
        return None


# Severity classification helper
def classify_severity(issue_type: str, description: str) -> str:
    """
    Classify severity based on issue type and description.
    This helps ensure consistent severity ratings across agents.
    """
    critical_patterns = [
        "reentrancy",
        "access control",
        "privilege escalation",
        "drain",
        "steal",
        "bypass",
    ]

    medium_patterns = [
        "unchecked",
        "race condition",
        "front-run",
        "oracle",
        "manipulation",
    ]

    low_patterns = [
        "gas",
        "optimization",
        "style",
        "natspec",
        "spdx",
    ]

    issue_lower = issue_type.lower()
    desc_lower = description.lower()

    for pattern in critical_patterns:
        if pattern in issue_lower or pattern in desc_lower:
            return "Critical"

    for pattern in medium_patterns:
        if pattern in issue_lower or pattern in desc_lower:
            return "Medium"

    for pattern in low_patterns:
        if pattern in issue_lower or pattern in desc_lower:
            return "Low"

    return "Medium"
