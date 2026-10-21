"""Managed execution: Fathom invokes the target directly."""

from typing import Callable, Optional
from subprocess import run
import json
from fathom.models import ExecutionResult, SkillResult, ResultState, ValidationMethod
from datetime import datetime


class ManagedExecutor:
    """Invokes a target directly (subprocess, API, etc.)."""

    def __init__(self):
        self.version = "1.0"

    def invoke_subprocess(
        self,
        python_path: str,
        script_path: str,
        args: list[str],
        test_inputs: dict,
        cwd: str = None,
        timeout: int = 30,
    ) -> ExecutionResult:
        """
        Invoke target via subprocess.
        python_path: absolute path to Python interpreter
        script_path: absolute path to wrapper script
        args: command-line arguments to pass to script
        test_inputs: JSON inputs (for logging/context)
        cwd: working directory (for .env loading, relative imports)
        """
        try:
            command = [python_path, script_path] + args
            result = run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )

            if result.returncode != 0:
                return ExecutionResult(
                    test_case_name=test_inputs.get("_test_case_name", "unknown"),
                    succeeded=False,
                    error=f"Subprocess exited with code {result.returncode}: {result.stderr}",
                )

            output = result.stdout.strip()
            return ExecutionResult(
                test_case_name=test_inputs.get("_test_case_name", "unknown"),
                succeeded=True,
                output=output,
            )

        except Exception as e:
            return ExecutionResult(
                test_case_name=test_inputs.get("_test_case_name", "unknown"),
                succeeded=False,
                error=f"Managed execution failed: {str(e)}",
            )

    def invoke_api(
        self,
        endpoint: str,
        test_inputs: dict,
        auth_token: Optional[str] = None,
        timeout: int = 30,
    ) -> ExecutionResult:
        """
        Invoke target via HTTP API.
        Endpoint should accept POST with JSON body, return JSON response.
        """
        try:
            import requests

            headers = {"Content-Type": "application/json"}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            response = requests.post(
                endpoint,
                json=test_inputs,
                headers=headers,
                timeout=timeout,
            )

            if response.status_code != 200:
                return ExecutionResult(
                    test_case_name=test_inputs.get("_test_case_name", "unknown"),
                    succeeded=False,
                    error=f"API returned {response.status_code}: {response.text}",
                )

            output = response.text
            return ExecutionResult(
                test_case_name=test_inputs.get("_test_case_name", "unknown"),
                succeeded=True,
                output=output,
            )

        except Exception as e:
            return ExecutionResult(
                test_case_name=test_inputs.get("_test_case_name", "unknown"),
                succeeded=False,
                error=f"API invocation failed: {str(e)}",
            )
