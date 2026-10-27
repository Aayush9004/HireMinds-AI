"""
Secure coding-assessment sandbox.

Security model
--------------
Candidate code is **never** executed inside the FastAPI process. This module
only builds a harness file and asks an external Docker daemon to run it in a
locked-down container.

Default configuration is DISABLED. When disabled, evaluation returns
``sandbox_unavailable`` and the attempt is marked partially evaluated. This is
deliberate: executing untrusted code without a real sandbox would be unsafe.

Docker restrictions applied:
* ``--network none``            no network access
* ``--read-only``               read-only root filesystem
* ``--tmpfs /tmp``              small, non-executable temporary filesystem
* ``--memory`` / ``--memory-swap``  memory cap (swap disabled)
* ``--cpus``                    CPU cap
* ``--pids-limit``              fork-bomb protection
* ``--cap-drop ALL``            drop Linux capabilities
* ``--security-opt no-new-privileges``
* non-root ``--user 65534:65534``
* candidate code mounted read-only
* host-side subprocess timeout as a final backstop

Limitations:
* Access to the Docker socket is effectively root-equivalent. Deploy the API
  with a restricted Docker context / dedicated sandbox host.
* The in-container harness runs in the same process as the candidate's code, so
  a malicious candidate could influence the harness output. The sandbox protects
  the host; it does not make the candidate's score tamper-proof.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

RESULT_MARKER = "__HIREMINDS_RESULT__"

_HARNESS_TEMPLATE = r'''
import contextlib
import io
import json
import sys

_candidate_code = {candidate_code}
_test_cases = {test_cases}
_function_name = {function_name}

# Capture references before running untrusted code so monkey-patching common
# modules is less likely to corrupt the result channel.
_dumps = json.dumps
_print = print
_StringIO = io.StringIO
_redirect_stdout = contextlib.redirect_stdout


def _safe(value):
    try:
        _dumps(value)
        return value
    except Exception:
        return repr(value)


def _same(actual, expected):
    try:
        return _dumps(_safe(actual), sort_keys=True) == _dumps(_safe(expected), sort_keys=True)
    except Exception:
        return False


def main():
    namespace = {{"__name__": "__candidate__"}}
    captured = _StringIO()
    try:
        with _redirect_stdout(captured):
            exec(compile(_candidate_code, "<candidate>", "exec"), namespace)

        function = namespace.get(_function_name)
        if not callable(function):
            _print({marker} + _dumps({{"fatal": "Function not found: " + _function_name}}))
            return

        results = []
        for index, test_case in enumerate(_test_cases):
            args = test_case.get("input", [])
            if not isinstance(args, list):
                args = [args]
            expected = test_case.get("expected")
            try:
                with _redirect_stdout(captured):
                    actual = function(*args)
                results.append({{
                    "index": index,
                    "passed": _same(actual, expected),
                    "actual": _safe(actual),
                    "expected": _safe(expected),
                }})
            except Exception as exc:
                results.append({{
                    "index": index,
                    "passed": False,
                    "error": repr(exc),
                    "expected": _safe(expected),
                }})

        _print({marker} + _dumps(results))
    except Exception as exc:
        _print({marker} + _dumps({{"fatal": repr(exc)}}))


if __name__ == "__main__":
    main()
'''


@dataclass
class SandboxResult:
    """Outcome of evaluating a coding submission."""

    status: str
    passed_tests: int = 0
    total_tests: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _unavailable(message: str, total_tests: int = 0) -> SandboxResult:
    return SandboxResult(
        status="sandbox_unavailable",
        total_tests=total_tests,
        message=message,
    )


def build_harness(code: str, test_cases: List[Dict[str, Any]], function_name: str) -> str:
    """Build the Python harness file. This does not execute anything."""
    return _HARNESS_TEMPLATE.format(
        candidate_code=repr(code),
        test_cases=repr(test_cases),
        function_name=repr(function_name),
        marker=repr(RESULT_MARKER),
    )


def _parse_harness_output(stdout: str) -> Optional[Any]:
    """Return the last marker-prefixed JSON payload, if present."""
    payload = None
    for line in stdout.splitlines():
        if line.startswith(RESULT_MARKER):
            try:
                payload = json.loads(line[len(RESULT_MARKER):])
            except json.JSONDecodeError:
                continue
    return payload


class CodingSandbox:
    """Docker-backed Python coding sandbox."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        backend: Optional[str] = None,
        docker_binary: Optional[str] = None,
        image: Optional[str] = None,
    ) -> None:
        self.enabled = settings.CODE_EXECUTION_ENABLED if enabled is None else enabled
        self.backend = (backend or settings.CODE_EXECUTION_BACKEND).lower()
        self.docker_binary = docker_binary or settings.CODE_EXECUTION_DOCKER_BINARY
        self.image = image or settings.CODE_EXECUTION_DOCKER_IMAGE

    def is_available(self) -> bool:
        if not self.enabled or self.backend != "docker":
            return False
        return shutil.which(self.docker_binary) is not None

    def evaluate(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
        function_name: str,
        time_limit_ms: Optional[int] = None,
        memory_limit_mb: Optional[int] = None,
    ) -> SandboxResult:
        """
        Evaluate Python code against test cases in a Docker container.

        Returns ``sandbox_unavailable`` when execution is disabled or Docker is
        not available. Never falls back to in-process execution.
        """
        total_tests = len(test_cases)
        if not self.enabled:
            return _unavailable(
                "Coding execution is disabled (CODE_EXECUTION_ENABLED=false). "
                "The submission was stored but not executed. Configure a secure "
                "Docker sandbox to enable coding evaluation.",
                total_tests,
            )
        if self.backend != "docker":
            return _unavailable(
                f"Unsupported CODE_EXECUTION_BACKEND='{self.backend}'. "
                "Only the Docker sandbox is supported.",
                total_tests,
            )
        if shutil.which(self.docker_binary) is None:
            return _unavailable(
                f"Docker binary '{self.docker_binary}' was not found. "
                "Coding evaluation is unavailable.",
                total_tests,
            )
        if not test_cases:
            return SandboxResult(
                status="error",
                total_tests=0,
                message="The coding question has no test cases.",
            )

        effective_time_ms = min(
            int(time_limit_ms or settings.CODE_EXECUTION_TIMEOUT_SECONDS * 1000),
            int(settings.CODE_EXECUTION_TIMEOUT_SECONDS * 1000),
        )
        effective_memory_mb = min(
            int(memory_limit_mb or settings.CODE_EXECUTION_MEMORY_MB),
            int(settings.CODE_EXECUTION_MEMORY_MB),
        )
        effective_time_ms = max(100, effective_time_ms)
        effective_memory_mb = max(64, effective_memory_mb)

        harness = build_harness(code, test_cases, function_name)
        started = time.monotonic()

        with tempfile.TemporaryDirectory(prefix="hireminds-sandbox-") as temp_dir:
            harness_path = Path(temp_dir) / "harness.py"
            harness_path.write_text(harness, encoding="utf-8")

            command = [
                self.docker_binary,
                "run",
                "--rm",
                "--pull", "never",
                "--network", "none",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                "--memory", f"{effective_memory_mb}m",
                "--memory-swap", f"{effective_memory_mb}m",
                "--cpus", str(settings.CODE_EXECUTION_CPU_LIMIT),
                "--pids-limit", str(settings.CODE_EXECUTION_PIDS_LIMIT),
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "--ulimit", "nofile=64:64",
                "--user", "65534:65534",
                "--workdir", "/workspace",
                "--volume", f"{temp_dir}:/workspace:ro",
                "--env", "PYTHONDONTWRITEBYTECODE=1",
                "--label", "hireminds-sandbox=true",
                self.image,
                "python", "-I", "-B", "/workspace/harness.py",
            ]

            timeout_seconds = (
                effective_time_ms / 1000.0
                + max(0.0, settings.CODE_EXECUTION_STARTUP_GRACE_SECONDS)
            )
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                duration_ms = int((time.monotonic() - started) * 1000)
                return SandboxResult(
                    status="timeout",
                    total_tests=total_tests,
                    duration_ms=duration_ms,
                    message=f"Execution exceeded the {effective_time_ms} ms time limit.",
                )
            except OSError as exc:
                duration_ms = int((time.monotonic() - started) * 1000)
                logger.warning("Sandbox launch failed: %s", exc)
                return _unavailable(
                    "The sandbox process could not be started.",
                    total_tests,
                )

        duration_ms = int((time.monotonic() - started) * 1000)
        stdout = completed.stdout[: settings.CODE_EXECUTION_MAX_OUTPUT_BYTES]
        stderr = completed.stderr[: settings.CODE_EXECUTION_MAX_OUTPUT_BYTES]

        if completed.returncode != 0:
            # Common environment failures should be reported as "unavailable",
            # not as a candidate failure.
            lowered = stderr.lower()
            if any(
                marker in lowered
                for marker in (
                    "cannot connect to the docker daemon",
                    "permission denied",
                    "unable to find image",
                    "no such image",
                    "pull access denied",
                )
            ):
                return _unavailable(
                    "The Docker sandbox is not available or the configured image "
                    "is missing. Pull the image and verify Docker permissions.",
                    total_tests,
                )
            return SandboxResult(
                status="error",
                total_tests=total_tests,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                message=f"Sandbox exited with code {completed.returncode}.",
            )

        payload = _parse_harness_output(stdout)
        if payload is None:
            return SandboxResult(
                status="error",
                total_tests=total_tests,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                message="The sandbox produced no parseable result.",
            )
        if isinstance(payload, dict) and payload.get("fatal"):
            return SandboxResult(
                status="error",
                total_tests=total_tests,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                message=str(payload["fatal"]),
            )
        if not isinstance(payload, list):
            return SandboxResult(
                status="error",
                total_tests=total_tests,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                message="The sandbox returned an unexpected result shape.",
            )

        passed = sum(1 for item in payload if isinstance(item, dict) and item.get("passed"))
        status = "passed" if passed == total_tests else "failed"
        return SandboxResult(
            status=status,
            passed_tests=passed,
            total_tests=total_tests,
            details=payload,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            message=(
                "All test cases passed."
                if status == "passed"
                else f"{passed} of {total_tests} test cases passed."
            ),
        )
