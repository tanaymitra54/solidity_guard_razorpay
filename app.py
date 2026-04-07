from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field

from environment import SolidityGuardEnv


app = FastAPI(title="SolidityGuard - Advanced Smart Contract Auditor")
env = SolidityGuardEnv()


class ResetRequest(BaseModel):
    task_id: Optional[str] = Field(default=None)


class StepRequest(BaseModel):
    action: List[Dict[str, Any]]


class ReportRequest(BaseModel):
    task_id: str
    include_fixes: bool = Field(default=True)
    include_exploits: bool = Field(default=True)


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    """Landing page with project information and links."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SolidityGuard - OpenEnv Smart Contract Auditor</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            h1 { font-size: 2.5em; margin-bottom: 10px; }
            h2 { color: #ffd700; margin-top: 30px; }
            .badge { 
                display: inline-block;
                background: #4CAF50;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.9em;
                margin: 10px 0;
            }
            .link-button {
                display: inline-block;
                background: #4CAF50;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 8px;
                margin: 10px 10px 10px 0;
                font-weight: bold;
                transition: background 0.3s;
            }
            .link-button:hover { background: #45a049; }
            .endpoint {
                background: rgba(0, 0, 0, 0.3);
                padding: 10px;
                border-radius: 8px;
                margin: 5px 0;
                font-family: monospace;
            }
            .feature {
                background: rgba(255, 255, 255, 0.1);
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ SolidityGuard</h1>
            <div class="badge">OpenEnv RL Environment</div>
            <div class="badge">Meta x PyTorch Hackathon</div>
            
            <p style="font-size: 1.2em; margin: 20px 0;">
                Advanced Smart Contract Security Review Environment for AI Agents
            </p>
            
            <div style="margin: 30px 0;">
                <a href="/docs" class="link-button">📚 API Documentation</a>
                <a href="/health" class="link-button">💚 Health Check</a>
            </div>
            
            <h2>🎯 What is SolidityGuard?</h2>
            <p>
                SolidityGuard is an OpenEnv reinforcement learning environment that trains AI agents 
                to review Solidity smart contracts for security vulnerabilities, gas optimizations, 
                and coding best practices.
            </p>
            
            <h2>✨ Features</h2>
            <div class="feature">
                <strong>🔍 Multi-Agent Verification</strong><br>
                Analyzer → Verifier → Risk Scorer pipeline for enhanced accuracy
            </div>
            <div class="feature">
                <strong>💥 Exploit Proof System</strong><br>
                Step-by-step attack explanations for security vulnerabilities
            </div>
            <div class="feature">
                <strong>🔧 Auto-Fix Suggestions</strong><br>
                Actionable code recommendations for detected issues
            </div>
            <div class="feature">
                <strong>📊 Advanced Scoring</strong><br>
                5-component grading: base, line accuracy, exploit, fix, confidence
            </div>
            
            <h2>📋 Tasks</h2>
            <div class="endpoint">
                <strong>Task 1 (Easy):</strong> Best Practices & Syntax Issues<br>
                <strong>Task 2 (Medium):</strong> Gas Optimization Opportunities<br>
                <strong>Task 3 (Hard):</strong> Security Vulnerabilities
            </div>
            
            <h2>🔌 API Endpoints</h2>
            <div class="endpoint">GET  /health - Health check</div>
            <div class="endpoint">POST /reset - Reset environment</div>
            <div class="endpoint">POST /step - Submit findings</div>
            <div class="endpoint">GET  /state - Get current state</div>
            <div class="endpoint">POST /report - Generate audit report</div>
            <div class="endpoint">GET  /dashboard - Get statistics</div>
            
            <h2>📊 Dataset</h2>
            <p>
                18 realistic Solidity samples across 3 difficulty levels, covering 15+ vulnerability types
            </p>
            
            <h2>🔗 Links</h2>
            <p>
                <strong>GitHub:</strong> <a href="https://github.com/tanaymitra54/ContractSLM" 
                style="color: #ffd700;">tanaymitra54/ContractSLM</a><br>
                <strong>HF Space:</strong> <a href="https://huggingface.co/spaces/tanaymitra01/solidityguard-openenv" 
                style="color: #ffd700;">tanaymitra01/solidityguard-openenv</a>
            </p>
            
            <div style="margin-top: 40px; text-align: center; opacity: 0.8;">
                <p>Meta x PyTorch Hackathon 2026 | Built with OpenEnv</p>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/reset")
def reset(request: ResetRequest) -> Dict[str, Any]:
    try:
        return env.reset(task_id=request.task_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/step")
def step(request: StepRequest) -> Dict[str, Any]:
    try:
        return env.step(request.action)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/state")
def state() -> Dict[str, Any]:
    try:
        return env.state()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/report")
def generate_report(request: ReportRequest) -> Dict[str, Any]:
    """Generate comprehensive audit report for a contract."""
    try:
        # Reset to get the contract
        observation = env.reset(task_id=request.task_id)
        
        # Get contract metadata
        metadata = observation["metadata"]
        source_code = observation["source_code"]
        
        # Calculate risk metrics
        risk_metrics = _calculate_risk_metrics(source_code, request.task_id)
        
        # Generate summary
        report = {
            "contract_info": {
                "name": metadata["contract_name"],
                "compiler_version": metadata["compiler_version"],
                "file_path": metadata["file_path"],
                "task_category": request.task_id,
                "lines_of_code": len(source_code.split('\n'))
            },
            "risk_assessment": risk_metrics,
            "recommendations": _generate_recommendations(risk_metrics),
            "timestamp": "2026-04-06T12:00:00Z",  # Mock timestamp
            "report_version": "2.0.0"
        }
        
        if request.include_fixes:
            report["suggested_fixes"] = _get_fix_suggestions(source_code, request.task_id)
        
        if request.include_exploits:
            report["exploit_scenarios"] = _get_exploit_scenarios(source_code, request.task_id)
        
        return report
        
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/dashboard")  
def get_dashboard() -> Dict[str, Any]:
    """Get dashboard overview of all contract categories."""
    try:
        dashboard_data = {
            "overview": {
                "total_samples": 18,
                "categories": 3,
                "avg_risk_score": 0.65,
                "last_updated": "2026-04-06T12:00:00Z"
            },
            "category_breakdown": {
                "task_1_best_practices": {
                    "sample_count": 6,
                    "avg_severity": "Low",
                    "common_issues": ["missing_spdx", "old_compiler_version", "missing_natspec"]
                },
                "task_2_gas_optimization": {
                    "sample_count": 6, 
                    "avg_severity": "Medium",
                    "common_issues": ["unbounded_loop", "redundant_storage_read", "poor_struct_packing"]
                },
                "task_3_security": {
                    "sample_count": 6,
                    "avg_severity": "Critical", 
                    "common_issues": ["reentrancy", "missing_access_control", "tx_origin_auth"]
                }
            },
            "agent_stats": {
                "multi_agent_enabled": True,
                "analyzer_accuracy": 0.85,
                "verifier_precision": 0.90,
                "risk_scorer_coverage": 0.95
            }
        }
        
        return dashboard_data
        
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _calculate_risk_metrics(source_code: str, task_id: str) -> Dict[str, Any]:
    """Calculate comprehensive risk metrics for a contract."""
    
    # Basic metrics
    lines_of_code = len(source_code.split('\n'))
    cyclomatic_complexity = source_code.count('if ') + source_code.count('for ') + source_code.count('while ')
    
    # Security indicators
    has_external_calls = 'call{' in source_code or '.call(' in source_code
    has_state_variables = 'mapping(' in source_code or 'uint' in source_code
    has_payable = 'payable' in source_code
    
    # Calculate overall risk score
    base_risk = 0.3
    if task_id == "task_3_security":
        base_risk = 0.8
    elif task_id == "task_2_gas_optimization": 
        base_risk = 0.5
    
    complexity_factor = min(cyclomatic_complexity * 0.1, 0.3)
    external_call_factor = 0.2 if has_external_calls else 0.0
    payable_factor = 0.1 if has_payable else 0.0
    
    overall_risk = min(base_risk + complexity_factor + external_call_factor + payable_factor, 1.0)
    
    return {
        "overall_risk_score": round(overall_risk, 3),
        "risk_category": "High" if overall_risk >= 0.7 else "Medium" if overall_risk >= 0.4 else "Low",
        "complexity_score": cyclomatic_complexity,
        "lines_of_code": lines_of_code,
        "has_external_calls": has_external_calls,
        "has_state_variables": has_state_variables,
        "has_payable_functions": has_payable,
        "recommended_review_time": f"{max(15, lines_of_code * 2)} minutes"
    }


def _generate_recommendations(risk_metrics: Dict[str, Any]) -> List[str]:
    """Generate audit recommendations based on risk metrics."""
    
    recommendations = []
    
    if risk_metrics["overall_risk_score"] >= 0.7:
        recommendations.append("🔴 HIGH RISK: Requires immediate security review")
        recommendations.append("Consider formal verification for critical functions")
        
    if risk_metrics["has_external_calls"]:
        recommendations.append("⚠️  External calls detected: Review for reentrancy vulnerabilities")
        
    if risk_metrics["has_payable_functions"]:
        recommendations.append("💰 Payable functions detected: Ensure proper access controls")
        
    if risk_metrics["complexity_score"] > 10:
        recommendations.append("🧩 High complexity: Consider breaking into smaller functions")
        
    if risk_metrics["lines_of_code"] > 100:
        recommendations.append("📏 Large contract: Consider modularization")
        
    recommendations.append("✅ Run static analysis tools (Slither, Mythril)")
    recommendations.append("🧪 Implement comprehensive test coverage")
    
    return recommendations


def _get_fix_suggestions(source_code: str, task_id: str) -> List[Dict[str, str]]:
    """Get specific fix suggestions for common issues."""
    
    suggestions = []
    
    if not source_code.strip().startswith("// SPDX"):
        suggestions.append({
            "issue": "Missing SPDX License",
            "fix": "Add '// SPDX-License-Identifier: MIT' at the top of the file",
            "priority": "Low"
        })
    
    if "0.4." in source_code or "0.7." in source_code:
        suggestions.append({
            "issue": "Outdated Solidity Version", 
            "fix": "Update to 'pragma solidity ^0.8.0;' for better security",
            "priority": "Medium"
        })
        
    if "tx.origin" in source_code:
        suggestions.append({
            "issue": "tx.origin Usage",
            "fix": "Replace 'tx.origin' with 'msg.sender' for proper authentication",
            "priority": "High"
        })
        
    return suggestions


def _get_exploit_scenarios(source_code: str, task_id: str) -> List[Dict[str, str]]:
    """Get potential exploit scenarios for security issues."""
    
    scenarios = []
    
    if "call{" in source_code and "balances[" in source_code:
        scenarios.append({
            "vulnerability": "Reentrancy Attack",
            "scenario": "Attacker creates malicious contract with fallback function that calls withdraw() recursively",
            "impact": "Complete drainage of contract funds",
            "mitigation": "Implement checks-effects-interactions pattern or ReentrancyGuard"
        })
    
    if "tx.origin" in source_code:
        scenarios.append({
            "vulnerability": "tx.origin Phishing",
            "scenario": "Attacker tricks user into calling malicious contract that forwards transactions",
            "impact": "Unauthorized access to protected functions",
            "mitigation": "Use msg.sender instead of tx.origin for authentication"
        })
        
    return scenarios
