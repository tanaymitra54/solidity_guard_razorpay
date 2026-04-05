from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Issue:
    issue_type: str
    line_number: Optional[int]
    severity: str


def _normalize_issue(issue: Dict[str, Any]) -> Issue:
    return Issue(
        issue_type=str(issue.get("issue_type", "")).strip(),
        line_number=issue.get("line_number"),
        severity=str(issue.get("severity", "")).strip(),
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


def grade_action(action: List[Dict[str, Any]], expected: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
    expected_issues = [_normalize_issue(item) for item in expected]
    predicted_issues = [_normalize_issue(item) for item in action]

    matched = 0
    line_bonus_total = 0.0
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
                found = True
                break
        if not found:
            continue

    expected_count = max(len(expected_issues), 1)
    base_score = matched / expected_count
    false_positives = max(len(predicted_issues) - matched, 0)
    fp_penalty = 0.05 * false_positives

    score = base_score * 0.8 + min(line_bonus_total, 0.2) - fp_penalty
    score = max(min(score, 1.0), 0.0)

    details = {
        "matched": matched,
        "expected": len(expected_issues),
        "false_positives": false_positives,
        "line_bonus": round(min(line_bonus_total, 0.2), 3),
        "score": round(score, 4),
    }
    return score, details
