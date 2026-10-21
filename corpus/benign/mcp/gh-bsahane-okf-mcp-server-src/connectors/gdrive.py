"""Google Drive connector over the Drive v3 API (service account).

Needs a service account JSON key with the Drive API enabled; share the
folders with the service account's email (or use domain-wide delegation with
`subject`). Lists a folder recursively, including shared drives, exports
Google Docs/Sheets/Slides as DOCX/XLSX/PPTX, downloads other supported
files, and maps Drive permissions to principals:

- user    -> user:<email>
- group   -> group:<group email>
- domain  -> *   (anyone in the domain; this server already requires sign-in)
- anyone  -> *

Drive only returns permissions to accounts that can share the file, and never
for shared drives; such items get the source's `access` default (or `_okf.yaml`
rules) instead of being hidden from everyone.
"""

import base64
import json
import re
import time
from functools import partial
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import httpx

from okf_mcp_server.src.connectors.base import RemoteItem
from okf_mcp_server.src.connectors.http import request

API = "https://www.googleapis.com/drive/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/drive.readonly"
FOLDER = "application/vnd.google-apps.folder"
EXPORTS = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
}
FIELDS = "nextPageToken,files(id,name,mimeType,modifiedTime,md5Checksum,size,permissions(type,role,emailAddress,domain))"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def service_account_assertion(
    key: Dict[str, Any], subject: str = "", now: Optional[int] = None
) -> str:
    """RS256-signed JWT for the OAuth 2.0 JWT bearer grant."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    now = int(now or time.time())
    claims = {
        "iss": key["client_email"],
        "scope": SCOPE,
        "aud": key.get("token_uri", TOKEN_URL),
        "iat": now,
        "exp": now + 3600,
    }
    if subject:
        claims["sub"] = subject
    header = {"alg": "RS256", "typ": "JWT", "kid": key.get("private_key_id", "")}
    signing_input = f"{_b64(json.dumps(header).encode())}.{_b64(json.dumps(claims).encode())}".encode()
    private_key = serialization.load_pem_private_key(
        key["private_key"].encode(), password=None
    )
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise ValueError("service account key must be an RSA private key")
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input.decode()}.{_b64(signature)}"


def get_token(client: httpx.Client, key: Dict[str, Any], subject: str = "") -> str:
    """Access token for the service account."""
    response = request(
        client,
        "POST",
        key.get("token_uri", TOKEN_URL),
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": service_account_assertion(key, subject),
        },
    )
    return response.json()["access_token"]


def principals_from(permissions: List[Dict[str, Any]]) -> List[str]:
    """Map Drive permission entries to principals."""
    out = set()
    for perm in permissions:
        kind = perm.get("type")
        if kind in ("anyone", "domain"):
            out.add("*")
        elif kind == "user" and perm.get("emailAddress"):
            out.add(f"user:{perm['emailAddress']}")
        elif kind == "group" and perm.get("emailAddress"):
            out.add(f"group:{perm['emailAddress']}")
    return sorted(out)


class DriveSource:
    """Lists and downloads one Drive folder (My Drive or a shared drive)."""

    def __init__(self, client: httpx.Client, token: str, folder_id: str):
        """`folder_id` is the ID in the folder's URL.

        Raises:
            ValueError: For IDs that are not Drive IDs (they are embedded in queries).
        """
        if not re.fullmatch(r"[A-Za-z0-9_-]+", folder_id or ""):
            raise ValueError(f"not a Drive folder ID: {folder_id!r}")
        self.client = client
        self.headers = {"Authorization": f"Bearer {token}"}
        self.folder_id = folder_id

    def _list(self, folder_id: str) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        token: Optional[str] = None
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": FIELDS,
                "pageSize": 1000,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if token:
                params["pageToken"] = token
            page = request(
                self.client, "GET", f"{API}/files", headers=self.headers, params=params
            ).json()
            files.extend(page.get("files", []))
            token = page.get("nextPageToken")
            if not token:
                return files

    def _download(self, file: Dict[str, Any], target: Path) -> None:
        export = EXPORTS.get(file["mimeType"])
        if export:
            url, params = f"{API}/files/{file['id']}/export", {"mimeType": export[0]}
        else:
            url, params = (
                f"{API}/files/{file['id']}",
                {"alt": "media", "supportsAllDrives": "true"},
            )
        with self.client.stream(
            "GET", url, headers=self.headers, params=params, follow_redirects=True
        ) as response:
            response.raise_for_status()
            with open(target, "wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)

    def items(self) -> Iterator[RemoteItem]:
        """Every file below the folder, with its permissions."""
        # A wrong or unshared folder ID would otherwise list as empty and empty the mirror.
        folder = request(
            self.client,
            "GET",
            f"{API}/files/{self.folder_id}",
            headers=self.headers,
            params={"fields": "id,mimeType", "supportsAllDrives": "true"},
        ).json()
        if folder.get("mimeType") != FOLDER:
            raise ValueError(f"{self.folder_id} is not a folder")
        stack = [(self.folder_id, "")]
        while stack:
            folder_id, prefix = stack.pop()
            for file in self._list(folder_id):
                if file["mimeType"] == FOLDER:
                    stack.append((file["id"], f"{prefix}{file['name']}/"))
                    continue
                name = file["name"]
                export = EXPORTS.get(file["mimeType"])
                if export and not name.lower().endswith(export[1]):
                    name += export[1]
                elif file["mimeType"].startswith("application/vnd.google-apps."):
                    continue  # forms, drawings, shortcuts: nothing to extract
                yield RemoteItem(
                    key=file["id"],
                    path=prefix + name,
                    version=file.get("md5Checksum") or file.get("modifiedTime", ""),
                    size=int(file["size"]) if file.get("size") else None,
                    principals=principals_from(file["permissions"])
                    if file.get("permissions")
                    else None,
                    download=partial(self._download, file),
                )
