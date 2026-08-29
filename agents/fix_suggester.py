"""
Fix Suggester Agent - Generate verified patches for vulnerabilities.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.base import BaseAgent, Finding, LLMClient


FIX_PROMPT = """You are a smart contract security expert specializing in fixing vulnerabilities while preserving functionality.

Given this vulnerable contract:
```solidity
{source_code}
```

And this vulnerability:
- Type: {issue_type}
- Line: {line_number}
- Description: {description}

Generate a minimal, targeted fix that:
1. **Blocks the exploit** - Directly addresses the vulnerability
2. **Preserves functionality** - Doesn't break existing behavior
3. **Follows best practices** - Checks-effects-interactions, CEI pattern, etc.
4. **Is minimal** - Only change what's necessary

Output the fix in this format:
{{
  "fix_description": "Brief description of the fix",
  "affected_lines": [14, 15, 16],
  "original_code": "lines to be replaced",
  "fixed_code": "replacement code",
  "explanation": "Why this fix works and what attack it prevents"
}}

If multiple changes are needed, include them all. Output only valid JSON."""


class FixSuggester(BaseAgent):
    """
    Generate verified patches for vulnerabilities.

    This agent analyzes a vulnerability and produces minimal,
    targeted fixes that block exploits while preserving functionality.
    """

    name = "fix_suggester"
    description = "Generate verified patches for vulnerabilities"

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(llm_client)

    async def process(
        self, source_code: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """
        Process is not the main entry point for this agent.
        Use suggest_fix() instead.
        """
        return []

    async def suggest_fix(
        self,
        source_code: str,
        finding: Finding,
        exploit_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a fix for the vulnerability."""
        prompt = FIX_PROMPT.format(
            source_code=source_code,
            issue_type=finding.issue_type,
            line_number=finding.line_number or "unknown",
            description=finding.description,
        )

        # If we have exploit code, add it for context
        if exploit_code:
            prompt += f"\n\nExploit code to block:\n```solidity\n{exploit_code}\n```"

        try:
            response = await self.llm.generate_json(prompt)
            return response

        except Exception as e:
            print(f"[FixSuggester] Error: {e}")
            return {
                "fix_description": f"Failed to generate fix: {e}",
                "affected_lines": [],
                "original_code": "",
                "fixed_code": "",
                "explanation": "",
            }

    def apply_fix(
        self,
        source_code: str,
        fix: Dict[str, Any],
    ) -> str:
        """Apply a fix to the source code and return the modified code."""
        lines = source_code.split("\n")
        affected_lines = fix.get("affected_lines", [])
        fixed_code = fix.get("fixed_code", "")

        if not affected_lines or not fixed_code:
            return source_code

        # Convert to 0-indexed
        start_line = min(affected_lines) - 1
        end_line = max(affected_lines)

        # Replace the affected lines
        new_lines = lines[:start_line] + fixed_code.split("\n") + lines[end_line:]

        return "\n".join(new_lines)


# Pre-built fix suggestions for common vulnerability types
FIX_TEMPLATES = {
    "reentrancy": {
        "fix_description": "Move state update before external call (checks-effects-interactions pattern)",
        "affected_lines": [14, 15, 16],
        "original_code": "        (bool success, ) = msg.sender.call{value: amount}(\"\");\n        require(success);\n        balances[msg.sender] = 0;",
        "fixed_code": "        balances[msg.sender] = 0;  // Update state BEFORE external call\n        (bool success, ) = msg.sender.call{value: amount}(\"\");\n        require(success);",
        "explanation": "By updating the balance before the external call, reentrant calls will see the updated (zero) balance and cannot drain funds repeatedly.",
    },
    "tx_origin_auth": {
        "fix_description": "Replace tx.origin with msg.sender for authorization",
        "affected_lines": [10],
        "original_code": "        require(tx.origin == owner, \"Not authorized\");",
        "fixed_code": "        require(msg.sender == owner, \"Not authorized\");",
        "explanation": "msg.sender is the immediate caller, preventing phishing attacks where a malicious contract forwards calls from a tricked user.",
    },
    "access_control": {
        "fix_description": "Add access control modifier to sensitive function",
        "affected_lines": [8],
        "original_code": "    function sensitiveFunction() public {",
        "fixed_code": "    function sensitiveFunction() public onlyOwner {",
        "explanation": "Adding the onlyOwner modifier ensures only authorized addresses can call this function.",
    },
    "unchecked_return_value": {
        "fix_description": "Check the return value of the external call",
        "affected_lines": [12],
        "original_code": "        (bool success, ) = target.call{value: amount}(\"\");",
        "fixed_code": "        (bool success, ) = target.call{value: amount}(\"\");\n        require(success, \"Call failed\");",
        "explanation": "Checking the return value ensures the call succeeded before proceeding.",
    },
}


def get_fix_template(issue_type: str) -> Optional[Dict[str, Any]]:
    """Get a pre-built fix template for common vulnerability types."""
    return FIX_TEMPLATES.get(issue_type.lower())


def generate_diff(original: str, fixed: str) -> str:
    """Generate a simple diff between original and fixed code."""
    import difflib

    original_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        fixed_lines,
        fromfile="original.sol",
        tofile="fixed.sol",
    )

    return "".join(diff)
