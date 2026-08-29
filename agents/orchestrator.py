"""
Agent Orchestrator - Coordinates the multi-agent analysis pipeline.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from agents.base import AuditResult, Finding, LLMClient
from agents.scanner import ScannerAgent, quick_pattern_scan
from agents.analyzer import AnalyzerAgent
from agents.exploit_gen import ExploitGenerator, get_exploit_template
from agents.fix_suggester import FixSuggester, get_fix_template


class AgentOrchestrator:
    """
    Coordinates the multi-agent analysis pipeline.

    Pipeline flow:
    1. Scanner (fast) → Initial findings via Slither + LLM
    2. Analyzer (deep) → Cross-verify and find complex issues
    3. ExploitGen (for critical) → Generate PoC exploits
    4. FixSuggester (for critical) → Generate verified patches

    All agents run in parallel where possible for speed.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        generate_exploits: bool = True,
        generate_fixes: bool = True,
    ):
        self.llm = llm_client or LLMClient()
        self.scanner = ScannerAgent(self.llm)
        self.analyzer = AnalyzerAgent(self.llm)
        self.exploit_gen = ExploitGenerator(self.llm) if generate_exploits else None
        self.fix_suggester = FixSuggester(self.llm) if generate_fixes else None

        self.generate_exploits = generate_exploits
        self.generate_fixes = generate_fixes

    async def analyze(
        self,
        source_code: str,
        task_id: Optional[str] = None,
    ) -> AuditResult:
        """
        Run the full multi-agent analysis pipeline.

        Args:
            source_code: Solidity source code to analyze
            task_id: Optional task category (task_1, task_2, task_3)

        Returns:
            AuditResult with findings, metrics, and exploit/fix data
        """
        start_time = time.time()
        metrics = {
            "scanner_findings": 0,
            "analyzer_findings": 0,
            "exploits_generated": 0,
            "fixes_generated": 0,
            "total_llm_calls": 0,
        }

        # Step 1: Quick pattern scan (instant, no LLM)
        pattern_findings = quick_pattern_scan(source_code)
        metrics["pattern_findings"] = len(pattern_findings)

        # Step 2: Run scanner and analyzer in parallel
        scanner_task = asyncio.create_task(
            self.scanner.process(source_code, {"pattern_findings": pattern_findings})
        )
        analyzer_task = asyncio.create_task(
            self.analyzer.process(source_code, {"pattern_findings": pattern_findings})
        )

        # Wait for both to complete
        scanner_findings, analyzer_findings = await asyncio.gather(
            scanner_task, analyzer_task
        )

        metrics["scanner_findings"] = len(scanner_findings)
        metrics["analyzer_findings"] = len(analyzer_findings)
        metrics["total_llm_calls"] = 2

        # Step 3: Merge findings with deduplication
        merged_findings = self._merge_findings(scanner_findings, analyzer_findings)

        # Add pattern findings that weren't caught
        for pf in pattern_findings:
            if not self._is_duplicate(pf, merged_findings):
                merged_findings.append(pf)

        # Step 4: Generate exploits and fixes for critical findings
        if self.generate_exploits or self.generate_fixes:
            for finding in merged_findings:
                if finding.severity == "Critical":
                    # Generate exploit
                    if self.generate_exploits and self.exploit_gen:
                        try:
                            # Try template first for speed
                            template = get_exploit_template(finding.issue_type)
                            if template:
                                finding.exploit_poc = template
                            else:
                                # Generate via LLM
                                finding.exploit_poc = await self.exploit_gen.generate_exploit(
                                    source_code, finding
                                )
                            metrics["exploits_generated"] += 1
                            metrics["total_llm_calls"] += 1
                        except Exception as e:
                            finding.exploit_poc = f"// Failed to generate exploit: {e}"

                    # Generate fix
                    if self.generate_fixes and self.fix_suggester:
                        try:
                            # Try template first for speed
                            template = get_fix_template(finding.issue_type)
                            if template:
                                finding.suggested_fix = template.get("fixed_code", "")
                            else:
                                # Generate via LLM
                                fix = await self.fix_suggester.suggest_fix(
                                    source_code, finding, finding.exploit_poc
                                )
                                finding.suggested_fix = fix.get("fixed_code", "")
                            metrics["fixes_generated"] += 1
                            metrics["total_llm_calls"] += 1
                        except Exception as e:
                            finding.suggested_fix = f"// Failed to generate fix: {e}"

        # Step 5: Rank findings by severity and confidence
        merged_findings.sort(
            key=lambda f: (
                {"Critical": 0, "Medium": 1, "Low": 2, "Info": 3}.get(f.severity, 1),
                -f.confidence,
            )
        )

        # Build result
        elapsed = time.time() - start_time

        result = AuditResult(
            findings=merged_findings,
            contract_info={
                "lines_of_code": len(source_code.split("\n")),
                "task_id": task_id,
            },
            agent_metrics=metrics,
            total_time_seconds=round(elapsed, 2),
        )

        return result

    def _merge_findings(
        self, scanner_findings: List[Finding], analyzer_findings: List[Finding]
    ) -> List[Finding]:
        """Merge findings from multiple agents, deduplicating by issue type and location."""
        merged = []
        seen = set()

        for finding in scanner_findings + analyzer_findings:
            key = self._make_dedup_key(finding)
            if key not in seen:
                seen.add(key)
                merged.append(finding)

        return merged

    def _make_dedup_key(self, finding: Finding) -> tuple:
        """Create a deduplication key for a finding."""
        # Normalize issue type
        issue_type = finding.issue_type.lower().replace("_", "").replace("-", "")

        # Line range (allow 5 line tolerance)
        line = finding.line_number or 0
        line_range = (max(0, line - 5), line + 5)

        return (issue_type, line_range)

    def _is_duplicate(self, finding: Finding, existing: List[Finding]) -> bool:
        """Check if a finding is a duplicate of existing findings."""
        key = self._make_dedup_key(finding)
        for existing_finding in existing:
            if self._make_dedup_key(existing_finding) == key:
                return True
        return False


async def analyze_contract(
    source_code: str,
    task_id: Optional[str] = None,
    llm_base_url: Optional[str] = None,
) -> AuditResult:
    """
    Convenience function to analyze a contract.

    Args:
        source_code: Solidity source code
        task_id: Optional task category
        llm_base_url: Optional LLM endpoint (defaults to env var or HF router)

    Returns:
        AuditResult with findings
    """
    llm_client = LLMClient(base_url=llm_base_url) if llm_base_url else None
    orchestrator = AgentOrchestrator(llm_client=llm_client)
    return await orchestrator.analyze(source_code, task_id)


# Sync wrapper for convenience
def analyze_contract_sync(
    source_code: str,
    task_id: Optional[str] = None,
    llm_base_url: Optional[str] = None,
) -> AuditResult:
    """Synchronous wrapper for analyze_contract."""
    return asyncio.run(analyze_contract(source_code, task_id, llm_base_url))
