#!/usr/bin/env python3
"""
Pre-Submission Validation Script
Meta x PyTorch Hackathon - Round 1

Validates all mandatory requirements before submission.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text: str) -> None:
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f"{BLUE}{text}{RESET}")
    print("=" * 70)


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{GREEN}✓ PASS{RESET} - {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{RED}✗ FAIL{RESET} - {text}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{YELLOW}⚠ WARN{RESET} - {text}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"  {text}")


class ValidationResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, message: str):
        self.passed.append(message)
        print_success(message)

    def add_fail(self, message: str):
        self.failed.append(message)
        print_error(message)

    def add_warning(self, message: str):
        self.warnings.append(message)
        print_warning(message)

    def is_passing(self) -> bool:
        return len(self.failed) == 0


def validate_hf_space_config(result: ValidationResult) -> None:
    """Check 1: HF Space Configuration."""
    print_header("CHECK 1: HF SPACE DEPLOYMENT CONFIGURATION")

    # Check README.md exists
    if not os.path.exists("README.md"):
        result.add_fail("README.md not found")
        return

    # Read README and check for HF frontmatter
    with open("README.md", "r") as f:
        content = f.read()

    if not content.startswith("---"):
        result.add_fail("README.md missing HF Spaces YAML frontmatter")
        return

    # Extract frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        result.add_fail("README.md has invalid YAML frontmatter")
        return

    frontmatter = parts[1]

    # Check required fields
    required_fields = ["title:", "sdk:", "docker"]
    for field in required_fields:
        if field in frontmatter.lower():
            result.add_pass(f"README.md has '{field}' configured")
        else:
            result.add_fail(f"README.md missing '{field}' in frontmatter")

    # Check Dockerfile exists
    if os.path.exists("Dockerfile"):
        result.add_pass("Dockerfile present")

        # Check Dockerfile content
        with open("Dockerfile", "r") as f:
            dockerfile = f.read()

        if "7860" in dockerfile:
            result.add_pass("Dockerfile exposes port 7860 (HF standard)")
        else:
            result.add_warning("Dockerfile should expose port 7860 for HF Spaces")

        if "uvicorn" in dockerfile.lower() or "CMD" in dockerfile:
            result.add_pass("Dockerfile has proper CMD configuration")
        else:
            result.add_fail("Dockerfile missing CMD to start server")
    else:
        result.add_fail("Dockerfile not found")


def validate_openenv_spec(result: ValidationResult) -> None:
    """Check 2: OpenEnv Spec Compliance."""
    print_header("CHECK 2: OPENENV SPEC COMPLIANCE")

    # Check openenv.yaml exists
    if not os.path.exists("openenv.yaml"):
        result.add_fail("openenv.yaml not found")
        return

    result.add_pass("openenv.yaml exists")

    # Parse openenv.yaml
    import yaml

    try:
        with open("openenv.yaml", "r") as f:
            spec = yaml.safe_load(f)
        result.add_pass("openenv.yaml is valid YAML")
    except Exception as e:
        result.add_fail(f"openenv.yaml parse error: {e}")
        return

    # Check required fields
    required_fields = [
        "name",
        "version",
        "description",
        "entrypoint",
        "tasks",
        "schemas",
    ]
    for field in required_fields:
        if field in spec:
            result.add_pass(f"openenv.yaml has '{field}'")
        else:
            result.add_fail(f"openenv.yaml missing '{field}'")

    # Check tasks
    if "tasks" in spec and isinstance(spec["tasks"], list):
        task_count = len(spec["tasks"])
        if task_count >= 3:
            result.add_pass(f"Has {task_count} tasks (minimum 3 required)")
        else:
            result.add_fail(f"Only {task_count} tasks (minimum 3 required)")

        # Check task difficulties
        difficulties = [t.get("difficulty") for t in spec["tasks"]]
        print_info(f"Task difficulties: {difficulties}")

        # Check graders for each task
        tasks_with_graders = 0
        for task in spec["tasks"]:
            if task.get("grader"):
                tasks_with_graders += 1
        if tasks_with_graders >= 3:
            result.add_pass(
                f"{tasks_with_graders} tasks have graders (minimum 3 required)"
            )
        else:
            result.add_fail(
                f"Only {tasks_with_graders} tasks have graders (minimum 3 required)"
            )

    # Check schemas
    if "schemas" in spec:
        required_schemas = ["observation", "action", "state"]
        for schema in required_schemas:
            if schema in spec["schemas"]:
                result.add_pass(f"Schema '{schema}' defined")
            else:
                result.add_fail(f"Schema '{schema}' missing")

    # Check environment.py exists and has required methods
    if os.path.exists("environment.py"):
        result.add_pass("environment.py exists")

        with open("environment.py", "r") as f:
            env_code = f.read()

        required_methods = ["reset", "step", "state"]
        for method in required_methods:
            if f"def {method}" in env_code:
                result.add_pass(f"environment.py has {method}() method")
            else:
                result.add_fail(f"environment.py missing {method}() method")
    else:
        result.add_fail("environment.py not found")


def validate_dockerfile_builds(result: ValidationResult) -> None:
    """Check 3: Dockerfile Builds."""
    print_header("CHECK 3: DOCKERFILE BUILD CHECK")

    if not os.path.exists("Dockerfile"):
        result.add_fail("Dockerfile not found")
        return

    result.add_pass("Dockerfile exists")

    # Check requirements.txt
    if os.path.exists("requirements.txt"):
        result.add_pass("requirements.txt exists")

        with open("requirements.txt", "r") as f:
            reqs = f.read()

        required_deps = ["fastapi", "uvicorn", "openai", "pydantic"]
        for dep in required_deps:
            if dep in reqs.lower():
                result.add_pass(f"requirements.txt has '{dep}'")
            else:
                result.add_fail(f"requirements.txt missing '{dep}'")
    else:
        result.add_fail("requirements.txt not found")

    print_info("Note: Actual Docker build test requires Docker daemon")
    result.add_warning("Docker build not tested (requires Docker installed)")


def validate_inference_script(result: ValidationResult) -> None:
    """Check 4: Baseline Inference Script."""
    print_header("CHECK 4: INFERENCE SCRIPT VALIDATION")

    # Check inference.py exists in root
    if not os.path.exists("inference.py"):
        result.add_fail("inference.py not found in root directory")
        return

    result.add_pass("inference.py exists in root directory")

    # Read inference.py
    with open("inference.py", "r") as f:
        inference_code = f.read()

    # Check for required imports
    if (
        "from openai import OpenAI" in inference_code
        or "import openai" in inference_code
    ):
        result.add_pass("inference.py uses OpenAI client")
    else:
        result.add_fail("inference.py must use OpenAI client for LLM calls")

    # Check for environment variables
    env_vars = ["API_BASE_URL", "MODEL_NAME", "HF_TOKEN"]
    for var in env_vars:
        if var in inference_code:
            result.add_pass(f"inference.py loads {var} environment variable")
        else:
            result.add_fail(f"inference.py missing {var} environment variable")

    # Check for logging format
    has_start = '"START"' in inference_code or "'START'" in inference_code
    has_step = '"STEP"' in inference_code or "'STEP'" in inference_code
    has_end = '"END"' in inference_code or "'END'" in inference_code

    if has_start and has_step and has_end:
        result.add_pass("inference.py has [START], [STEP], [END] logging")
    else:
        missing = []
        if not has_start:
            missing.append("START")
        if not has_step:
            missing.append("STEP")
        if not has_end:
            missing.append("END")
        result.add_fail(f"inference.py missing logging tags: {missing}")

    # Check for proper logging function
    if "_log(" in inference_code or 'print(f"[' in inference_code:
        result.add_pass("inference.py has logging function")
    else:
        result.add_warning("inference.py logging implementation unclear")

    # Try to run inference.py (will fail on missing env vars, but checks syntax)
    print_info("Testing inference.py syntax...")
    import subprocess

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "py_compile", "inference.py"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            result.add_pass("inference.py has valid Python syntax")
        else:
            result.add_fail(f"inference.py syntax error: {proc.stderr}")
    except Exception as e:
        result.add_warning(f"Could not validate syntax: {e}")


def validate_tasks_and_graders(result: ValidationResult) -> None:
    """Check 5: Tasks and Grading System."""
    print_header("CHECK 5: TASKS AND GRADING SYSTEM")

    # Check graders.py exists
    if not os.path.exists("graders.py"):
        result.add_fail("graders.py not found")
        return

    result.add_pass("graders.py exists")

    # Import and test graders
    try:
        from graders import grade_action

        result.add_pass("graders.py imports successfully")

        # Test grading with empty action
        score, details = grade_action([], [])
        if 0.0 <= score <= 1.0:
            result.add_pass(f"Grading returns score in 0.0-1.0 range: {score}")
        else:
            result.add_fail(f"Grading score out of range: {score}")

        # Test with sample data
        sample_action = [
            {
                "issue_type": "test",
                "line_number": 1,
                "description": "test",
                "severity": "Low",
            }
        ]
        sample_expected = [
            {
                "issue_type": "test",
                "line_number": 1,
                "description": "test",
                "severity": "Low",
            }
        ]
        score, details = grade_action(sample_action, sample_expected)

        if 0.0 <= score <= 1.0:
            result.add_pass(f"Grading with perfect match: {score}")
        else:
            result.add_fail(f"Grading score invalid: {score}")

    except Exception as e:
        result.add_fail(f"Grading system error: {e}")

    # Check environment and tasks
    try:
        from environment import SolidityGuardEnv

        result.add_pass("Environment imports successfully")

        env = SolidityGuardEnv()

        # Test each task
        tasks = ["task_1_best_practices", "task_2_gas_optimization", "task_3_security"]
        for task_id in tasks:
            try:
                obs = env.reset(task_id=task_id)
                result.add_pass(f"Task '{task_id}' resets successfully")

                # Test step
                step_result = env.step([])
                reward = step_result.get("reward", -1)

                if 0.0 <= reward <= 1.0:
                    result.add_pass(f"Task '{task_id}' reward in valid range: {reward}")
                else:
                    result.add_fail(f"Task '{task_id}' reward out of range: {reward}")

            except Exception as e:
                result.add_fail(f"Task '{task_id}' error: {e}")

    except Exception as e:
        result.add_fail(f"Environment error: {e}")


def validate_api_endpoints(result: ValidationResult) -> None:
    """Check 6: API Endpoints."""
    print_header("CHECK 6: API ENDPOINTS")

    if not os.path.exists("app.py"):
        result.add_fail("app.py not found")
        return

    result.add_pass("app.py exists")

    # Import app
    try:
        from app import app

        result.add_pass("FastAPI app imports successfully")

        # Check routes
        routes = {route.path: route for route in app.routes if hasattr(route, "path")}

        required_endpoints = ["/health", "/reset", "/step", "/state"]
        for endpoint in required_endpoints:
            if endpoint in routes:
                result.add_pass(f"Endpoint '{endpoint}' exists")
            else:
                result.add_fail(f"Endpoint '{endpoint}' missing")

    except Exception as e:
        result.add_fail(f"FastAPI app error: {e}")


def validate_dataset(result: ValidationResult) -> None:
    """Check 7: Dataset and Manifest."""
    print_header("CHECK 7: DATASET VALIDATION")

    # Check manifest.json
    manifest_path = "data/manifest.json"
    if not os.path.exists(manifest_path):
        result.add_fail("data/manifest.json not found")
        return

    result.add_pass("data/manifest.json exists")

    # Parse manifest
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        if not isinstance(manifest, list):
            result.add_fail("manifest.json must be a list")
            return

        result.add_pass(f"manifest.json has {len(manifest)} samples")

        if len(manifest) >= 12:
            result.add_pass(
                f"Dataset has {len(manifest)} samples (minimum 12 recommended)"
            )
        else:
            result.add_warning(
                f"Dataset has only {len(manifest)} samples (12-20 recommended)"
            )

        # Check sample structure
        for i, sample in enumerate(manifest[:3]):  # Check first 3
            required_fields = ["task_id", "source_path", "labels"]
            missing = [f for f in required_fields if f not in sample]
            if not missing:
                result.add_pass(f"Sample {i + 1} has required fields")
            else:
                result.add_fail(f"Sample {i + 1} missing fields: {missing}")

            # Check source file exists
            if "source_path" in sample:
                if os.path.exists(sample["source_path"]):
                    result.add_pass(f"Sample {i + 1} source file exists")
                else:
                    result.add_fail(
                        f"Sample {i + 1} source file missing: {sample['source_path']}"
                    )

    except Exception as e:
        result.add_fail(f"manifest.json error: {e}")


def validate_runtime_requirements(result: ValidationResult) -> None:
    """Check 8: Runtime Requirements."""
    print_header("CHECK 8: RUNTIME REQUIREMENTS")

    print_info("Runtime constraints:")
    print_info("  - Max runtime: 20 minutes")
    print_info("  - CPU: 2 vCPU")
    print_info("  - Memory: 8 GB")

    result.add_pass("Runtime requirements documented")
    result.add_warning(
        "Actual runtime test requires LLM credentials and full execution"
    )


def generate_report(result: ValidationResult) -> None:
    """Generate final report."""
    print_header("VALIDATION SUMMARY")

    print(f"\n{GREEN}Passed: {len(result.passed)}{RESET}")
    print(f"{RED}Failed: {len(result.failed)}{RESET}")
    print(f"{YELLOW}Warnings: {len(result.warnings)}{RESET}")

    if result.failed:
        print(f"\n{RED}FAILURES:{RESET}")
        for i, fail in enumerate(result.failed, 1):
            print(f"  {i}. {fail}")

    if result.warnings:
        print(f"\n{YELLOW}WARNINGS:{RESET}")
        for i, warn in enumerate(result.warnings, 1):
            print(f"  {i}. {warn}")

    print("\n" + "=" * 70)

    if result.is_passing():
        print(f"{GREEN}✓ VALIDATION PASSED - READY FOR SUBMISSION{RESET}")
        print("=" * 70)
        return 0
    else:
        print(f"{RED}✗ VALIDATION FAILED - FIX ISSUES BEFORE SUBMISSION{RESET}")
        print("=" * 70)
        return 1


def main() -> int:
    """Run all validation checks."""
    print(f"\n{BLUE}{'=' * 70}")
    print("PRE-SUBMISSION VALIDATION SCRIPT")
    print("Meta x PyTorch Hackathon - Round 1")
    print(f"{'=' * 70}{RESET}\n")

    result = ValidationResult()

    try:
        validate_hf_space_config(result)
        validate_openenv_spec(result)
        validate_dockerfile_builds(result)
        validate_inference_script(result)
        validate_tasks_and_graders(result)
        validate_api_endpoints(result)
        validate_dataset(result)
        validate_runtime_requirements(result)
    except Exception as e:
        print_error(f"Validation error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return generate_report(result)


if __name__ == "__main__":
    sys.exit(main())
