"""
Unit tests for BOEClient and typed exceptions in core/.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from core.client import BOEClient
from core.exceptions import (
    BOEAuthError,
    BOEError,
    BOENotFoundError,
    BOEProcessingError,
)


class TestBOEClientInitialization:
    def test_default_init(self):
        client = BOEClient()
        assert client.protocol == "http"
        assert client.host == "localhost"
        assert client.port == "8080"
        assert client.base_url == "http://localhost:8080/biprws"
        assert client.webi_url == "http://localhost:8080/biprws/raylight/v1"
        assert client.sl_url == "http://localhost:8080/biprws/sl/v1"
        assert client.query_url == "http://localhost:8080/biprws/v1"
        assert client.logon_token is None

    def test_custom_base_url_with_prefix(self):
        client = BOEClient(base_url="https://boserver.corp:8443/BOE/biprws")
        assert client.protocol == "https"
        assert client.host == "boserver.corp"
        assert client.port == "8443"
        assert client.base_url == "https://boserver.corp:8443/BOE/biprws"
        assert client.webi_url == "https://boserver.corp:8443/BOE/biprws/raylight/v1"


class TestBOEClientResponseHandling:
    def test_handle_response_json(self):
        client = BOEClient()
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.json.return_value = {"key": "value"}

        result = client._handle_response(mock_resp)
        assert result == {"key": "value"}

    def test_handle_response_text(self):
        client = BOEClient()
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/xml"}
        mock_resp.text = "<xml>data</xml>"

        result = client._handle_response(mock_resp)
        assert result == "<xml>data</xml>"

    def test_handle_response_401(self):
        client = BOEClient()
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 401
        mock_resp.url = "http://localhost:8080/biprws/v1/cmsquery"

        with pytest.raises(BOEAuthError) as exc_info:
            client._handle_response(mock_resp)
        assert "Unauthorized" in str(exc_info.value)
        assert exc_info.value.status_code == 401

    def test_handle_response_404(self):
        client = BOEClient()
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 404
        mock_resp.url = "http://localhost:8080/biprws/raylight/v1/documents/9999"

        with pytest.raises(BOENotFoundError) as exc_info:
            client._handle_response(mock_resp)
        assert "Resource not found" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    def test_handle_response_500_wsr_00999(self):
        client = BOEClient()
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 500
        mock_resp.json.return_value = {
            "error": {
                "error_code": "WSR 00999",
                "message": "Web Intelligence Server internal error",
            }
        }

        with pytest.raises(BOEProcessingError) as exc_info:
            client._handle_response(mock_resp)
        assert "WSR 00999" in str(exc_info.value)
        assert exc_info.value.status_code == 500

    def test_handle_response_generic_error(self):
        client = BOEClient()
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"

        with pytest.raises(BOEError) as exc_info:
            client._handle_response(mock_resp)
        assert "HTTP request failed with status 400" in str(exc_info.value)


class TestBOEClientAuthentication:
    @patch.object(requests.Session, "get")
    @patch.object(requests.Session, "post")
    def test_set_logon_token_success(self, mock_post, mock_get):
        client = BOEClient()
        # Mock template response
        mock_get_resp = MagicMock()
        mock_get_resp.json.return_value = {"userName": "", "password": "", "auth": "secEnterprise"}
        mock_get.return_value = mock_get_resp

        # Mock token response
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"logonToken": "VALID_TOKEN_XYZ"}
        mock_post.return_value = mock_post_resp

        token = client.set_logon_token("admin", "secret")
        assert token == "VALID_TOKEN_XYZ"
        assert client.logon_token == "VALID_TOKEN_XYZ"
        assert client.headers["X-SAP-LogonToken"] == "VALID_TOKEN_XYZ"

    @patch.object(requests.Session, "get")
    @patch.object(requests.Session, "post")
    def test_set_logon_token_invalid_credentials(self, mock_post, mock_get):
        client = BOEClient()
        mock_get_resp = MagicMock()
        mock_get_resp.json.return_value = {}
        mock_get.return_value = mock_get_resp

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 401
        mock_post.return_value = mock_post_resp

        with pytest.raises(BOEAuthError) as exc_info:
            client.set_logon_token("admin", "wrong_password")
        assert "Invalid credentials" in str(exc_info.value)

    def test_bo_logoff(self):
        client = BOEClient()
        client.logon_token = "ACTIVE_TOKEN"
        client.headers["X-SAP-LogonToken"] = "ACTIVE_TOKEN"

        res = client.bo_logoff()
        assert res is True
        assert client.logon_token is None
        assert "X-SAP-LogonToken" not in client.headers
