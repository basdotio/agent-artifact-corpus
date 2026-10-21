"""
Low-level HTTP client for SAP BusinessObjects REST Web Services (biprws).
Manages authentication, session tokens, request headers, timeouts, and error handling.
"""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
import urllib3

from .exceptions import (
    BOEAuthError,
    BOEError,
    BOENotFoundError,
    BOEProcessingError,
)

# Suppress InsecureRequestWarning for internal self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("BOEClient")


class BOEClient:
    """
    HTTP client managing connections, persistent sessions, and token authentication
    for SAP BusinessObjects BI Platform 4.3 SP5 REST Web Services.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        protocol: str = "http",
        host: str = "localhost",
        port: str = "8080",
        content_type: str = "application/json",
        timeout: int = 120,
        verify_ssl: bool = False,
    ):
        if base_url:
            parsed = urlparse(base_url)
            self.protocol = parsed.scheme or "http"
            self.host = parsed.hostname or host
            self.port = str(parsed.port) if parsed.port else ("443" if self.protocol == "https" else "8080")
            # Preserve path prefix if specified, e.g. /biprws or /BOE/biprws
            path_prefix = parsed.path.rstrip("/")
            if not path_prefix or path_prefix == "/":
                path_prefix = "/biprws"
            self.base_url = f"{self.protocol}://{self.host}:{self.port}{path_prefix}"
        else:
            self.protocol = protocol
            self.host = host
            self.port = port
            self.base_url = f"{protocol}://{host}:{port}/biprws"

        self.bip_url = self.base_url
        self.webi_url = f"{self.bip_url}/raylight/v1"
        self.sl_url = f"{self.bip_url}/sl/v1"
        self.query_url = f"{self.bip_url}/v1"

        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.headers: Dict[str, str] = {
            "Accept": content_type,
            "Content-Type": content_type,
        }
        self.session = requests.Session()
        self.logon_token: Optional[str] = None

    def _get_auth_template(self) -> Dict[str, Any]:
        """Retrieves logon template structure from the BI platform."""
        url = f"{self.bip_url}/logon/long"
        try:
            resp = self.session.get(url, headers=self.headers, verify=self.verify_ssl, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise BOEAuthError(f"Failed to fetch logon template from {url}: {str(e)}")

    def set_logon_token(self, username: str, password: str, auth: str = "secEnterprise") -> str:
        """
        Authenticates against SAP BusinessObjects and stores the X-SAP-LogonToken.
        """
        template = self._get_auth_template()
        template["userName"] = username
        template["password"] = password
        if "auth" in template:
            template["auth"] = auth

        url = f"{self.bip_url}/logon/long"
        try:
            resp = self.session.post(
                url, json=template, headers=self.headers, verify=self.verify_ssl, timeout=self.timeout
            )
            if resp.status_code == 200:
                data = resp.json()
                self.logon_token = data.get("logonToken")
                if not self.logon_token:
                    raise BOEAuthError("Logon response did not contain 'logonToken'.")
                self.headers["X-SAP-LogonToken"] = self.logon_token
                logger.info(f"Logon successful for user '{username}'.")
                return self.logon_token
            elif resp.status_code == 401:
                raise BOEAuthError(f"Invalid credentials for user '{username}'.")
            else:
                raise BOEAuthError(f"Logon failed [HTTP {resp.status_code}]: {resp.text}")
        except requests.exceptions.RequestException as e:
            raise BOEAuthError(f"Network error during logon: {str(e)}")

    def set_trusted_token(self, username: str = "Administrator") -> str:
        """
        Authenticates using the SAP trusted principal authentication mechanism.
        """
        url = f"{self.bip_url}/logon/trusted"
        headers = self.headers.copy()
        headers["X-SAP-TRUSTED-USER"] = username
        try:
            resp = self.session.get(url, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                self.logon_token = data.get("logonToken")
                self.headers["X-SAP-LogonToken"] = self.logon_token
                return self.logon_token
            else:
                raise BOEAuthError(f"Trusted logon failed [HTTP {resp.status_code}]: {resp.text}")
        except requests.exceptions.RequestException as e:
            raise BOEAuthError(f"Network error during trusted logon: {str(e)}")

    def bo_logoff(self) -> bool:
        """
        Logs off from the SAP BusinessObjects platform and clears session state.
        """
        url = f"{self.bip_url}/v1/logoff"
        try:
            if self.logon_token:
                self.session.post(url, headers=self.headers, verify=self.verify_ssl, timeout=10)
        except Exception:
            pass
        finally:
            self.logon_token = None
            self.headers.pop("X-SAP-LogonToken", None)
            self.session.close()
            # Recreate session for future logons
            self.session = requests.Session()
        return True

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Any:
        """
        Executes an HTTP request with uniform error handling, header injection, and response parsing.
        """
        req_headers = self.headers.copy()
        if headers:
            req_headers.update(headers)

        req_timeout = timeout or self.timeout

        try:
            resp = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                data=data,
                headers=req_headers,
                verify=self.verify_ssl,
                timeout=req_timeout,
            )
            return self._handle_response(resp)
        except requests.exceptions.Timeout as e:
            raise BOEError(f"Request to {url} timed out after {req_timeout}s: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise BOEError(f"Request failed: {str(e)}")

    def _handle_response(self, resp: requests.Response) -> Any:
        """Inspects status codes and extracts JSON or text payload."""
        status = resp.status_code

        if 200 <= status < 300:
            if not resp.content:
                return {}
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    return resp.json()
                except ValueError:
                    return resp.text
            return resp.text

        # Error cases
        if status == 401:
            raise BOEAuthError(
                "Unauthorized. The SAP BusinessObjects session token may have expired. Please login again.",
                status_code=401,
            )
        if status == 404:
            raise BOENotFoundError(
                f"Resource not found at {resp.url} (it may be deleted or of a different document type).",
                status_code=404,
            )
        if status == 500:
            try:
                err_data = resp.json()
                if isinstance(err_data, dict):
                    err_obj = err_data.get("error", {})
                    code = err_obj.get("error_code")
                    msg = err_obj.get("message")
                    if code == "WSR 00999":
                        raise BOEProcessingError(
                            f"Web Intelligence Server Engine Error (WSR 00999): {msg}",
                            status_code=500,
                            details=err_data,
                        )
                    raise BOEError(f"SAP BO Server Error [{code}]: {msg}", status_code=500, details=err_data)
            except (ValueError, AttributeError):
                pass
            raise BOEError(f"Internal server error: {resp.text[:300]}", status_code=500)

        raise BOEError(f"HTTP request failed with status {status}: {resp.text[:300]}", status_code=status)

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return self.request("GET", url, params=params, **kwargs)

    def post(self, url: str, json_data: Optional[Any] = None, **kwargs) -> Any:
        return self.request("POST", url, json_data=json_data, **kwargs)

    def put(self, url: str, json_data: Optional[Any] = None, **kwargs) -> Any:
        return self.request("PUT", url, json_data=json_data, **kwargs)

    def delete(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return self.request("DELETE", url, params=params, **kwargs)
