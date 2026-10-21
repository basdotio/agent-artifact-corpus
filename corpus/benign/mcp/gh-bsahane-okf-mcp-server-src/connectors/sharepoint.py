"""SharePoint / OneDrive connector over Microsoft Graph (app-only).

Needs an Entra ID app registration with the `Sites.Read.All` (or
`Sites.Selected`) application permission and a client secret. Lists a
document library folder recursively, downloads supported files and maps each
item's permissions to principals:

- user (grantedToV2.user)          -> user:<email or id>
- Entra group (grantedToV2.group)  -> group:<display name>
- SharePoint group (siteGroup)     -> group:<display name>
- sharing link, organization scope -> *   (any authenticated user)
- sharing link, anonymous scope    -> *
- sharing link, users scope        -> the listed users

Group names must match the groups claim your identity provider puts in
tokens; with Entra ID tokens that claim holds object IDs unless configured
to emit names, so set `group_names: id` to map groups by ID instead.
"""

from functools import partial
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import quote

import httpx

from okf_mcp_server.src.connectors.base import RemoteItem
from okf_mcp_server.src.connectors.http import request

GRAPH = "https://graph.microsoft.com/v1.0"
LOGIN = "https://login.microsoftonline.com"


def get_token(
    client: httpx.Client, tenant_id: str, client_id: str, client_secret: str
) -> str:
    """App-only token for Microsoft Graph (client credentials grant)."""
    response = request(
        client,
        "POST",
        f"{LOGIN}/{tenant_id}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        },
    )
    return response.json()["access_token"]


def _principals_from(permissions: List[Dict[str, Any]], group_names: str) -> List[str]:
    out = set()

    def identity(entry: Dict[str, Any]) -> None:
        user = entry.get("user") or {}
        if user:
            out.add(f"user:{user.get('email') or user.get('id')}")
        for kind in ("group", "siteGroup"):
            group = entry.get(kind) or {}
            if group:
                name = (
                    group.get("id")
                    if group_names == "id"
                    else group.get("displayName") or group.get("id")
                )
                if name:
                    out.add(f"group:{name}")

    for perm in permissions:
        link = perm.get("link") or {}
        if link.get("scope") in ("organization", "anonymous"):
            out.add("*")
        if perm.get("grantedToV2"):
            identity(perm["grantedToV2"])
        for entry in perm.get("grantedToIdentitiesV2") or []:
            identity(entry)
    return sorted(p for p in out if not p.endswith(":None"))


class SharePointSource:
    """Lists and downloads one document-library folder."""

    def __init__(
        self,
        client: httpx.Client,
        token: str,
        site: str,
        drive: str = "Documents",
        folder: str = "",
        group_names: str = "name",
    ):
        """`site` is `host:/sites/Name` (or a Graph site ID); `drive` a library name."""
        self.client = client
        self.headers = {"Authorization": f"Bearer {token}"}
        self.group_names = group_names
        site_id = self._get(f"{GRAPH}/sites/{site}")["id"]
        drives = self._paged(f"{GRAPH}/sites/{site_id}/drives")
        match = next((d for d in drives if d.get("name") == drive), None)
        if match is None:
            raise ValueError(f"drive {drive!r} not found in site {site!r}")
        self.drive_id = match["id"]
        folder = folder.strip("/")
        root = f"{GRAPH}/drives/{self.drive_id}/root" + (
            f":/{quote(folder)}:" if folder else ""
        )
        self.root_id = self._get(root)["id"]

    def _get(self, url: str, **params: Any) -> Dict[str, Any]:
        return request(
            self.client, "GET", url, headers=self.headers, params=params or None
        ).json()

    def _paged(self, url: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        next_url: Optional[str] = url
        while next_url:
            page = self._get(next_url)
            items.extend(page.get("value", []))
            next_url = page.get("@odata.nextLink")
        return items

    def _download(self, item_id: str, target: Path) -> None:
        with self.client.stream(
            "GET",
            f"{GRAPH}/drives/{self.drive_id}/items/{item_id}/content",
            headers=self.headers,
            follow_redirects=True,
        ) as response:
            response.raise_for_status()
            with open(target, "wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)

    def items(self) -> Iterator[RemoteItem]:
        """Every file below the folder, with its permissions."""
        stack = [(self.root_id, "")]
        while stack:
            folder_id, prefix = stack.pop()
            for child in self._paged(
                f"{GRAPH}/drives/{self.drive_id}/items/{folder_id}/children"
            ):
                path = f"{prefix}{child['name']}"
                if "folder" in child:
                    stack.append((child["id"], path + "/"))
                    continue
                if "file" not in child:
                    continue
                perms = self._paged(
                    f"{GRAPH}/drives/{self.drive_id}/items/{child['id']}/permissions"
                )
                yield RemoteItem(
                    key=child["id"],
                    path=path,
                    version=child.get("cTag")
                    or child.get("eTag")
                    or child.get("lastModifiedDateTime", ""),
                    size=child.get("size"),
                    principals=_principals_from(perms, self.group_names),
                    download=partial(self._download, child["id"]),
                )
