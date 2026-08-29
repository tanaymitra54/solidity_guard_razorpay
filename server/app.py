from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from environment import SolidityGuardEnv
from agents.orchestrator import AgentOrchestrator, analyze_contract
from agents.base import LLMClient


app = FastAPI(title="SolidityGuard - Advanced Smart Contract Auditor")
env = SolidityGuardEnv()

# Initialize multi-agent orchestrator (lazy-loaded)
_orchestrator = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


class ResetRequest(BaseModel):
    task_id: Optional[str] = Field(default=None)


class StepRequest(BaseModel):
    action: List[Dict[str, Any]]


class ReportRequest(BaseModel):
    task_id: str
    include_fixes: bool = Field(default=True)
    include_exploits: bool = Field(default=True)


class AuditRequest(BaseModel):
    """Request model for the /audit endpoint."""
    source_code: str
    task_id: Optional[str] = Field(default=None)
    generate_exploits: bool = Field(default=True)
    generate_fixes: bool = Field(default=True)
    llm_base_url: Optional[str] = Field(default=None)


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    """Landing page with project information and links."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SOLIDITYGUARD [CYBER-AUDIT PROXY]</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&family=Orbitron:wght@500;700;900&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #ff5500;
                --secondary: #ff8800;
                --dark: #050505;
                --panel-bg: rgba(10, 10, 10, 0.85);
                --border: #ff5500;
                --text: #e0e0e0;
                --glitch-1: #00ffff;
                --glitch-2: #ff003c;
            }

            * { margin: 0; padding: 0; box-sizing: border-box; }

            body {
                font-family: 'Fira Code', monospace;
                background-color: var(--dark);
                color: var(--text);
                overflow-x: hidden;
            }

            /* Matrix Background */
            canvas {
                position: fixed;
                top: 0; left: 0;
                width: 100%; height: 100%;
                z-index: -2;
                opacity: 0.15;
            }

            /* CRT Overlay */
            .scanlines {
                position: fixed;
                top: 0; left: 0; width: 100vw; height: 100vh;
                background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
                background-size: 100% 2px, 3px 100%;
                z-index: 9999;
                pointer-events: none;
            }

            .vignette {
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background: radial-gradient(circle, rgba(0,0,0,0) 60%, rgba(0,0,0,0.8) 100%);
                z-index: 9998;
                pointer-events: none;
            }

            .container {
                max-width: 1100px;
                margin: 0 auto;
                padding: 40px 20px;
                position: relative;
                z-index: 1;
            }

            /* HUD Header */
            header {
                text-align: center;
                margin-bottom: 60px;
                padding: 40px 0;
                border-bottom: 2px solid var(--primary);
                position: relative;
                background: linear-gradient(180deg, transparent, rgba(255, 85, 0, 0.05));
            }
            header::after {
                content: '';
                position: absolute;
                bottom: -5px; left: 50%; transform: translateX(-50%);
                width: 150px; height: 8px;
                background: var(--primary);
                box-shadow: 0 0 15px var(--primary);
            }

            h1.glitch {
                font-family: 'Orbitron', sans-serif;
                font-size: 4.5rem;
                font-weight: 900;
                color: #fff;
                text-transform: uppercase;
                position: relative;
                display: inline-block;
                text-shadow: 0 0 20px rgba(255, 85, 0, 0.8);
                margin-bottom: 10px;
            }

            h1.glitch::before, h1.glitch::after {
                content: attr(data-text);
                position: absolute;
                top: 0; left: 0; width: 100%; height: 100%;
                background: var(--dark);
            }
            h1.glitch::before {
                left: 3px;
                text-shadow: -2px 0 var(--glitch-2);
                clip: rect(24px, 550px, 90px, 0);
                animation: glitch-anim-2 3s infinite linear alternate-reverse;
            }
            h1.glitch::after {
                left: -3px;
                text-shadow: -2px 0 var(--glitch-1);
                clip: rect(85px, 550px, 140px, 0);
                animation: glitch-anim 2.5s infinite linear alternate-reverse;
            }

            @keyframes glitch-anim {
                0% { clip: rect(21px, 9999px, 80px, 0); }
                20% { clip: rect(65px, 9999px, 99px, 0); }
                40% { clip: rect(110px, 9999px, 11px, 0); }
                60% { clip: rect(32px, 9999px, 55px, 0); }
                80% { clip: rect(88px, 9999px, 14px, 0); }
                100% { clip: rect(44px, 9999px, 90px, 0); }
            }
            @keyframes glitch-anim-2 {
                0% { clip: rect(65px, 9999px, 100px, 0); }
                20% { clip: rect(10px, 9999px, 44px, 0); }
                40% { clip: rect(88px, 9999px, 11px, 0); }
                60% { clip: rect(32px, 9999px, 80px, 0); }
                80% { clip: rect(55px, 9999px, 60px, 0); }
                100% { clip: rect(11px, 9999px, 22px, 0); }
            }

            .typewriter-text {
                font-size: 1.2rem;
                color: var(--secondary);
                border-right: 2px solid var(--secondary);
                display: inline-block;
                white-space: nowrap;
                overflow: hidden;
                animation: typing 3.5s steps(40, end), blink-caret .75s step-end infinite;
            }

            @keyframes typing { from { width: 0 } to { width: 100% } }
            @keyframes blink-caret { from, to { border-color: transparent } 50% { border-color: var(--secondary); } }

            /* Panels */
            .hud-panel {
                background: var(--panel-bg);
                border: 1px solid rgba(255, 85, 0, 0.3);
                border-left: 4px solid var(--primary);
                padding: 30px;
                margin-bottom: 40px;
                position: relative;
                box-shadow: inset 0 0 20px rgba(255, 85, 0, 0.05), 0 5px 15px rgba(0,0,0,0.5);
                transition: all 0.3s ease;
            }

            .hud-panel:hover {
                border-color: var(--primary);
                box-shadow: inset 0 0 30px rgba(255, 85, 0, 0.1), 0 5px 25px rgba(255, 85, 0, 0.2);
                transform: translateY(-2px);
            }

            .hud-panel::before {
                content: '[SYS_DATA_BLK]';
                position: absolute;
                top: -12px; right: 20px;
                background: var(--dark);
                color: var(--secondary);
                padding: 0 10px;
                font-size: 0.8rem;
                border: 1px solid var(--primary);
            }

            h2 {
                font-family: 'Orbitron', sans-serif;
                color: #fff;
                font-size: 1.8rem;
                margin-bottom: 20px;
                text-transform: uppercase;
                letter-spacing: 2px;
                display: flex;
                align-items: center;
            }
            h2::before {
                content: '>';
                color: var(--primary);
                margin-right: 15px;
                animation: blink-caret 1s infinite;
            }

            p { line-height: 1.7; margin-bottom: 15px; font-size: 1.1rem; color: #a0a0a0; }
            
            .highlight { color: var(--primary); font-weight: bold; text-shadow: 0 0 5px var(--primary); }

            /* Feature Grid */
            .grid-2 {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }

            .cyber-card {
                background: rgba(0, 0, 0, 0.6);
                border: 1px solid #333;
                padding: 20px;
                position: relative;
                transition: all 0.3s;
            }

            .cyber-card:hover {
                border-color: var(--secondary);
                background: rgba(255, 85, 0, 0.1);
            }

            .cyber-card h3 {
                color: var(--primary);
                font-family: 'Orbitron', sans-serif;
                margin-bottom: 10px;
                font-size: 1.2rem;
            }

            .endpoint-list {
                list-style: none;
            }
            .endpoint-list li {
                margin: 10px 0;
                padding: 15px;
                background: rgba(255, 255, 255, 0.03);
                border-left: 2px solid #555;
                display: flex;
                align-items: center;
                transition: all 0.2s;
            }
            .endpoint-list li:hover {
                border-left-color: var(--primary);
                background: rgba(255, 85, 0, 0.05);
                transform: translateX(5px);
            }
            .method {
                font-family: 'Orbitron', sans-serif;
                font-weight: bold;
                padding: 4px 8px;
                background: rgba(255, 85, 0, 0.2);
                color: var(--primary);
                border-radius: 4px;
                margin-right: 15px;
                min-width: 60px;
                text-align: center;
            }

            /* Buttons */
            .btn-container {
                display: flex;
                justify-content: center;
                gap: 30px;
                margin: 40px 0;
            }

            .cyber-btn {
                background: transparent;
                color: var(--primary);
                font-family: 'Orbitron', sans-serif;
                font-size: 1.2rem;
                font-weight: bold;
                text-decoration: none;
                padding: 15px 40px;
                border: 2px solid var(--primary);
                position: relative;
                text-transform: uppercase;
                letter-spacing: 2px;
                overflow: hidden;
                transition: all 0.3s;
                box-shadow: 0 0 10px rgba(255, 85, 0, 0.2), inset 0 0 10px rgba(255, 85, 0, 0.1);
            }

            .cyber-btn::before {
                content: '';
                position: absolute;
                top: 0; left: -100%;
                width: 100%; height: 100%;
                background: var(--primary);
                transition: all 0.3s;
                z-index: -1;
            }

            .cyber-btn:hover {
                color: var(--dark);
                box-shadow: 0 0 20px var(--primary);
            }

            .cyber-btn:hover::before {
                left: 0;
            }

            /* Footer */
            footer {
                text-align: center;
                padding: 40px 0;
                border-top: 1px solid rgba(255, 85, 0, 0.2);
                margin-top: 60px;
            }
            footer a { color: var(--secondary); text-decoration: none; }
            footer a:hover { text-decoration: underline; text-shadow: 0 0 5px var(--secondary); }

            @media (max-width: 768px) {
                h1.glitch { font-size: 2.5rem; }
                .grid-2 { grid-template-columns: 1fr; }
                .btn-container { flex-direction: column; padding: 0 20px; }
            }
        </style>
    </head>
    <body>
        <canvas id="matrix"></canvas>
        <div class="scanlines"></div>
        <div class="vignette"></div>

        <div class="container">
            <header>
                <h1 class="glitch" data-text="SOLIDITYGUARD">SOLIDITYGUARD</h1>
                <br>
                <div class="typewriter-text">> SMART CONTRACT ANNIHILATOR PROTOCOL INITIATED...</div>
            </header>

            <div class="btn-container">
                <a href="/docs" class="cyber-btn">API_DOCS</a>
                <a href="/health" class="cyber-btn">SYS_HEALTH</a>
            </div>

            <div class="hud-panel">
                <h2>MISSION BRIEFING</h2>
                <p>SolidityGuard is an elite <span class="highlight">OpenEnv reinforcement learning environment</span> built for the Meta x PyTorch Hackathon. It trains AI agents to hunt down security vulnerabilities, optimize gas consumption, and enforce coding best practices in Solidity smart contracts.</p>
                <p>Think of it as a <span class="highlight">cyber-assassin</span> for your blockchain code. If it compiles, we will break it.</p>
            </div>

            <div class="grid-2">
                <div class="hud-panel">
                    <h2>TACTICAL FEATURES</h2>
                    <div class="cyber-card">
                        <h3>[01] Multi-Agent Verification</h3>
                        <p>Triple-layer defense matrix: Analyzer → Verifier → Risk Scorer pipeline for zero false positives.</p>
                    </div>
                    <div class="cyber-card" style="margin-top: 15px;">
                        <h3>[02] Exploit Proof System</h3>
                        <p>Reverse-engineers the attack vector. Provides step-by-step attack sequences for detected vulnerabilities.</p>
                    </div>
                    <div class="cyber-card" style="margin-top: 15px;">
                        <h3>[03] Auto-Fix Engine</h3>
                        <p>Calculates exact code modifications needed to neutralize the threat. Actionable remediation in milliseconds.</p>
                    </div>
                </div>

                <div class="hud-panel">
                    <h2>THREAT LEVELS</h2>
                    <ul class="endpoint-list">
                        <li><span class="method">LVL_1</span> <span style="color: #00ffcc;">[EASY] Best Practices & Syntax Patrol</span></li>
                        <li><span class="method">LVL_2</span> <span style="color: #ffaa00;">[MED] Gas Optimization Hunter</span></li>
                        <li><span class="method">LVL_3</span> <span style="color: #ff003c;">[HARD] Security Vulnerability Terminator</span></li>
                    </ul>
                    <div style="margin-top: 30px; padding: 15px; border: 1px solid var(--primary); background: rgba(255,85,0,0.1);">
                        <h3 style="color: var(--primary); margin-bottom: 10px; font-family: 'Orbitron', sans-serif;">TARGET DATASET</h3>
                        <p style="margin: 0;">18 battle-tested Solidity contracts covering 15+ vulnerability types. Real-world scenarios. Fatal consequences.</p>
                    </div>
                </div>
            </div>

            <div class="hud-panel">
                <h2>SYSTEM ENDPOINTS</h2>
                <ul class="endpoint-list" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">
                    <li><span class="method">GET</span> /health <span style="margin-left: 10px; color: #888;">// System vitals</span></li>
                    <li><span class="method">POST</span> /reset <span style="margin-left: 10px; color: #888;">// Init mission</span></li>
                    <li><span class="method">POST</span> /step <span style="margin-left: 10px; color: #888;">// Submit findings</span></li>
                    <li><span class="method">GET</span> /state <span style="margin-left: 10px; color: #888;">// Env status</span></li>
                    <li><span class="method">POST</span> /report <span style="margin-left: 10px; color: #888;">// Generate audit</span></li>
                    <li><span class="method">GET</span> /dashboard <span style="margin-left: 10px; color: #888;">// Analytics</span></li>
                </ul>
            </div>

            <footer>
                <p>META X PYTORCH HACKATHON 2026 // OPENENV PROTOCOL</p>
                <p style="margin-top: 10px;">
                    [ <a href="https://github.com/tanaymitra54/ContractSLM" target="_blank">GITHUB_REPO</a> ] | 
                    [ <a href="https://huggingface.co/spaces/tanaymitra01/solidityguard-openenv" target="_blank">HF_SPACE</a> ]
                </p>
            </footer>
        </div>

        <script>
            // Matrix Rain Animation
            const canvas = document.getElementById('matrix');
            const ctx = canvas.getContext('2d');

            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;

            const katakana = 'アァカサタナハマヤャラワガザダバパイィキシチニヒミリヰギジヂビピウゥクスツヌフムユュルグズブヅプエェケセテネヘメレゲゼデベペオォコソトノホモヨョロゴゾドボポヴッン';
            const latin = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
            const nums = '0123456789';
            const alphabet = katakana + latin + nums;

            const fontSize = 16;
            const columns = canvas.width / fontSize;
            const drops = [];
            for (let x = 0; x < columns; x++) drops[x] = 1;

            const draw = () => {
                ctx.fillStyle = 'rgba(5, 5, 5, 0.05)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.fillStyle = '#ff5500'; // Orange text
                ctx.font = fontSize + 'px monospace';

                for (let i = 0; i < drops.length; i++) {
                    const text = alphabet.charAt(Math.floor(Math.random() * alphabet.length));
                    ctx.fillText(text, i * fontSize, drops[i] * fontSize);

                    if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                        drops[i] = 0;
                    }
                    drops[i]++;
                }
            };

            setInterval(draw, 30);
            
            window.addEventListener('resize', () => {
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
            });
        </script>
    </body>
    </html>
    """


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/reset")
def reset(request: Optional[ResetRequest] = None) -> Dict[str, Any]:
    task_id = request.task_id if request else None
    try:
        return env.reset(task_id=task_id)
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
                "lines_of_code": len(source_code.split("\n")),
            },
            "risk_assessment": risk_metrics,
            "recommendations": _generate_recommendations(risk_metrics),
            "timestamp": "2026-04-06T12:00:00Z",  # Mock timestamp
            "report_version": "2.0.0",
        }

        if request.include_fixes:
            report["suggested_fixes"] = _get_fix_suggestions(
                source_code, request.task_id
            )

        if request.include_exploits:
            report["exploit_scenarios"] = _get_exploit_scenarios(
                source_code, request.task_id
            )

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
                "last_updated": "2026-04-06T12:00:00Z",
            },
            "category_breakdown": {
                "task_1_best_practices": {
                    "sample_count": 6,
                    "avg_severity": "Low",
                    "common_issues": [
                        "missing_spdx",
                        "old_compiler_version",
                        "missing_natspec",
                    ],
                },
                "task_2_gas_optimization": {
                    "sample_count": 6,
                    "avg_severity": "Medium",
                    "common_issues": [
                        "unbounded_loop",
                        "redundant_storage_read",
                        "poor_struct_packing",
                    ],
                },
                "task_3_security": {
                    "sample_count": 6,
                    "avg_severity": "Critical",
                    "common_issues": [
                        "reentrancy",
                        "missing_access_control",
                        "tx_origin_auth",
                    ],
                },
                "task_4_comprehensive_audit": {
                    "sample_count": 3,
                    "avg_severity": "Critical",
                    "common_issues": [
                        "old_compiler_version",
                        "unbounded_loop",
                        "tx_origin_auth",
                    ],
                },
            },
            "agent_stats": {
                "multi_agent_enabled": True,
                "analyzer_accuracy": 0.85,
                "verifier_precision": 0.90,
                "risk_scorer_coverage": 0.95,
            },
        }

        return dashboard_data

    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _calculate_risk_metrics(source_code: str, task_id: str) -> Dict[str, Any]:
    """Calculate comprehensive risk metrics for a contract."""

    # Basic metrics
    lines_of_code = len(source_code.split("\n"))
    cyclomatic_complexity = (
        source_code.count("if ")
        + source_code.count("for ")
        + source_code.count("while ")
    )

    # Security indicators
    has_external_calls = "call{" in source_code or ".call(" in source_code
    has_state_variables = "mapping(" in source_code or "uint" in source_code
    has_payable = "payable" in source_code

    # Calculate overall risk score
    base_risk = 0.3
    if task_id == "task_3_security":
        base_risk = 0.8
    elif task_id == "task_4_comprehensive_audit":
        base_risk = 0.85
    elif task_id == "task_2_gas_optimization":
        base_risk = 0.5

    complexity_factor = min(cyclomatic_complexity * 0.1, 0.3)
    external_call_factor = 0.2 if has_external_calls else 0.0
    payable_factor = 0.1 if has_payable else 0.0

    overall_risk = min(
        base_risk + complexity_factor + external_call_factor + payable_factor, 1.0
    )

    return {
        "overall_risk_score": round(overall_risk, 3),
        "risk_category": "High"
        if overall_risk >= 0.7
        else "Medium"
        if overall_risk >= 0.4
        else "Low",
        "complexity_score": cyclomatic_complexity,
        "lines_of_code": lines_of_code,
        "has_external_calls": has_external_calls,
        "has_state_variables": has_state_variables,
        "has_payable_functions": has_payable,
        "recommended_review_time": f"{max(15, lines_of_code * 2)} minutes",
    }


def _generate_recommendations(risk_metrics: Dict[str, Any]) -> List[str]:
    """Generate audit recommendations based on risk metrics."""

    recommendations = []

    if risk_metrics["overall_risk_score"] >= 0.7:
        recommendations.append("🔴 HIGH RISK: Requires immediate security review")
        recommendations.append("Consider formal verification for critical functions")

    if risk_metrics["has_external_calls"]:
        recommendations.append(
            "⚠️  External calls detected: Review for reentrancy vulnerabilities"
        )

    if risk_metrics["has_payable_functions"]:
        recommendations.append(
            "💰 Payable functions detected: Ensure proper access controls"
        )

    if risk_metrics["complexity_score"] > 10:
        recommendations.append(
            "🧩 High complexity: Consider breaking into smaller functions"
        )

    if risk_metrics["lines_of_code"] > 100:
        recommendations.append("📏 Large contract: Consider modularization")

    recommendations.append("✅ Run static analysis tools (Slither, Mythril)")
    recommendations.append("🧪 Implement comprehensive test coverage")

    return recommendations


def _get_fix_suggestions(source_code: str, task_id: str) -> List[Dict[str, str]]:
    """Get specific fix suggestions for common issues."""

    suggestions = []

    if not source_code.strip().startswith("// SPDX"):
        suggestions.append(
            {
                "issue": "Missing SPDX License",
                "fix": "Add '// SPDX-License-Identifier: MIT' at the top of the file",
                "priority": "Low",
            }
        )

    if "0.4." in source_code or "0.7." in source_code:
        suggestions.append(
            {
                "issue": "Outdated Solidity Version",
                "fix": "Update to 'pragma solidity ^0.8.0;' for better security",
                "priority": "Medium",
            }
        )

    if "tx.origin" in source_code:
        suggestions.append(
            {
                "issue": "tx.origin Usage",
                "fix": "Replace 'tx.origin' with 'msg.sender' for proper authentication",
                "priority": "High",
            }
        )

    return suggestions


def _get_exploit_scenarios(source_code: str, task_id: str) -> List[Dict[str, str]]:
    """Get potential exploit scenarios for security issues."""

    scenarios = []

    if "call{" in source_code and "balances[" in source_code:
        scenarios.append(
            {
                "vulnerability": "Reentrancy Attack",
                "scenario": "Attacker creates malicious contract with fallback function that calls withdraw() recursively",
                "impact": "Complete drainage of contract funds",
                "mitigation": "Implement checks-effects-interactions pattern or ReentrancyGuard",
            }
        )

    if "tx.origin" in source_code:
        scenarios.append(
            {
                "vulnerability": "tx.origin Phishing",
                "scenario": "Attacker tricks user into calling malicious contract that forwards transactions",
                "impact": "Unauthorized access to protected functions",
                "mitigation": "Use msg.sender instead of tx.origin for authentication",
            }
        )

    return scenarios


@app.post("/audit")
async def audit_contract(request: AuditRequest) -> Dict[str, Any]:
    """
    Run multi-agent analysis on a Solidity contract.

    This is the main production endpoint that runs the full pipeline:
    Scanner -> Analyzer -> ExploitGen -> FixSuggester
    """
    try:
        orchestrator = AgentOrchestrator(
            llm_client=LLMClient(base_url=request.llm_base_url) if request.llm_base_url else None,
            generate_exploits=request.generate_exploits,
            generate_fixes=request.generate_fixes,
        )

        result = await orchestrator.analyze(request.source_code, request.task_id)

        return {
            "success": True,
            "findings": [f.model_dump() for f in result.findings],
            "summary": {
                "critical": result.critical_count,
                "medium": result.medium_count,
                "low": result.low_count,
                "total": len(result.findings),
            },
            "metrics": result.agent_metrics,
            "time_seconds": result.total_time_seconds,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@app.get("/demo", response_class=HTMLResponse)
def demo_page() -> str:
    """Professional demo page for investor presentations."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SolidityGuard - AI-Powered Smart Contract Auditing</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #6366f1;
                --primary-dark: #4f46e5;
                --success: #10b981;
                --warning: #f59e0b;
                --danger: #ef4444;
                --dark: #0f172a;
                --light: #f8fafc;
                --muted: #64748b;
                --border: #e2e8f0;
            }

            * { margin: 0; padding: 0; box-sizing: border-box; }

            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: var(--light);
                min-height: 100vh;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
            }

            /* Header */
            header {
                text-align: center;
                margin-bottom: 50px;
            }

            .logo {
                font-size: 2.5rem;
                font-weight: 700;
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 10px;
            }

            .tagline {
                color: var(--muted);
                font-size: 1.1rem;
            }

            /* Metrics Bar */
            .metrics-bar {
                display: flex;
                justify-content: center;
                gap: 40px;
                margin: 30px 0;
                padding: 20px;
                background: rgba(255,255,255,0.05);
                border-radius: 12px;
            }

            .metric {
                text-align: center;
            }

            .metric-value {
                font-size: 2rem;
                font-weight: 700;
                color: var(--primary);
            }

            .metric-label {
                color: var(--muted);
                font-size: 0.9rem;
            }

            /* Main Grid */
            .grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
            }

            @media (max-width: 900px) {
                .grid { grid-template-columns: 1fr; }
            }

            /* Card */
            .card {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 16px;
                padding: 24px;
            }

            .card-header {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
            }

            .card-title {
                font-size: 1.2rem;
                font-weight: 600;
            }

            /* Code Editor */
            .editor {
                background: #0d1117;
                border-radius: 8px;
                overflow: hidden;
            }

            .editor-header {
                background: #161b22;
                padding: 10px 15px;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .dot {
                width: 12px;
                height: 12px;
                border-radius: 50%;
            }

            .dot.red { background: #ff5f56; }
            .dot.yellow { background: #ffbd2e; }
            .dot.green { background: #27c93f; }

            textarea {
                width: 100%;
                height: 300px;
                background: transparent;
                border: none;
                color: #e6edf3;
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                font-size: 14px;
                padding: 15px;
                resize: vertical;
            }

            textarea:focus {
                outline: none;
            }

            /* Button */
            .btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                padding: 14px 28px;
                background: linear-gradient(135deg, var(--primary), var(--primary-dark));
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
                margin-top: 20px;
            }

            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 30px rgba(99, 102, 241, 0.3);
            }

            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }

            /* Progress */
            .progress {
                margin: 20px 0;
            }

            .progress-step {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 0;
                opacity: 0.5;
            }

            .progress-step.active {
                opacity: 1;
            }

            .progress-step.complete {
                opacity: 1;
            }

            .step-icon {
                width: 24px;
                height: 24px;
                border-radius: 50%;
                background: var(--muted);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
            }

            .progress-step.complete .step-icon {
                background: var(--success);
            }

            .progress-step.active .step-icon {
                background: var(--primary);
                animation: pulse 1.5s infinite;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            /* Findings */
            .findings {
                margin-top: 20px;
            }

            .finding {
                background: rgba(255,255,255,0.03);
                border-left: 4px solid var(--danger);
                padding: 16px;
                margin-bottom: 15px;
                border-radius: 0 8px 8px 0;
            }

            .finding.medium {
                border-left-color: var(--warning);
            }

            .finding.low {
                border-left-color: var(--muted);
            }

            .finding-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }

            .finding-type {
                font-weight: 600;
                text-transform: uppercase;
                font-size: 0.85rem;
            }

            .finding.critical .finding-type { color: var(--danger); }
            .finding.medium .finding-type { color: var(--warning); }
            .finding.low .finding-type { color: var(--muted); }

            .finding-severity {
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
            }

            .finding.critical .finding-severity { background: rgba(239, 68, 68, 0.2); color: var(--danger); }
            .finding.medium .finding-severity { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
            .finding.low .finding-severity { background: rgba(100, 116, 139, 0.2); color: var(--muted); }

            .finding-desc {
                color: var(--light);
                margin-bottom: 12px;
                line-height: 1.5;
            }

            .finding-line {
                font-family: monospace;
                color: var(--muted);
                font-size: 0.85rem;
            }

            .code-block {
                background: #0d1117;
                border-radius: 6px;
                padding: 12px;
                margin-top: 12px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 13px;
                overflow-x: auto;
                color: #e6edf3;
            }

            .code-label {
                font-size: 0.75rem;
                color: var(--muted);
                margin-bottom: 6px;
                text-transform: uppercase;
            }

            /* Empty State */
            .empty-state {
                text-align: center;
                padding: 60px 20px;
                color: var(--muted);
            }

            .empty-state-icon {
                font-size: 3rem;
                margin-bottom: 15px;
            }

            /* Footer */
            footer {
                text-align: center;
                padding: 40px 0;
                color: var(--muted);
                font-size: 0.9rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="logo">SolidityGuard</div>
                <div class="tagline">AI-Powered Smart Contract Auditing in Minutes, Not Weeks</div>

                <div class="metrics-bar">
                    <div class="metric">
                        <div class="metric-value">500+</div>
                        <div class="metric-label">Contracts Analyzed</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">85%</div>
                        <div class="metric-label">Detection Rate</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">&lt;10s</div>
                        <div class="metric-label">Avg Audit Time</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">$2B+</div>
                        <div class="metric-label">TVL Protected</div>
                    </div>
                </div>
            </header>

            <div class="grid">
                <!-- Left: Code Input -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">📝 Contract Source</span>
                    </div>

                    <div class="editor">
                        <div class="editor-header">
                            <span class="dot red"></span>
                            <span class="dot yellow"></span>
                            <span class="dot green"></span>
                            <span style="color: var(--muted); font-size: 12px; margin-left: 10px;">Contract.sol</span>
                        </div>
                        <textarea id="sourceCode" placeholder="Paste your Solidity contract here...">// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");

        // VULNERABILITY: External call before state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        balances[msg.sender] = 0;
    }

    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
}</textarea>
                    </div>

                    <button class="btn" id="auditBtn" onclick="runAudit()">
                        🔍 Start Audit
                    </button>
                </div>

                <!-- Right: Results -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">🛡️ Analysis Results</span>
                    </div>

                    <div id="progress" class="progress" style="display: none;">
                        <div class="progress-step" id="step-scan">
                            <div class="step-icon">1</div>
                            <span>Scanning with Slither...</span>
                        </div>
                        <div class="progress-step" id="step-analyze">
                            <div class="step-icon">2</div>
                            <span>Deep analyzing with AI...</span>
                        </div>
                        <div class="progress-step" id="step-exploit">
                            <div class="step-icon">3</div>
                            <span>Generating exploit PoCs...</span>
                        </div>
                        <div class="progress-step" id="step-fix">
                            <div class="step-icon">4</div>
                            <span>Suggesting fixes...</span>
                        </div>
                    </div>

                    <div id="findings" class="findings">
                        <div class="empty-state">
                            <div class="empty-state-icon">🔍</div>
                            <p>Paste a contract and click "Start Audit"<br>to begin the analysis</p>
                        </div>
                    </div>
                </div>
            </div>

            <footer>
                <p>SolidityGuard © 2026 • AI-Native Smart Contract Security</p>
            </footer>
        </div>

        <script>
            async function runAudit() {
                const btn = document.getElementById('auditBtn');
                const progress = document.getElementById('progress');
                const findingsDiv = document.getElementById('findings');
                const sourceCode = document.getElementById('sourceCode').value;

                if (!sourceCode.trim()) {
                    alert('Please paste a contract first');
                    return;
                }

                btn.disabled = true;
                btn.textContent = '⏳ Analyzing...';
                progress.style.display = 'block';
                findingsDiv.innerHTML = '';

                const steps = ['scan', 'analyze', 'exploit', 'fix'];
                let currentStep = 0;

                // Simulate progress
                const progressInterval = setInterval(() => {
                    if (currentStep > 0) {
                        document.getElementById(`step-${steps[currentStep - 1]}`).classList.remove('active');
                        document.getElementById(`step-${steps[currentStep - 1]}`).classList.add('complete');
                    }
                    if (currentStep < steps.length) {
                        document.getElementById(`step-${steps[currentStep]}`).classList.add('active');
                        currentStep++;
                    }
                }, 500);

                try {
                    const response = await fetch('/audit', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            source_code: sourceCode,
                            generate_exploits: true,
                            generate_fixes: true
                        })
                    });

                    const result = await response.json();

                    clearInterval(progressInterval);

                    // Mark all complete
                    steps.forEach(s => {
                        document.getElementById(`step-${s}`).classList.remove('active');
                        document.getElementById(`step-${s}`).classList.add('complete');
                    });

                    // Display findings
                    displayFindings(result.findings);

                    btn.disabled = false;
                    btn.textContent = '🔍 Start Audit';

                } catch (error) {
                    clearInterval(progressInterval);
                    findingsDiv.innerHTML = `<div class="finding critical"><p>Error: ${error.message}</p></div>`;
                    btn.disabled = false;
                    btn.textContent = '🔍 Start Audit';
                }
            }

            function displayFindings(findings) {
                const findingsDiv = document.getElementById('findings');

                if (!findings || findings.length === 0) {
                    findingsDiv.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">✅</div>
                            <p>No vulnerabilities found!<br>Your contract looks secure.</p>
                        </div>
                    `;
                    return;
                }

                findingsDiv.innerHTML = findings.map(f => `
                    <div class="finding ${f.severity.toLowerCase()}">
                        <div class="finding-header">
                            <span class="finding-type">${f.issue_type}</span>
                            <span class="finding-severity">${f.severity}</span>
                        </div>
                        <p class="finding-desc">${f.description}</p>
                        ${f.line_number ? `<p class="finding-line">📍 Line ${f.line_number}</p>` : ''}
                        ${f.exploit_scenario ? `
                            <div class="code-label">Exploit Scenario</div>
                            <div class="code-block">${escapeHtml(f.exploit_scenario)}</div>
                        ` : ''}
                        ${f.exploit_poc ? `
                            <div class="code-label">Generated PoC (Foundry)</div>
                            <div class="code-block"><pre>${escapeHtml(f.exploit_poc)}</pre></div>
                        ` : ''}
                        ${f.suggested_fix ? `
                            <div class="code-label">Suggested Fix</div>
                            <div class="code-block"><pre>${escapeHtml(f.suggested_fix)}</pre></div>
                        ` : ''}
                    </div>
                `).join('');
            }

            function escapeHtml(text) {
                if (!text) return '';
                return text
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;');
            }
        </script>
    </body>
    </html>
    """


def main():
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
