"""
Network Validator

Validates that the MCP server is running in a properly air-gapped environment.
This is CRITICAL for enterprise customers who need to prove no external access.

Tests performed:
1. DNS resolution fails for external domains
2. HTTPS connections fail to external IPs
3. All traffic stays on localhost/internal network
4. No unexpected listening ports
"""

import socket
import asyncio
import platform
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import ipaddress


class ValidationStatus(str, Enum):
    """Validation result status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationCheck:
    """Individual validation check result."""
    name: str
    status: ValidationStatus
    message: str
    details: Optional[dict] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NetworkValidationResult:
    """Complete network validation result."""
    overall_status: ValidationStatus
    checks: list[ValidationCheck] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    hostname: str = ""
    platform: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/reporting."""
        return {
            "overall_status": self.overall_status.value,
            "timestamp": self.timestamp.isoformat(),
            "hostname": self.hostname,
            "platform": self.platform,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
            "passed_count": sum(1 for c in self.checks if c.status == ValidationStatus.PASSED),
            "failed_count": sum(1 for c in self.checks if c.status == ValidationStatus.FAILED),
            "warning_count": sum(1 for c in self.checks if c.status == ValidationStatus.WARNING),
        }

    def get_report(self) -> str:
        """Generate human-readable report."""
        lines = [
            "=" * 60,
            "NETWORK ISOLATION VALIDATION REPORT",
            "=" * 60,
            f"Timestamp: {self.timestamp.isoformat()}",
            f"Hostname: {self.hostname}",
            f"Platform: {self.platform}",
            f"Overall Status: {self.overall_status.value.upper()}",
            "-" * 60,
            "CHECKS:",
        ]

        for check in self.checks:
            status_icon = {
                ValidationStatus.PASSED: "[PASS]",
                ValidationStatus.FAILED: "[FAIL]",
                ValidationStatus.WARNING: "[WARN]",
                ValidationStatus.SKIPPED: "[SKIP]",
            }[check.status]
            lines.append(f"  {status_icon} {check.name}")
            lines.append(f"         {check.message}")
            if check.details:
                for key, value in check.details.items():
                    lines.append(f"         - {key}: {value}")

        lines.append("-" * 60)
        passed = sum(1 for c in self.checks if c.status == ValidationStatus.PASSED)
        failed = sum(1 for c in self.checks if c.status == ValidationStatus.FAILED)
        lines.append(f"Summary: {passed} passed, {failed} failed")
        lines.append("=" * 60)

        return "\n".join(lines)


class NetworkValidator:
    """
    Validates network isolation for air-gapped deployments.

    This validator performs multiple checks to ensure:
    1. No external DNS resolution is possible
    2. No external network connections can be made
    3. Only localhost services are accessible
    4. The system is properly isolated
    """

    # External domains to test (should all fail in air-gap)
    EXTERNAL_TEST_DOMAINS = [
        "google.com",
        "microsoft.com",
        "anthropic.com",
        "openai.com",
        "api.openai.com",
    ]

    # External IPs to test (should all fail in air-gap)
    EXTERNAL_TEST_IPS = [
        ("8.8.8.8", 53),       # Google DNS
        ("1.1.1.1", 53),       # Cloudflare DNS
        ("13.107.42.14", 443), # Microsoft
    ]

    # Localhost addresses that SHOULD work
    LOCALHOST_ADDRESSES = ["127.0.0.1", "localhost", "::1"]

    def __init__(
        self,
        strict_mode: bool = True,
        timeout: float = 2.0,
    ):
        """
        Initialize the network validator.

        Args:
            strict_mode: If True, any external access fails validation
            timeout: Timeout for network tests in seconds
        """
        self.strict_mode = strict_mode
        self.timeout = timeout

    async def validate(self) -> NetworkValidationResult:
        """
        Run all validation checks.

        Returns:
            NetworkValidationResult with all check results
        """
        result = NetworkValidationResult(
            overall_status=ValidationStatus.PASSED,
            hostname=socket.gethostname(),
            platform=platform.platform(),
        )

        # Run all checks
        checks = [
            self._check_external_dns(),
            self._check_external_connections(),
            self._check_localhost_access(),
            self._check_listening_ports(),
            self._check_environment_variables(),
        ]

        for check_coro in checks:
            try:
                check = await check_coro
                result.checks.append(check)

                # Update overall status
                if check.status == ValidationStatus.FAILED:
                    result.overall_status = ValidationStatus.FAILED
                elif check.status == ValidationStatus.WARNING and result.overall_status != ValidationStatus.FAILED:
                    result.overall_status = ValidationStatus.WARNING

            except Exception as e:
                result.checks.append(ValidationCheck(
                    name="check_error",
                    status=ValidationStatus.FAILED,
                    message=f"Check failed with error: {str(e)}",
                ))
                result.overall_status = ValidationStatus.FAILED

        return result

    async def _check_external_dns(self) -> ValidationCheck:
        """
        Check that external DNS resolution fails.

        In a properly air-gapped environment, DNS queries to
        external domains should not resolve.
        """
        resolved_domains = []

        for domain in self.EXTERNAL_TEST_DOMAINS:
            try:
                # Try to resolve the domain
                socket.setdefaulttimeout(self.timeout)
                socket.gethostbyname(domain)
                resolved_domains.append(domain)
            except socket.gaierror:
                # Good - resolution failed
                pass
            except socket.timeout:
                # Good - timed out
                pass
            except Exception:
                # Other errors are also acceptable
                pass

        if resolved_domains:
            return ValidationCheck(
                name="external_dns",
                status=ValidationStatus.FAILED,
                message=f"External DNS resolution succeeded for {len(resolved_domains)} domain(s)",
                details={"resolved_domains": resolved_domains},
            )

        return ValidationCheck(
            name="external_dns",
            status=ValidationStatus.PASSED,
            message="External DNS resolution blocked (all test domains failed to resolve)",
            details={"tested_domains": self.EXTERNAL_TEST_DOMAINS},
        )

    async def _check_external_connections(self) -> ValidationCheck:
        """
        Check that external TCP connections fail.

        In a properly air-gapped environment, TCP connections to
        external IPs should be blocked.
        """
        successful_connections = []

        for ip, port in self.EXTERNAL_TEST_IPS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                result = sock.connect_ex((ip, port))
                sock.close()

                if result == 0:
                    successful_connections.append(f"{ip}:{port}")
            except Exception:
                # Connection failed - this is expected
                pass

        if successful_connections:
            return ValidationCheck(
                name="external_connections",
                status=ValidationStatus.FAILED,
                message=f"External connections succeeded to {len(successful_connections)} endpoint(s)",
                details={"connected_to": successful_connections},
            )

        return ValidationCheck(
            name="external_connections",
            status=ValidationStatus.PASSED,
            message="External TCP connections blocked (all test endpoints unreachable)",
            details={"tested_endpoints": [f"{ip}:{port}" for ip, port in self.EXTERNAL_TEST_IPS]},
        )

    async def _check_localhost_access(self) -> ValidationCheck:
        """
        Check that localhost is accessible.

        The MCP server needs to communicate with local services
        like Ollama on localhost.
        """
        localhost_accessible = False

        for addr in self.LOCALHOST_ADDRESSES:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                # Try to connect to a common local port (we just check if localhost resolves)
                sock.bind((addr if addr != "localhost" else "127.0.0.1", 0))
                sock.close()
                localhost_accessible = True
                break
            except Exception:
                continue

        if localhost_accessible:
            return ValidationCheck(
                name="localhost_access",
                status=ValidationStatus.PASSED,
                message="Localhost access confirmed",
            )

        return ValidationCheck(
            name="localhost_access",
            status=ValidationStatus.WARNING,
            message="Could not verify localhost access",
        )

    async def _check_listening_ports(self) -> ValidationCheck:
        """
        Check for unexpected listening ports.

        Identifies ports that might indicate external service exposure.
        """
        try:
            # Use netstat or ss to list listening ports
            if platform.system() == "Windows":
                cmd = ["netstat", "-an"]
            else:
                cmd = ["ss", "-tlnp"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )

            listening_external = []
            for line in result.stdout.split("\n"):
                # Look for LISTENING on non-localhost addresses
                if "LISTEN" in line or "ESTABLISHED" in line:
                    # Check if bound to 0.0.0.0 or external IP
                    if "0.0.0.0:" in line or "*:" in line:
                        # Extract port info
                        listening_external.append(line.strip())

            if listening_external and self.strict_mode:
                return ValidationCheck(
                    name="listening_ports",
                    status=ValidationStatus.WARNING,
                    message=f"Found {len(listening_external)} port(s) listening on all interfaces",
                    details={"ports": listening_external[:10]},  # Limit output
                )

            return ValidationCheck(
                name="listening_ports",
                status=ValidationStatus.PASSED,
                message="No concerning listening ports detected",
            )

        except Exception as e:
            return ValidationCheck(
                name="listening_ports",
                status=ValidationStatus.SKIPPED,
                message=f"Could not check listening ports: {str(e)}",
            )

    async def _check_environment_variables(self) -> ValidationCheck:
        """
        Check environment for proxy or external connection settings.

        Environment variables like HTTP_PROXY could bypass air-gap.
        """
        import os

        proxy_vars = [
            "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
            "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy",
        ]

        found_proxies = {}
        for var in proxy_vars:
            value = os.environ.get(var)
            if value:
                found_proxies[var] = value

        if found_proxies:
            return ValidationCheck(
                name="environment_variables",
                status=ValidationStatus.WARNING,
                message="Proxy environment variables detected",
                details={"proxy_vars": list(found_proxies.keys())},
            )

        return ValidationCheck(
            name="environment_variables",
            status=ValidationStatus.PASSED,
            message="No proxy environment variables set",
        )

    async def validate_endpoint(self, endpoint: str) -> ValidationCheck:
        """
        Validate that an endpoint is localhost only.

        Args:
            endpoint: URL to validate

        Returns:
            ValidationCheck result
        """
        from urllib.parse import urlparse

        parsed = urlparse(endpoint)
        host = parsed.hostname or ""

        # Check if it's a localhost address
        if host.lower() in ["localhost", "127.0.0.1", "::1"]:
            return ValidationCheck(
                name="endpoint_validation",
                status=ValidationStatus.PASSED,
                message=f"Endpoint {endpoint} is localhost",
            )

        # Check if it's a private IP
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback:
                return ValidationCheck(
                    name="endpoint_validation",
                    status=ValidationStatus.PASSED,
                    message=f"Endpoint {endpoint} is private/loopback",
                )
        except ValueError:
            pass

        return ValidationCheck(
            name="endpoint_validation",
            status=ValidationStatus.FAILED,
            message=f"Endpoint {endpoint} is not a localhost address",
            details={"host": host},
        )


async def main():
    """Run network validation as standalone script."""
    print("Running Network Isolation Validation...")
    print()

    validator = NetworkValidator(strict_mode=True)
    result = await validator.validate()

    print(result.get_report())

    # Exit with appropriate code
    if result.overall_status == ValidationStatus.PASSED:
        print("\n Air-gap validation PASSED")
        return 0
    elif result.overall_status == ValidationStatus.WARNING:
        print("\n Air-gap validation completed with WARNINGS")
        return 1
    else:
        print("\n Air-gap validation FAILED")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
