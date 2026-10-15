"""Contracts: one directory per Contract in the private contracts repo (ADR 0003).

    <contracts-dir>/<id>/contract.yaml       what the Contract runs; secret *names* only
    <contracts-dir>/<id>/secrets.sops.yaml   SOPS-encrypted map: secret name -> value
    <contracts-dir>/<id>/runbooks/*.md       this Contract's Runbooks
    <contracts-dir>/shared/runbooks/*.md     Shared knowledge, for every Contract

`load()` reads every Contract, decrypts its secrets with the `sops` binary and
reports every problem at once as `path: field: message`. Secret values never
appear in errors, logs or repr.
"""

import json
import os
import shutil
import subprocess
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    SecretStr,
    ValidationError,
    model_validator,
)

from aiops_agent.config import Settings

SECRETS_FILE = "secrets.sops.yaml"
SHARED = "shared"

# Becomes a URL path segment (/contracts/{id}/...), so a lowercase slug.
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", max_length=63)]


class Strict(BaseModel):
    # A typo must fail, not be ignored. Fields are added when a slice gives them behaviour.
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class Cluster(Strict):
    name: Slug
    namespaces: list[str] = Field(min_length=1)
    in_cluster: bool = False
    context: str | None = None
    kubeconfig_file: Path | None = None  # default: ~/.kube/config
    kubeconfig_secret: str | None = None
    # A kubeconfig credential plugin runs as a command on the Hub, next to every other
    # Contract's secrets. Refused unless set here, where review of the contracts repo sees it.
    allow_exec: bool = False

    @model_validator(mode="after")
    def _one_source(self) -> "Cluster":
        if (
            self.in_cluster
            + (self.kubeconfig_file is not None)
            + (self.kubeconfig_secret is not None)
            > 1
        ):
            raise ValueError("set only one of in_cluster, kubeconfig_file, kubeconfig_secret")
        if not self.in_cluster and not self.context:
            raise ValueError("context is required unless in_cluster (no silent default context)")
        return self


class Kubernetes(Strict):
    name: Literal["kubernetes"]
    enable_actions: bool = False
    max_replicas: int = Field(10, ge=1)


class Prometheus(Strict):
    name: Literal["prometheus"]
    url: str
    token_secret: str | None = None


class Runbooks(Strict):
    name: Literal["runbooks"]  # reads <contract dir>/runbooks


Integration = Annotated[Kubernetes | Prometheus | Runbooks, Field(discriminator="name")]


class Contract(Strict):
    id: Slug
    name: str
    clusters: list[Cluster] = []
    integrations: list[Integration] = Field(min_length=1)

    _dir: Path = PrivateAttr(default=Path())
    _secrets: dict[str, SecretStr] = PrivateAttr(default_factory=dict)
    _runbook_dirs: list[Path] = PrivateAttr(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> "Contract":
        groups: dict[str, list[str]] = {
            "cluster": [c.name for c in self.clusters],
            "integration": [i.name for i in self.integrations],
        }
        for kind, names in groups.items():
            dupes = sorted({n for n in names if names.count(n) > 1})
            if dupes:
                raise ValueError(f"duplicate {kind} names: {dupes}")
        has_k8s = any(i.name == "kubernetes" for i in self.integrations)
        if has_k8s != bool(self.clusters):
            raise ValueError("the kubernetes integration and clusters go together")
        return self

    @property
    def dir(self) -> Path:
        return self._dir

    @property
    def runbook_dirs(self) -> list[Path]:
        """Shared knowledge first, then the Contract's own: its Runbook wins on a name clash."""
        return self._runbook_dirs

    def secret(self, name: str) -> SecretStr:
        return self._secrets[name]

    def secret_refs(self) -> set[str]:
        """Every `*_secret` field, so a new integration's credentials are checked
        without being listed here."""
        return {
            value
            for item in (*self.clusters, *self.integrations)
            for field in type(item).model_fields
            if field.endswith("_secret") and (value := getattr(item, field)) is not None
        }


class ContractError(Exception):
    """Every problem found, one `path: field: message` line each."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


def load(directory: Path) -> dict[str, Contract]:
    if not directory.is_dir():
        raise ContractError([f"{directory}: not a directory"])
    contracts: dict[str, Contract] = {}
    owners: dict[str, list[str]] = defaultdict(list)  # age recipient -> Contract ids
    problems: list[str] = []
    for path in sorted(directory.glob("*/contract.yaml")):
        try:
            contract, recipients = _load_one(path)
        except ContractError as e:
            problems += e.problems
            continue
        contracts[contract.id] = contract
        for r in recipients:
            owners[r].append(contract.id)
    for recipient, ids in owners.items():
        if len(ids) > 1:
            problems.append(
                f"{directory}: {', '.join(ids)} share age recipient {recipient}; "
                "each Contract needs its own key"
            )
    if not contracts and not problems:
        problems.append(f"{directory}: no */contract.yaml found")
    if problems:
        raise ContractError(problems)
    return contracts


def _load_one(path: Path) -> tuple[Contract, set[str]]:
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise ContractError([f"{path}: invalid YAML: {e}"]) from None
    try:
        contract = Contract.model_validate(raw)
    except ValidationError as e:
        raise ContractError(_lines(str(path), e)) from None
    problems = []
    if contract.id != path.parent.name:
        problems.append(
            f"{path}: id: {contract.id!r} must match its directory {path.parent.name!r}"
        )
    if (path.parent / "secrets.yaml").exists():
        problems.append(
            f"{path.parent / 'secrets.yaml'}: plaintext secrets; encrypt as {SECRETS_FILE}"
        )
    secrets, recipients = {}, set()
    secrets_path = path.parent / SECRETS_FILE
    if secrets_path.exists():
        recipients = _recipients(secrets_path)
        secrets = _decrypt(secrets_path)
    for name in sorted(contract.secret_refs() - secrets.keys()):
        problems.append(f"{path}: secret {name!r} is not in {SECRETS_FILE}")
    for i, cluster in enumerate(contract.clusters):
        if cluster.kubeconfig_secret in secrets:
            kubeconfig = _yaml_or_none(secrets[cluster.kubeconfig_secret])
        elif cluster.kubeconfig_file and cluster.kubeconfig_file.expanduser().is_file():
            kubeconfig = read_kubeconfig(cluster.kubeconfig_file)
        else:
            continue  # the default kubeconfig is the Hub's, checked when it connects
        if kubeconfig is None:
            problems.append(f"{path}: clusters.{i}: kubeconfig is not valid YAML")
        elif refusal := refuse_plugin(cluster, kubeconfig):
            problems.append(f"{path}: clusters.{i}: {refusal}")
    if problems:
        raise ContractError(problems)
    contract._dir = path.parent
    contract._secrets = {k: SecretStr(v) for k, v in secrets.items()}
    contract._runbook_dirs = [path.parent.parent / SHARED / "runbooks", path.parent / "runbooks"]
    return contract, recipients


def _yaml_or_none(text: str) -> Any:
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None  # never echo the text: it is a credential


def read_kubeconfig(path: Path | None) -> dict[str, Any]:
    """The contexts and users the kubernetes client would see: `path`, or else
    KUBECONFIG / ~/.kube/config, merged first-wins like kubectl."""
    env = os.environ.get("KUBECONFIG", "~/.kube/config")
    paths = [path] if path else [Path(p) for p in env.split(os.pathsep) if p]
    merged: dict[str, Any] = {"contexts": [], "users": []}
    seen = set()
    for p in paths:
        p = p.expanduser()
        if not p.is_file():
            continue
        data = yaml.safe_load(p.read_text()) or {}
        for key in ("contexts", "users"):
            for entry in data.get(key) or []:
                if isinstance(entry, dict) and (key, entry.get("name")) not in seen:
                    seen.add((key, entry.get("name")))
                    merged[key].append(entry)
    return merged


def credential_plugin(kubeconfig: Any, context: str | None) -> str | None:
    """The command `context`'s user would run on the Hub to get credentials, if any:
    an exec plugin, or an auth-provider (gcp's can run a cmd-path)."""
    if not isinstance(kubeconfig, dict):
        return None

    def named(key: str, name: Any) -> dict[str, Any]:
        for entry in kubeconfig.get(key) or []:
            if isinstance(entry, dict) and entry.get("name") == name:
                inner = entry.get(key[:-1])  # contexts[].context, users[].user
                return inner if isinstance(inner, dict) else {}
        return {}

    user = named("users", named("contexts", context).get("user"))
    if "exec" in user:
        return f"exec plugin {(user['exec'] or {}).get('command')!r}"
    if "auth-provider" in user:
        return f"auth-provider {(user['auth-provider'] or {}).get('name')!r}"
    return None


def refuse_plugin(cluster: Cluster, kubeconfig: Any) -> str | None:
    """Why this cluster's kubeconfig may not be used, or None."""
    plugin = None if cluster.allow_exec else credential_plugin(kubeconfig, cluster.context)
    if plugin is None:
        return None
    return (
        f"cluster {cluster.name!r}: its kubeconfig runs {plugin} on the Hub; "
        "set allow_exec: true on the cluster to permit it"
    )


def _lines(where: str, e: ValidationError) -> list[str]:
    # loc and msg only: pydantic's `input` could echo a value.
    return [
        f"{where}: {'.'.join(map(str, err['loc'])) or '<root>'}: {err['msg']}" for err in e.errors()
    ]


def build(
    data: dict[str, Any],
    *,
    secrets: dict[str, SecretStr] | None = None,
    runbook_dirs: Sequence[Path] = (),
) -> Contract:
    """A Contract from data already in memory (tests, evals, the env settings)."""
    contract = Contract.model_validate(data)
    contract._secrets = dict(secrets or {})
    contract._runbook_dirs = list(runbook_dirs)
    return contract


def from_settings(settings: Settings) -> Contract:
    """ponytail: the AIOPS_* variables as one Contract, until slice 0.3 loads a
    contracts directory. Never calls sops, which the image doesn't ship yet."""
    cluster = {
        "name": "default",
        "namespaces": settings.namespaces,
        "in_cluster": settings.in_cluster,
        "context": settings.kube_context,
        "kubeconfig_file": settings.kubeconfig,
    }
    integrations: list[dict[str, Any]] = [
        {
            "name": "kubernetes",
            "enable_actions": settings.enable_actions,
            "max_replicas": settings.max_replicas,
        }
    ]
    secrets = {}
    if settings.prometheus_url:
        prom = {"name": "prometheus", "url": settings.prometheus_url}
        if settings.prometheus_token:
            prom["token_secret"] = "prometheus-token"  # noqa: S105 - a name, not a value
            secrets["prometheus-token"] = settings.prometheus_token
        integrations.append(prom)
    if settings.runbooks_dir.is_dir():
        integrations.append({"name": "runbooks"})
    data = {
        "id": "default",
        "name": "AIOPS_* settings",
        "clusters": [cluster],
        "integrations": integrations,
    }
    try:
        return build(data, secrets=secrets, runbook_dirs=[settings.runbooks_dir])
    except ValidationError as e:
        hint = "set AIOPS_NAMESPACES, and AIOPS_KUBE_CONTEXT or AIOPS_IN_CLUSTER"
        raise RuntimeError("; ".join(_lines("AIOPS_* settings", e)) + f" ({hint})") from None


def _recipients(path: Path) -> set[str]:
    """Read from the file's sops metadata: no key needed. Refuses unencrypted files."""
    try:
        meta = (yaml.safe_load(path.read_text()) or {}).get("sops")
    except (yaml.YAMLError, AttributeError):
        meta = None
    if not isinstance(meta, dict):
        raise ContractError([f"{path}: not encrypted with sops; refusing to read it"])
    return {a["recipient"] for a in meta.get("age") or [] if "recipient" in a}


def _decrypt(path: Path) -> dict[str, str]:
    sops = shutil.which("sops")
    if sops is None:
        raise ContractError([f"{path}: sops is not on PATH (brew install sops)"])
    proc = subprocess.run(  # noqa: S603 - fixed binary and arguments, no shell
        [sops, "--decrypt", "--output-type", "json", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        reason = (proc.stderr.strip().splitlines() or ["unknown error"])[0]
        raise ContractError([f"{path}: sops could not decrypt: {reason}"])
    data: Any = json.loads(proc.stdout)
    if not isinstance(data, dict):
        raise ContractError([f"{path}: must be a map of secret name to value"])
    bad = sorted(str(k) for k, v in data.items() if not isinstance(v, str))
    if bad:
        # Name the keys, never the values.
        raise ContractError([f"{path}: {k}: value must be a string" for k in bad])
    return data
