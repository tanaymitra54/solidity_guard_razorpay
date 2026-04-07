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
    pred_type = pred.issue_type.lower()
    exp_type = expected.issue_type.lower()
    
    type_variations = {
        "missing_spdx": ["spdx", "license", "licensing"],
        "old_compiler_version": ["compiler", "pragma", "version"],
        "missing_natspec": ["natspec", "documentation", "doc comment"],
        "deprecated_constructor": ["constructor", "deprecated"],
        "unbounded_loop": ["loop", "unbounded", "dynamic array"],
        "redundant_storage_read": ["storage read", "redundant", "cache", "sload", "repeated storage"],
        "custom_error_missing": ["custom error", "require string"],
        "reentrancy": ["reentrancy", "re-entrancy", "re-entry"],
        "missing_access_control": ["access control", "authorization", "owner only"],
        "tx_origin_auth": ["tx.origin", "tx origin"],
    }
    
    matched_type = True
    if pred_type != exp_type:
        matched_type = False
        if exp_type in type_variations:
            for variation in type_variations[exp_type]:
                if variation in pred_type or pred_type in variation:
                    matched_type = True
                    break
        if not matched_type:
            for key, variations in type_variations.items():
                for v in variations:
                    if v in pred_type and v in exp_type:
                        matched_type = True
                        break
                if matched_type:
                    break
        if not matched_type:
            return False
    
    pred_sev = pred.severity.lower()
    exp_sev = expected.severity.lower()
    
    severity_map = {
        "critical": ["critical", "high", "severe", "danger", "major", "important"],
        "medium": ["medium", "moderate", "warning", "medium-high", "average"],
        "low": ["low", "minor", "informational", "info", "minor issue", "cosmetic"],
        "info": ["info", "information", "low", "informational", "note"],
    }
    
    if pred_sev != exp_sev:
        if exp_sev in severity_map:
            matched_sev = any(s in pred_sev for s in severity_map[exp_sev])
            if not matched_sev:
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