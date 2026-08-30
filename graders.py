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


class Grader:
    """OpenEnv-compatible grader class for MetaXScalar validator."""

    @staticmethod
    def grade(
        action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        """Grade the action against expected results. Returns (score, details)."""
        return grade_action(action, expected)

    @staticmethod
    def grade_task_1(
        action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        return grade_action(action, expected)

    @staticmethod
    def grade_task_2(
        action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        return grade_action(action, expected)

    @staticmethod
    def grade_task_3(
        action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        return grade_action(action, expected)

    @staticmethod
    def grade_task_4(
        action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        return grade_action(action, expected)


def _normalize_issue(issue: Dict[str, Any]) -> Issue:
    return Issue(
        issue_type=str(issue.get("issue_type", "")).strip(),
        line_number=issue.get("line_number"),
        severity=str(issue.get("severity", "")).strip(),
        exploit_path=issue.get("exploit_path"),
        recommended_fix=issue.get("recommended_fix"),
        confidence=issue.get("confidence"),
    )


# Canonical issue type families: maps canonical name to a set of acceptable variations
_ISSUE_TYPE_FAMILIES: Dict[str, set] = {
    "missing_spdx": {"missing_spdx", "spdx", "license", "licensing", "missing_license"},
    "old_compiler_version": {
        "old_compiler_version", "compiler", "pragma", "version",
        "old_pragma", "outdated_compiler", "outdated_pragma",
    },
    "missing_natspec": {"missing_natspec", "natspec", "documentation", "doc_comment", "missing_docs"},
    "deprecated_constructor": {"deprecated_constructor", "constructor", "deprecated"},
    "missing_events": {"missing_events", "events", "missing_event", "emit"},
    "unused_variables": {"unused_variables", "unused", "dead_code"},
    "unbounded_loop": {"unbounded_loop", "loop", "unbounded", "dynamic_array", "infinite_loop"},
    "redundant_storage_read": {
        "redundant_storage_read", "storage_read", "redundant",
        "cache", "sload", "repeated_storage",
    },
    "custom_error_missing": {"custom_error_missing", "custom_error", "require_string", "error_missing"},
    "poor_struct_packing": {"poor_struct_packing", "struct_packing", "packing", "storage_packing"},
    "unchecked_math_opportunity": {"unchecked_math", "unchecked", "overflow_protection", "safe_math"},
    "expensive_operation_in_loop": {
        "expensive_operation_in_loop", "expensive_op", "expensive",
        "loop_operation", "loop_cost",
    },
    "inefficient_string_concat": {"inefficient_string_concat", "string_concat", "string_op", "concat"},
    "reentrancy": {"reentrancy", "reentrancy_vulnerability", "re-entrancy", "re-entry"},
    "missing_access_control": {
        "missing_access_control", "access_control", "authorization",
        "owner_only", "no_auth", "unauthorized",
    },
    "tx_origin_auth": {"tx_origin_auth", "tx.origin", "tx_origin", "tx origin", "origin_auth"},
    "integer_overflow_risk": {
        "integer_overflow_risk", "overflow", "underflow",
        "integer_overflow", "integer_underflow",
    },
    "unsafe_delegatecall": {"unsafe_delegatecall", "delegatecall", "unsafe_delegate"},
    "weak_randomness": {"weak_randomness", "randomness", "weak_random", "block_hash_random"},
}

# Severity normalization: map any severity string to canonical form
_SEVERITY_CANONICAL: Dict[str, str] = {
    "critical": "Critical",
    "high": "Critical",
    "severe": "Critical",
    "danger": "Critical",
    "major": "Critical",
    "important": "Critical",
    "medium": "Medium",
    "moderate": "Medium",
    "warning": "Medium",
    "medium-high": "Medium",
    "average": "Medium",
    "low": "Low",
    "minor": "Low",
    "informational": "Info",
    "info": "Info",
    "information": "Info",
    "note": "Info",
    "cosmetic": "Low",
    "minor issue": "Low",
}

# Canonical severity values
_CANONICAL_SEVERITIES = {"Critical", "Medium", "Low", "Info"}


def _canonicalize_severity(sev: str) -> str:
    """Map a severity string to its canonical form."""
    return _SEVERITY_CANONICAL.get(sev.lower().strip(), "Medium")


def _canonicalize_issue_type(issue_type: str) -> Optional[str]:
    """Map a freeform issue type to its canonical family name, or None."""
    normalized = issue_type.lower().replace("_", "").replace("-", "").replace(" ", "")
    for canonical, variations in _ISSUE_TYPE_FAMILIES.items():
        for var in variations:
            if var.replace("_", "").replace("-", "").replace(" ", "") == normalized:
                return canonical
        # Substring check for fuzzy matching
        canonical_flat = canonical.replace("_", "")
        if canonical_flat in normalized or normalized in canonical_flat:
            return canonical
    return None


def _match_issue(pred: Issue, expected: Issue) -> bool:
    """Match a predicted issue against an expected issue using canonical forms."""
    # Canonicalize issue types
    pred_canonical = _canonicalize_issue_type(pred.issue_type)
    exp_canonical = _canonicalize_issue_type(expected.issue_type)

    if pred_canonical is None or exp_canonical is None:
        return False

    if pred_canonical != exp_canonical:
        return False

    # Canonicalize severity
    pred_sev = _canonicalize_severity(pred.severity)
    exp_sev = _canonicalize_severity(expected.severity)

    # Allow severity mismatch within a tolerance:
    # Critical can match High, but not Low
    _sev_order = {"Critical": 0, "Medium": 1, "Low": 2, "Info": 3}
    pred_order = _sev_order.get(pred_sev, 1)
    exp_order = _sev_order.get(exp_sev, 1)
    if abs(pred_order - exp_order) > 1:
        return False

    return True


def _line_bonus(pred_line: Optional[int], exp_line: Optional[int]) -> float:
    """Bonus for line number accuracy."""
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
        if pred.severity.lower() == "critical" and pred.confidence >= 0.8:
            return 0.05
        elif pred.severity.lower() in ("medium", "low") and pred.confidence >= 0.6:
            return 0.05
    return 0.0


def grade_action(
    action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
) -> Tuple[float, Dict[str, Any]]:
    """Grade a list of predicted findings against expected findings.

    Returns (score, details) where score is always in [0.0, 1.0].
    """
    expected_issues = [_normalize_issue(item) for item in expected]
    predicted_issues = [_normalize_issue(item) for item in action]

    matched = 0
    line_bonus_total = 0.0
    exploit_bonus_total = 0.0
    fix_bonus_total = 0.0
    confidence_bonus_total = 0.0
    expected_used = [False] * len(expected_issues)

    for pred in predicted_issues:
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
                break

    expected_count = max(len(expected_issues), 1)
    base_score = matched / expected_count
    false_positives = max(len(predicted_issues) - matched, 0)
    fp_penalty = 0.05 * false_positives

    # Calculate total bonuses (capped)
    total_line_bonus = min(line_bonus_total, 0.2)
    total_exploit_bonus = min(exploit_bonus_total, 0.15)
    total_fix_bonus = min(fix_bonus_total, 0.15)
    total_confidence_bonus = min(confidence_bonus_total, 0.1)

    score = (
        base_score * 0.6
        + total_line_bonus
        + total_exploit_bonus
        + total_fix_bonus
        + total_confidence_bonus
        - fp_penalty
    )

    # ALWAYS clamp to [0.0, 1.0] — critical for RL reward signals
    score = max(0.0, min(1.0, round(score, 4)))

    details = {
        "matched": matched,
        "expected": len(expected_issues),
        "false_positives": false_positives,
        "line_bonus": round(total_line_bonus, 3),
        "exploit_bonus": round(total_exploit_bonus, 3),
        "fix_bonus": round(total_fix_bonus, 3),
        "confidence_bonus": round(total_confidence_bonus, 3),
        "score": score,
    }
    return score, details


def grade(
    action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
) -> Tuple[float, Dict[str, Any]]:
    """Compatibility alias for validators expecting graders:grade."""
    return grade_action(action, expected)


def grade_task_1(
    action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
) -> Tuple[float, Dict[str, Any]]:
    return grade_action(action, expected)


def grade_task_2(
    action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
) -> Tuple[float, Dict[str, Any]]:
    return grade_action(action, expected)


def grade_task_3(
    action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
) -> Tuple[float, Dict[str, Any]]:
    return grade_action(action, expected)


def grade_task_4(
    action: List[Dict[str, Any]], expected: List[Dict[str, Any]]
) -> Tuple[float, Dict[str, Any]]:
    return grade_action(action, expected)
