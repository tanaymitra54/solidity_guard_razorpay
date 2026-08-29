"""
Multi-Agent System for SolidityGuard.

A production-grade multi-agent architecture for smart contract auditing.
Each agent specializes in a specific aspect of vulnerability detection and remediation.
"""

from agents.base import BaseAgent, Finding, AuditResult, LLMClient
from agents.scanner import ScannerAgent
from agents.analyzer import AnalyzerAgent
from agents.exploit_gen import ExploitGenerator
from agents.fix_suggester import FixSuggester
from agents.orchestrator import AgentOrchestrator

__all__ = [
    "BaseAgent",
    "Finding",
    "AuditResult",
    "LLMClient",
    "ScannerAgent",
    "AnalyzerAgent",
    "ExploitGenerator",
    "FixSuggester",
    "AgentOrchestrator",
]
