"""`connectors.yaml`: which sources to mirror, and running the sync.

    mirror: /var/lib/okf/mirror          # build source; one subfolder per source
    okf_config: /etc/okf/_okf.yaml       # optional: copied to <mirror>/_okf.yaml
    sources:
      - name: finance-share
        kind: fileshare
        path: /Volumes/Finance
        permissions: posix               # or none (use _okf.yaml rules)
        access: [group:finance]          # optional: for items without source permissions
      - name: hr-sharepoint
        kind: sharepoint
        tenant_id: 00000000-0000-0000-0000-000000000000
        client_id: 11111111-1111-1111-1111-111111111111
        client_secret_env: OKF_SHAREPOINT_SECRET
        site: contoso.sharepoint.com:/sites/HR
        drive: Documents
        folder: Policies
      - name: ops-drive
        kind: gdrive
        service_account_key_env: OKF_GDRIVE_KEY_FILE   # path to the JSON key
        folder_id: 1AbCdEfGhIjKlMnOpQrStUv

Secrets are only read from environment variables named in the file, never
from the file itself.
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import httpx
import yaml

from okf_mcp_server.src.connectors import fileshare, gdrive, sharepoint
from okf_mcp_server.src.connectors.base import (
    STATE_FILE,
    RemoteItem,
    SyncResult,
    sync,
)
from okf_mcp_server.src.knowledge.access import normalize_access

KINDS = ("fileshare", "sharepoint", "gdrive")
_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")


def load(path: Path) -> Dict[str, Any]:
    """Load and validate a connectors file.

    Raises:
        ValueError: For missing fields, unknown kinds, bad names or inline secrets.
    """
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict) or not config.get("mirror"):
        raise ValueError(f"{path.name}: needs a `mirror` folder")
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"{path.name}: needs a non-empty `sources` list")
    names = set()
    for source in sources:
        name = str(source.get("name", ""))
        if not _NAME.fullmatch(name) or name in names:
            raise ValueError(
                f"{path.name}: source names must be unique lowercase slugs: {name!r}"
            )
        names.add(name)
        if source.get("kind") not in KINDS:
            raise ValueError(f"{path.name}: {name}: kind must be one of {KINDS}")
        for secret in ("client_secret", "service_account_key", "private_key"):
            if secret in source:
                raise ValueError(
                    f"{path.name}: {name}: put secrets in an environment variable ({secret}_env)"
                )
        required = {
            "fileshare": ["path"],
            "sharepoint": ["tenant_id", "client_id", "client_secret_env", "site"],
            "gdrive": ["service_account_key_env", "folder_id"],
        }[source["kind"]]
        missing = [f for f in required if not source.get(f)]
        if missing:
            raise ValueError(f"{path.name}: {name}: missing {', '.join(missing)}")
        if "access" in source:
            try:
                source["access"] = normalize_access(source["access"])
            except (ValueError, TypeError, AttributeError) as e:
                raise ValueError(f"{path.name}: {name}: access: {e}") from e
    config["mirror"] = str(Path(str(config["mirror"])).expanduser())
    if (
        config.get("okf_config")
        and not Path(str(config["okf_config"])).expanduser().is_file()
    ):
        raise ValueError(f"{path.name}: okf_config not found: {config['okf_config']}")
    return config


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ValueError(f"environment variable {name} is not set")
    return value


def source_items(source: Dict[str, Any], client: httpx.Client) -> Iterable[RemoteItem]:
    """The remote items of one configured source."""
    kind = source["kind"]
    if kind == "fileshare":
        return fileshare.list_items(
            Path(source["path"]).expanduser(), source.get("permissions", "posix")
        )
    if kind == "sharepoint":
        token = sharepoint.get_token(
            client,
            source["tenant_id"],
            source["client_id"],
            _env(source["client_secret_env"]),
        )
        return sharepoint.SharePointSource(
            client,
            token,
            source["site"],
            source.get("drive", "Documents"),
            source.get("folder", ""),
            source.get("group_names", "name"),
        ).items()
    key = json.loads(
        Path(_env(source["service_account_key_env"])).read_text(encoding="utf-8")
    )
    token = gdrive.get_token(client, key, source.get("subject", ""))
    return gdrive.DriveSource(client, token, source["folder_id"]).items()


def run(
    config: Dict[str, Any],
    only: Optional[List[str]] = None,
    client: Optional[httpx.Client] = None,
) -> List[SyncResult]:
    """Sync every source (or `only` these) into `<mirror>/<name>`.

    A source that fails to list keeps its previous mirror untouched and is
    reported with an error, so one outage does not delete that content.
    """
    mirror = Path(config["mirror"])
    mirror.mkdir(parents=True, exist_ok=True)
    if config.get("okf_config"):
        # Build rules (types, lifecycle, access prefixes like "hr-share/") for the mirror.
        shutil.copyfile(
            Path(str(config["okf_config"])).expanduser(), mirror / "_okf.yaml"
        )
    elif (mirror / "_okf.yaml").is_file():
        (mirror / "_okf.yaml").unlink()  # okf_config was removed: drop its rules too
    results = []
    if not only:
        # A source removed from the file must stop being published.
        configured = {source["name"] for source in config["sources"]}
        for folder in sorted(mirror.iterdir()):
            if folder.name not in configured and (folder / STATE_FILE).is_file():
                shutil.rmtree(folder)
                results.append(
                    SyncResult(source=folder.name, deleted=["<source removed>"])
                )
    own_client = client is None
    client = client or httpx.Client(timeout=60)
    try:
        for source in config["sources"]:
            if only and source["name"] not in only:
                continue
            try:
                items = list(source_items(source, client))
            except Exception as e:  # noqa: BLE001 - report per source, keep the old mirror
                failed = SyncResult(source=source["name"])
                failed.errors["<listing>"] = f"{type(e).__name__}: {e}"
                results.append(failed)
                continue
            default = source.get("access")
            if default is not None:
                for item in items:
                    if item.principals is None:
                        item.principals = list(default)
            results.append(sync(source["name"], mirror / source["name"], items))
    finally:
        if own_client:
            client.close()
    return results
