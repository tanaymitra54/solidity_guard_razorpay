"""
Multi-agent verification system for SolidityGuard.
Implements analyzer, verifier, and risk scorer agents.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AgentFinding:
    """Enhanced finding with agent verification data."""
    issue_type: str
    line_number: Optional[int]
    description: str
    severity: str
    exploit_path: Optional[str] = None
    recommended_fix: Optional[str] = None
    confidence: Optional[float] = None
    analyzer_confidence: Optional[float] = None
    verifier_confidence: Optional[float] = None
    risk_score: Optional[float] = None
    agent_consensus: Optional[float] = None


class AnalyzerAgent:
    """Primary agent that finds security issues."""
    
    def analyze(self, source_code: str, task_id: str) -> List[Dict[str, Any]]:
        """Simulate initial analysis (in real implementation, this would call LLM)."""
        
        # Mock analysis based on task type and code patterns
        findings = []
        
        # Security analysis
        if task_id == "task_3_security":
            # Reentrancy detection
            if ("call{" in source_code or ".call(" in source_code) and ("balances[" in source_code or "amount" in source_code):
                # Look for state change after external call
                lines = source_code.split('\n')
                for i, line in enumerate(lines):
                    if "call{" in line or ".call(" in line:
                        # Check if balance update happens after the call
                        for j in range(i+1, len(lines)):
                            if "balances[" in lines[j] and "=" in lines[j]:
                                findings.append({
                                    "issue_type": "reentrancy",
                                    "line_number": j + 1,
                                    "description": "State update after external call allows reentrancy",
                                    "severity": "Critical",
                                    "exploit_path": "Attacker can recursively call function before balance update",
                                    "recommended_fix": "Use checks-effects-interactions pattern",
                                    "confidence": 0.85,
                                    "analyzer_confidence": 0.85
                                })
                                break
                        break
            
            # Access control detection  
            if "function " in source_code and ("admin" in source_code.lower() or "owner" in source_code.lower()):
                lines = source_code.split('\n')
                for i, line in enumerate(lines):
                    if "function " in line and "public" in line:
                        # Check if function has access control
                        func_body = []
                        brace_count = 0
                        for j in range(i, len(lines)):
                            if "{" in lines[j]:
                                brace_count += lines[j].count("{")
                            if "}" in lines[j]:
                                brace_count -= lines[j].count("}")
                            func_body.append(lines[j])
                            if brace_count == 0 and "{" in lines[i]:
                                break
                        
                        func_text = " ".join(func_body)
                        if "require" not in func_text and "modifier" not in func_text:
                            if "setAdmin" in line or "admin" in line.lower():
                                findings.append({
                                    "issue_type": "missing_access_control",
                                    "line_number": i + 1,
                                    "description": "Sensitive function lacks access control",
                                    "severity": "Critical", 
                                    "exploit_path": "Any user can call this function and gain admin privileges",
                                    "recommended_fix": "Add access control modifier or require statement",
                                    "confidence": 0.75,
                                    "analyzer_confidence": 0.75
                                })
            
            # tx.origin detection
            if "tx.origin" in source_code:
                lines = source_code.split('\n')
                for i, line in enumerate(lines):
                    if "tx.origin" in line:
                        findings.append({
                            "issue_type": "tx_origin_auth",
                            "line_number": i + 1,
                            "description": "Authorization uses tx.origin",
                            "severity": "Critical",
                            "exploit_path": "Attacker can trick user into calling malicious contract",
                            "recommended_fix": "Replace tx.origin with msg.sender",
                            "confidence": 0.90,
                            "analyzer_confidence": 0.90
                        })
        
        # Gas optimization analysis
        elif task_id == "task_2_gas_optimization":
            # Loop optimization
            if "for (" in source_code and ".length" in source_code:
                lines = source_code.split('\n')
                for i, line in enumerate(lines):
                    if "for (" in line and ".length" in line:
                        findings.append({
                            "issue_type": "unbounded_loop",
                            "line_number": i + 1,
                            "description": "Loop uses dynamic array length without bounds",
                            "severity": "Medium",
                            "recommended_fix": "Cache array length in local variable",
                            "confidence": 0.80,
                            "analyzer_confidence": 0.80
                        })
            
            # Storage optimization
            if "storage" in source_code.lower() or ("uint" in source_code and "mapping" in source_code):
                # Check for repeated storage reads
                lines = source_code.split('\n')
                for i, line in enumerate(lines):
                    # Simple heuristic for repeated storage access
                    if "+=" in line and any(storage_var in line for storage_var in ["fee", "price", "balance"]):
                        findings.append({
                            "issue_type": "redundant_storage_read", 
                            "line_number": i + 1,
                            "description": "Repeated storage reads could be cached",
                            "severity": "Medium",
                            "recommended_fix": "Cache storage variable in memory",
                            "confidence": 0.70,
                            "analyzer_confidence": 0.70
                        })
        
        # Best practices analysis
        elif task_id == "task_1_best_practices":
            # SPDX check
            if not source_code.strip().startswith("// SPDX"):
                findings.append({
                    "issue_type": "missing_spdx", 
                    "line_number": 1,
                    "description": "Missing SPDX license identifier",
                    "severity": "Low",
                    "recommended_fix": "Add // SPDX-License-Identifier: MIT at top of file",
                    "confidence": 0.95,
                    "analyzer_confidence": 0.95
                })
            
            # Compiler version check
            if "pragma solidity" in source_code:
                if "0.4." in source_code or "0.5." in source_code or "0.6." in source_code or "0.7." in source_code:
                    lines = source_code.split('\n')
                    for i, line in enumerate(lines):
                        if "pragma solidity" in line:
                            findings.append({
                                "issue_type": "old_compiler_version",
                                "line_number": i + 1, 
                                "description": "Compiler version below 0.8.x",
                                "severity": "Low",
                                "recommended_fix": "Update to pragma solidity ^0.8.0 or higher",
                                "confidence": 0.85,
                                "analyzer_confidence": 0.85
                            })
            
            # NatSpec check
            if "function " in source_code and "public" in source_code:
                lines = source_code.split('\n')
                for i, line in enumerate(lines):
                    if "function " in line and "public" in line:
                        # Check if previous lines contain NatSpec
                        has_natspec = False
                        for j in range(max(0, i-3), i):
                            if "///" in lines[j] or "/**" in lines[j]:
                                has_natspec = True
                                break
                        
                        if not has_natspec:
                            findings.append({
                                "issue_type": "missing_natspec",
                                "line_number": i + 1,
                                "description": "Public function missing NatSpec comment", 
                                "severity": "Low",
                                "recommended_fix": "Add /// @notice or /** */ comment above function",
                                "confidence": 0.75,
                                "analyzer_confidence": 0.75
                            })
                            break  # Only report first occurrence
        
        return findings


class VerifierAgent:
    """Secondary agent that verifies and adjusts findings."""
    
    def verify(self, findings: List[Dict[str, Any]], source_code: str) -> List[Dict[str, Any]]:
        """Verify findings and adjust confidence/severity."""
        
        verified_findings = []
        
        for finding in findings:
            # Simulate verification logic
            verifier_confidence = finding.get("analyzer_confidence", 0.5)
            
            # Adjust confidence based on verification
            if finding["issue_type"] == "reentrancy":
                # Check if external call exists
                if "call{" in source_code and "balances[" in source_code:
                    verifier_confidence = min(verifier_confidence + 0.1, 1.0)
                else:
                    verifier_confidence = max(verifier_confidence - 0.2, 0.0)
            
            elif finding["issue_type"] == "missing_spdx":
                # Simple check
                if not source_code.strip().startswith("// SPDX"):
                    verifier_confidence = 0.99
                else:
                    verifier_confidence = 0.0  # False positive
            
            # Only include if verifier confidence is reasonable
            if verifier_confidence >= 0.3:
                finding["verifier_confidence"] = verifier_confidence
                finding["confidence"] = (finding.get("analyzer_confidence", 0.5) + verifier_confidence) / 2
                verified_findings.append(finding)
        
        return verified_findings


class RiskScorerAgent:
    """Tertiary agent that assigns risk scores."""
    
    def score_risk(self, findings: List[Dict[str, Any]], source_code: str) -> List[Dict[str, Any]]:
        """Assign final risk scores to findings."""
        
        scored_findings = []
        
        for finding in findings:
            # Calculate risk score based on severity, confidence, and context
            severity_weight = {
                "Critical": 1.0,
                "Medium": 0.6, 
                "Low": 0.3,
                "Info": 0.1
            }.get(finding["severity"], 0.5)
            
            confidence = finding.get("confidence", 0.5)
            
            # Contextual risk factors
            context_multiplier = 1.0
            if finding["issue_type"] == "reentrancy" and "payable" in source_code:
                context_multiplier = 1.2  # Higher risk if contract handles funds
            
            risk_score = severity_weight * confidence * context_multiplier
            risk_score = min(risk_score, 1.0)
            
            finding["risk_score"] = round(risk_score, 3)
            
            # Calculate consensus score
            analyzer_conf = finding.get("analyzer_confidence", 0.5)
            verifier_conf = finding.get("verifier_confidence", 0.5)
            consensus = min(analyzer_conf, verifier_conf)  # Conservative consensus
            finding["agent_consensus"] = round(consensus, 3)
            
            scored_findings.append(finding)
        
        return scored_findings


class MultiAgentSystem:
    """Orchestrates the multi-agent verification process."""
    
    def __init__(self):
        self.analyzer = AnalyzerAgent()
        self.verifier = VerifierAgent()
        self.risk_scorer = RiskScorerAgent()
    
    def process(self, source_code: str, task_id: str) -> List[Dict[str, Any]]:
        """Run complete multi-agent analysis pipeline."""
        
        # Step 1: Analyzer finds issues
        initial_findings = self.analyzer.analyze(source_code, task_id)
        
        # Step 2: Verifier cross-checks
        verified_findings = self.verifier.verify(initial_findings, source_code)
        
        # Step 3: Risk scorer assigns final scores
        final_findings = self.risk_scorer.score_risk(verified_findings, source_code)
        
        return final_findings
    
    def get_pipeline_stats(self, initial_count: int, verified_count: int, final_count: int) -> Dict[str, Any]:
        """Get statistics about the multi-agent pipeline."""
        return {
            "initial_findings": initial_count,
            "verified_findings": verified_count,
            "final_findings": final_count,
            "verification_rate": verified_count / max(initial_count, 1),
            "final_rate": final_count / max(initial_count, 1)
        }


# Example usage
if __name__ == "__main__":
    system = MultiAgentSystem()
    
    # Test with reentrancy contract
    test_code = '''
    contract Test {
        mapping(address => uint256) balances;
        
        function withdraw() public {
            uint256 amount = balances[msg.sender];
            require(amount > 0);
            (bool success, ) = msg.sender.call{value: amount}("");
            require(success);
            balances[msg.sender] = 0;
        }
    }
    '''
    
    findings = system.process(test_code, "task_3_security")
    print(json.dumps(findings, indent=2))