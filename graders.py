from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Issue:
    issue_type: str
    line_number: Optional[int]
    severity: str
    exploit_path: Optional[str] = None
    recommended_fix: Optional[str] = None
    confidence: Optional[float] = None


def _normalize_issue(issue: Dict[str, Any]) -> Issue:
    return Issue(
        issue_type=str(issue.get("issue_type", "")).strip(),
        line_number=issue.get("line_number"),
        severity=str(issue.get("severity", "")).strip(),
        exploit_path=issue.get("exploit_path"),
        recommended_fix=issue.get("recommended_fix"),
        confidence=issue.get("confidence"),
    )


def _match_issue(pred: Issue, expected: Issue) -> bool:
    if pred.issue_type.lower() != expected.issue_type.lower():
        return False
    if pred.severity.lower() != expected.severity.lower():
        return False
    return True


def _line_bonus(pred_line: Optional[int], exp_line: Optional[int]) -> float:
    if pred_line is None or exp_line is None:
        return 0.0
    diff = abs(pred_line - exp_line)
    if diff == 0:
        return 0.2
    if diff <= 2:
        return 0.1
    return 0.0


def _exploit_bonus(pred: Issue, exp: Issue) -> float:
    """Bonus for providing exploit explanation."""
    if pred.exploit_path and len(pred.exploit_path.strip()) >= 50:
        return 0.1
    return 0.0


def _fix_bonus(pred: Issue, exp: Issue) -> float:
    """Bonus for providing fix recommendation.""" 
    if pred.recommended_fix and len(pred.recommended_fix.strip()) >= 20:
        return 0.1
    return 0.0


def _confidence_bonus(pred: Issue, exp: Issue) -> float:
    """Bonus for appropriate confidence level."""
    if pred.confidence is not None and 0.0 <= pred.confidence <= 1.0:
        # Higher confidence for critical issues
        if pred.severity.lower() == "critical" and pred.confidence >= 0.8:
            return 0.05
        elif pred.severity.lower() in ["medium", "low"] and pred.confidence >= 0.6:
            return 0.05
    return 0.0


def grade_action(action: List[Dict[str, Any]], expected: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
    expected_issues = [_normalize_issue(item) for item in expected]
    predicted_issues = [_normalize_issue(item) for item in action]

    matched = 0
    line_bonus_total = 0.0
    exploit_bonus_total = 0.0
    fix_bonus_total = 0.0
    confidence_bonus_total = 0.0
    expected_used = [False] * len(expected_issues)

    for pred in predicted_issues:
        found = False
        for idx, exp in enumerate(expected_issues):
            if expected_used[idx]:
                continue
            if _match_issue(pred, exp):
                expected_used[idx] = True
                matched += 1
                line_bonus_total += _line_bonus(pred.line_number, exp.line_number)
                exploit_bonus_total += _exploit_bonus(pred, exp)
                fix_bonus_total += _fix_bonus(pred, exp)
                confidence_bonus_total += _confidence_bonus(pred, exp)
                found = True
                break
        if not found:
            continue

    expected_count = max(len(expected_issues), 1)
    base_score = matched / expected_count
    false_positives = max(len(predicted_issues) - matched, 0)
    fp_penalty = 0.05 * false_positives

    # Calculate total bonuses (capped)
    total_line_bonus = min(line_bonus_total, 0.2)
    total_exploit_bonus = min(exploit_bonus_total, 0.15)
    total_fix_bonus = min(fix_bonus_total, 0.15)
    total_confidence_bonus = min(confidence_bonus_total, 0.1)

    score = base_score * 0.6 + total_line_bonus + total_exploit_bonus + total_fix_bonus + total_confidence_bonus - fp_penalty
    score = max(min(score, 1.0), 0.0)

    details = {
        "matched": matched,
        "expected": len(expected_issues),
        "false_positives": false_positives,
        "line_bonus": round(total_line_bonus, 3),
        "exploit_bonus": round(total_exploit_bonus, 3),
        "fix_bonus": round(total_fix_bonus, 3),
        "confidence_bonus": round(total_confidence_bonus, 3),
        "score": round(score, 4),
    }
    return score, details
