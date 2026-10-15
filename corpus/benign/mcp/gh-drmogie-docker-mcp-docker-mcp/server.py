"""Docker MCP tool.

Lets Claude look at and manage Docker (containers, images, volumes, networks,
and Compose stacks) on one or more Docker hosts.

How it connects: it runs the `docker` command. For a remote host it runs it
over SSH with a key (never a password). For the machine it runs on, it runs
`docker` directly. Nothing is installed on the Docker host.

Settings come from environment variables only.

  DOCKER_MCP_HOSTS      names of your hosts, comma separated, for example "themedia"
                        (if left empty, one host called "local" is used)

For each host name (letters, digits; other characters become "_", upper case):

  DOCKER_MCP_<NAME>_SSH         user@address for SSH. Leave empty to use local docker.
  DOCKER_MCP_<NAME>_SSH_PORT    SSH port (default 22)
  DOCKER_MCP_<NAME>_SSH_KEY     path to the private key file to use
  DOCKER_MCP_<NAME>_SUDO        "true" to run docker with `sudo -n` (needs passwordless sudo)
  DOCKER_MCP_<NAME>_STACKS      folder with one sub folder per Compose stack (default /opt/stacks)

Other settings:

  DOCKER_MCP_READ_ONLY  "true" to refuse every change
  DOCKER_MCP_TIMEOUT    seconds to wait for a normal command (default 60)
  DOCKER_MCP_LONG_TIMEOUT  seconds for pull, up and update (default 900)
  DOCKER_MCP_SSH_BIN    ssh program to use (default "ssh")
  DOCKER_MCP_DOCKER_BIN docker program for local use (default "docker")

Safety tiers:
  read         runs right away
  change       needs confirm=true (ask the user first)
  destructive  needs confirm=true AND confirm_phrase "<host> <what>"

Secrets (passwords, tokens, keys) are hidden in everything shown to Claude.
The .env files are never read.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import functools
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

__version__ = "2026.10.12.01"

mcp = FastMCP("docker")

# ---------------------------------------------------------------------------
# Names and checks
# ---------------------------------------------------------------------------
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@-]{0,255}$")
SINCE_RE = re.compile(r"^(\d{1,6}[smhd]|\d{4}-\d{2}-\d{2}(T[0-9:.+Z-]+)?)$")
COMPOSE_NAMES = ("compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml")

# A name with one of these words in it holds a secret. Its value is hidden.
SECRET_WORDS = (
    "PASS", "SECRET", "TOKEN", "KEY", "CRED", "AUTH", "CLAIM", "LICENSE",
    "PRIVATE", "COOKIE", "SESSION", "USER",
)
HIDDEN = "***hidden***"

_LINE = re.compile(
    r"^(?P<pre>\s*(?:-\s*)?[\"']?)(?P<key>[A-Za-z0-9_.-]+)(?P<mid>[\"']?\s*[:=]\s*)(?P<val>\S.*)$"
)
_INLINE = re.compile(
    r"(?i)\b([A-Za-z0-9_]*(?:pass|passwd|password|secret|token|apikey|api_key)[A-Za-z0-9_]*)=(\S+)"
)


_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{6,}")
_AUTHHDR = re.compile(r"(?i)\b(authorization:\s*)\S.*$")


def _secret_name(name: str) -> bool:
    up = name.upper()
    return any(w in up for w in SECRET_WORDS)


def _redact_text(text: str) -> str:
    """Hide secret values in text (compose files, logs). Best effort."""
    out = []
    for line in text.splitlines():
        m = _LINE.match(line)
        if m and _secret_name(m.group("key")):
            val = m.group("val").strip()
            if not val.startswith("${"):  # a reference like ${PIA_PASSWORD} is fine to show
                line = f"{m.group('pre')}{m.group('key')}{m.group('mid')}{HIDDEN}"
        line = _INLINE.sub(lambda mm: f"{mm.group(1)}={HIDDEN}", line)
        line = _AUTHHDR.sub(lambda mm: mm.group(1) + HIDDEN, line)
        line = _BEARER.sub(lambda mm: f"{mm.group(1)} {HIDDEN}", line)
        out.append(line)
    return "\n".join(out)


def _redact_env(env: list[str] | None) -> list[str]:
    out = []
    for item in env or []:
        key, sep, val = str(item).partition("=")
        out.append(f"{key}={HIDDEN}" if sep and _secret_name(key) and val else str(item))
    return out


# ---------------------------------------------------------------------------
# Hosts
# ---------------------------------------------------------------------------
def _env_key(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", name.upper())


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


def _hosts() -> dict[str, dict[str, Any]]:
    names = [n.strip() for n in os.environ.get("DOCKER_MCP_HOSTS", "").split(",") if n.strip()]
    if not names:
        names = ["local"]
    hosts: dict[str, dict[str, Any]] = {}
    for n in names:
        p = f"DOCKER_MCP_{_env_key(n)}_"
        hosts[n] = {
            "name": n,
            "ssh": os.environ.get(p + "SSH", "").strip(),
            "port": os.environ.get(p + "SSH_PORT", "").strip(),
            "key": os.environ.get(p + "SSH_KEY", "").strip(),
            "sudo": _truthy(os.environ.get(p + "SUDO")),
            "stacks": (os.environ.get(p + "STACKS", "").strip() or "/opt/stacks").rstrip("/") or "/",
        }
    return hosts


def _pick(host: str) -> tuple[dict[str, Any] | None, str]:
    hs = _hosts()
    if not host:
        if len(hs) == 1:
            return next(iter(hs.values())), ""
        return None, "Which host? Choose one of: " + ", ".join(hs)
    if host not in hs:
        return None, f"Unknown host '{host}'. Choose one of: " + ", ".join(hs)
    return hs[host], ""


def _timeout(long: bool = False) -> int:
    if long:
        return int(os.environ.get("DOCKER_MCP_LONG_TIMEOUT", "900"))
    return int(os.environ.get("DOCKER_MCP_TIMEOUT", "60"))


def _ssh_cmd(h: dict[str, Any], argv: list[str], cwd: str | None = None) -> list[str]:
    """Build the ssh command that runs argv on the remote host. Every part is quoted."""
    if h["ssh"].startswith("-"):
        raise ValueError("SSH target must not start with '-'")
    remote = " ".join(shlex.quote(a) for a in argv)
    if cwd:
        remote = f"cd {shlex.quote(cwd)} && {remote}"
    cmd = [os.environ.get("DOCKER_MCP_SSH_BIN", "ssh"),
           "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
    if h["port"]:
        cmd += ["-p", h["port"]]
    if h["key"]:
        cmd += ["-i", h["key"], "-o", "IdentitiesOnly=yes"]
    return cmd + ["--", h["ssh"], remote]


def _exec(h: dict[str, Any], argv: list[str], cwd: str | None = None,
          timeout: int | None = None) -> tuple[int, str, str]:
    """Run a command on the host. Returns (exit code, stdout, stderr)."""
    argv = list(argv)
    if h["sudo"] and argv and argv[0] == "docker":
        argv = ["sudo", "-n"] + argv
    try:
        if h["ssh"]:
            cmd, kw = _ssh_cmd(h, argv, cwd), {}
        else:
            if "docker" in argv:
                i = argv.index("docker")
                argv[i] = os.environ.get("DOCKER_MCP_DOCKER_BIN", "docker")
            cmd, kw = argv, {"cwd": cwd}
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout or _timeout(),
                           stdin=subprocess.DEVNULL, errors="replace", **kw)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "Timed out waiting for the command."
    except (OSError, ValueError) as e:
        return 127, "", str(e)


def _docker(h: dict[str, Any], args: list[str], cwd: str | None = None,
            long: bool = False) -> tuple[int, str, str]:
    return _exec(h, ["docker"] + args, cwd=cwd, timeout=_timeout(long))


def _fail(rc: int, err: str, out: str = "") -> str:
    text = (err or out or "no message").strip()
    hint = ""
    if "permission denied" in text.lower() and "docker.sock" in text.lower():
        hint = " Hint: add the user to the docker group, or set DOCKER_MCP_<NAME>_SUDO=true."
    if "a password is required" in text.lower():
        hint = " Hint: sudo needs a password. Use the docker group instead of sudo."
    if "permission denied (publickey" in text.lower():
        hint = " Hint: SSH key was not accepted. Check DOCKER_MCP_<NAME>_SSH and _SSH_KEY."
    return f"ERROR (exit {rc}): {_redact_text(text)[:1500]}{hint}"


def _json_lines(out: str) -> list[Any]:
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def _show(obj: Any, limit: int = 60000) -> str:
    text = json.dumps(obj, indent=1, ensure_ascii=False, default=str)
    if len(text) > limit:
        text = text[:limit] + f"\n... cut at {limit} characters"
    return text


def _safe(fn: Callable[..., str]) -> Callable[..., str]:
    @functools.wraps(fn)
    def wrapper(*a: Any, **k: Any) -> str:
        try:
            return fn(*a, **k)
        except Exception as e:  # never crash the tool; tell Claude what went wrong
            return f"ERROR: {type(e).__name__}: {_redact_text(str(e))[:500]}"
    return wrapper


# ---------------------------------------------------------------------------
# Safety gate
# ---------------------------------------------------------------------------
def _gate(h: dict[str, Any], tier: str, what: str, details: str,
          confirm: bool, phrase: str) -> str | None:
    """Return a message if the action must not run yet, else None."""
    if tier == "read":
        return None
    if _truthy(os.environ.get("DOCKER_MCP_READ_ONLY")):
        return "NOT RUN. Read-only mode is on (DOCKER_MCP_READ_ONLY). No changes are allowed."
    need = f"{h['name']} {what}"
    if not confirm:
        extra = f' and confirm_phrase "{need}"' if tier == "destructive" else ""
        return (
            f"NOT RUN. This makes a change ({tier}).\n"
            f"Action: {need}\nDetails: {details}\n"
            "Tell the user exactly what will change and ask for a clear yes. "
            f"Only after they say yes, call again with confirm=true{extra}."
        )
    if tier == "destructive" and phrase.strip() != need:
        return (
            f"NOT RUN. This is destructive. confirm_phrase must be exactly: {need}\n"
            "Ask the user to confirm, then repeat the call with that phrase."
        )
    return None


def _check_name(kind: str, value: str, image: bool = False) -> str | None:
    rx = IMAGE_RE if image else NAME_RE
    if not value or not rx.match(value) or ".." in value:
        return f"Bad {kind} name: {value!r}"
    return None


# ---------------------------------------------------------------------------
# Stacks (Compose projects, one folder each)
# ---------------------------------------------------------------------------
def _find_stacks(h: dict[str, Any]) -> tuple[dict[str, str] | None, str]:
    """Return {stack name: compose file path} or (None, error)."""
    root = h["stacks"]
    found: dict[str, str] = {}
    if h["ssh"]:
        argv = ["find", root, "-maxdepth", "2", "-type", "f", "("]
        for i, n in enumerate(COMPOSE_NAMES):
            argv += (["-o"] if i else []) + ["-name", n]
        argv += [")"]
        rc, out, err = _exec(h, argv)
        if rc != 0 and not out.strip():
            return None, _fail(rc, err)
        paths = [p.strip() for p in out.splitlines() if p.strip()]
    else:
        paths = []
        if os.path.isdir(root):
            for d in sorted(os.listdir(root)):
                for n in COMPOSE_NAMES:
                    p = os.path.join(root, d, n)
                    if os.path.isfile(p):
                        paths.append(p.replace("\\", "/"))
                        break
    for p in sorted(paths):
        parts = p.rstrip("/").split("/")
        if len(parts) >= 2 and NAME_RE.match(parts[-2]) and parts[-2] not in found:
            found[parts[-2]] = p
    return found, ""


def _stack(h: dict[str, Any], name: str) -> tuple[tuple[str, str] | None, str]:
    """Return ((folder, compose file), '') or (None, error)."""
    bad = _check_name("stack", name)
    if bad:
        return None, bad
    stacks, err = _find_stacks(h)
    if stacks is None:
        return None, err
    if name not in stacks:
        return None, f"No stack '{name}' under {h['stacks']}. Found: " + (", ".join(stacks) or "none")
    path = stacks[name]
    return (path.rsplit("/", 1)[0], path), ""


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------
@mcp.tool()
@_safe
def docker_hosts() -> str:
    """List the Docker hosts this tool knows and test the connection to each."""
    rows = []
    for h in _hosts().values():
        rc, out, err = _docker(h, ["version", "--format", "{{.Server.Version}}"])
        row: dict[str, Any] = {
            "host": h["name"], "via": f"ssh {h['ssh']}" if h["ssh"] else "local docker",
            "sudo": h["sudo"], "stacks_folder": h["stacks"],
        }
        if rc == 0:
            row["docker"] = out.strip()
            rc2, out2, _ = _docker(h, ["compose", "version", "--short"])
            row["compose"] = out2.strip() if rc2 == 0 else "not found"
        else:
            row["error"] = _fail(rc, err)
        rows.append(row)
    return _show(rows)


@mcp.tool()
@_safe
def docker_ps(host: str = "", all: bool = True, name_contains: str = "") -> str:
    """List containers: name, image, state, status, ports, networks.

    all=true includes stopped containers. name_contains filters by name.
    """
    h, err = _pick(host)
    if not h:
        return err
    args = ["ps", "--format", "{{json .}}"] + (["-a"] if all else [])
    rc, out, e = _docker(h, args)
    if rc != 0:
        return _fail(rc, e)
    rows = []
    for r in _json_lines(out):
        if name_contains and name_contains.lower() not in str(r.get("Names", "")).lower():
            continue
        rows.append({
            "name": r.get("Names"), "image": r.get("Image"), "state": r.get("State"),
            "status": r.get("Status"), "ports": r.get("Ports"), "networks": r.get("Networks"),
        })
    return _show(rows) if rows else "No containers."


@mcp.tool()
@_safe
def docker_logs(container: str, host: str = "", tail: int = 100, since: str = "") -> str:
    """Show the last lines of a container's log. since like 10m, 2h, or 2026-10-11.

    Secrets that look like password or token values are hidden.
    """
    h, err = _pick(host)
    if not h:
        return err
    bad = _check_name("container", container)
    if bad:
        return bad
    args = ["logs", "--timestamps", "--tail", str(max(1, min(int(tail), 1000)))]
    if since:
        if not SINCE_RE.match(since):
            return f"Bad since value: {since!r}. Use 10m, 2h, 1d, or 2026-10-11."
        args += ["--since", since]
    rc, out, e = _docker(h, args + [container])
    if rc != 0:
        return _fail(rc, e)
    text = _redact_text((out + e).strip())
    return text[-30000:] if text else "(no log lines)"


def _inspect_container(d: dict[str, Any]) -> dict[str, Any]:
    cfg, st, hc = d.get("Config") or {}, d.get("State") or {}, d.get("HostConfig") or {}
    nets = {k: v.get("IPAddress") for k, v in ((d.get("NetworkSettings") or {}).get("Networks") or {}).items()}
    labels = cfg.get("Labels") or {}
    return {
        "name": str(d.get("Name", "")).lstrip("/"),
        "image": cfg.get("Image"),
        "state": {k: st.get(k) for k in ("Status", "Running", "ExitCode", "StartedAt", "FinishedAt", "OOMKilled")},
        "health": (st.get("Health") or {}).get("Status"),
        "restart_count": d.get("RestartCount"),
        "restart_policy": (hc.get("RestartPolicy") or {}).get("Name"),
        "network_mode": hc.get("NetworkMode"),
        "networks": nets,
        "ports": hc.get("PortBindings"),
        "user": cfg.get("User"),
        "cmd": [_redact_text(str(c)) for c in (cfg.get("Cmd") or [])],
        "env": _redact_env(cfg.get("Env")),
        "mounts": [
            {"type": m.get("Type"), "source": m.get("Name") or m.get("Source"),
             "target": m.get("Destination"), "rw": m.get("RW")}
            for m in d.get("Mounts") or []
        ],
        "compose": {k.split(".")[-1]: v for k, v in labels.items() if k.startswith("com.docker.compose.project") or k == "com.docker.compose.service"},
    }


@mcp.tool()
@_safe
def docker_inspect(name: str, kind: str = "container", host: str = "") -> str:
    """Show details of a container, volume, network or image (kind).

    For a volume this shows its driver and options, such as the NFS address.
    Secret values in environment variables are hidden.
    """
    h, err = _pick(host)
    if not h:
        return err
    if kind not in ("container", "volume", "network", "image"):
        return "kind must be container, volume, network or image."
    bad = _check_name(kind, name, image=(kind == "image"))
    if bad:
        return bad
    if kind in ("container", "image"):
        args = ["inspect", "--type", kind, name]
    else:
        args = [kind, "inspect", name]
    rc, out, e = _docker(h, args)
    if rc != 0:
        return _fail(rc, e)
    try:
        data = json.loads(out)[0]
    except (ValueError, IndexError):
        return "Could not read the answer from docker."
    if kind == "container":
        return _show(_inspect_container(data))
    if kind == "image":
        cfg = data.get("Config") or {}
        return _show({
            "id": data.get("Id"), "tags": data.get("RepoTags"), "created": data.get("Created"),
            "size": data.get("Size"), "env": _redact_env(cfg.get("Env")),
            "user": cfg.get("User"), "ports": list((cfg.get("ExposedPorts") or {})),
        })
    if kind == "volume":
        return _show({k: data.get(k) for k in ("Name", "Driver", "Options", "Mountpoint", "Labels", "CreatedAt")})
    return _show({k: data.get(k) for k in ("Name", "Driver", "Scope", "Options", "IPAM", "Labels")}
                 | {"containers": {v.get("Name"): v.get("IPv4Address") for v in (data.get("Containers") or {}).values()}})


@mcp.tool()
@_safe
def docker_stats(host: str = "") -> str:
    """Show CPU, memory and network use of running containers right now."""
    h, err = _pick(host)
    if not h:
        return err
    rc, out, e = _docker(h, ["stats", "--no-stream", "--format", "{{json .}}"])
    if rc != 0:
        return _fail(rc, e)
    rows = [{"name": r.get("Name"), "cpu": r.get("CPUPerc"), "memory": r.get("MemUsage"),
             "mem_percent": r.get("MemPerc"), "network": r.get("NetIO"), "block_io": r.get("BlockIO")}
            for r in _json_lines(out)]
    return _show(rows) if rows else "No running containers."


@mcp.tool()
@_safe
def docker_images(host: str = "") -> str:
    """List images: name, tag, size, age."""
    h, err = _pick(host)
    if not h:
        return err
    rc, out, e = _docker(h, ["images", "--format", "{{json .}}"])
    if rc != 0:
        return _fail(rc, e)
    rows = [{"image": f"{r.get('Repository')}:{r.get('Tag')}", "id": r.get("ID"),
             "size": r.get("Size"), "created": r.get("CreatedSince")} for r in _json_lines(out)]
    return _show(rows) if rows else "No images."


@mcp.tool()
@_safe
def docker_volumes(host: str = "") -> str:
    """List volumes: name and driver."""
    h, err = _pick(host)
    if not h:
        return err
    rc, out, e = _docker(h, ["volume", "ls", "--format", "{{json .}}"])
    if rc != 0:
        return _fail(rc, e)
    rows = [{"name": r.get("Name"), "driver": r.get("Driver")} for r in _json_lines(out)]
    return _show(rows) if rows else "No volumes."


@mcp.tool()
@_safe
def docker_networks(host: str = "") -> str:
    """List networks: name, driver, scope."""
    h, err = _pick(host)
    if not h:
        return err
    rc, out, e = _docker(h, ["network", "ls", "--format", "{{json .}}"])
    if rc != 0:
        return _fail(rc, e)
    rows = [{"name": r.get("Name"), "driver": r.get("Driver"), "scope": r.get("Scope")} for r in _json_lines(out)]
    return _show(rows) if rows else "No networks."


@mcp.tool()
@_safe
def docker_disk_usage(host: str = "") -> str:
    """Show how much disk space images, containers, volumes and build cache use."""
    h, err = _pick(host)
    if not h:
        return err
    rc, out, e = _docker(h, ["system", "df", "--format", "{{json .}}"])
    if rc != 0:
        return _fail(rc, e)
    return _show(_json_lines(out))


@mcp.tool()
@_safe
def docker_stacks(host: str = "") -> str:
    """List Compose stacks (one folder each under the stacks folder) and whether they are running."""
    h, err = _pick(host)
    if not h:
        return err
    stacks, e = _find_stacks(h)
    if stacks is None:
        return e
    running: list[dict[str, Any]] = []
    rc, out, _ = _docker(h, ["compose", "ls", "--all", "--format", "json"])
    if rc == 0:
        try:
            running = json.loads(out) if out.strip() else []
        except ValueError:
            running = []
    rows = []
    for name, path in sorted(stacks.items()):
        match = next((p for p in running if path in str(p.get("ConfigFiles", ""))), None)
        rows.append({"stack": name, "file": path, "status": match.get("Status") if match else "not created yet"})
    return _show(rows) if rows else f"No stacks found under {h['stacks']}."


@mcp.tool()
@_safe
def docker_stack_status(stack: str, host: str = "") -> str:
    """Show the containers of one stack and their state."""
    h, err = _pick(host)
    if not h:
        return err
    st, e = _stack(h, stack)
    if not st:
        return e
    rc, out, er = _docker(h, ["compose", "ps", "--all", "--format", "json"], cwd=st[0])
    if rc != 0:
        return _fail(rc, er)
    rows = []
    for line in out.strip().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        for x in (r if isinstance(r, list) else [r]):
            rows.append({"service": x.get("Service"), "name": x.get("Name"), "image": x.get("Image"),
                         "state": x.get("State"), "health": x.get("Health"), "status": x.get("Status"),
                         "ports": x.get("Publishers") and [f"{p.get('PublishedPort')}->{p.get('TargetPort')}" for p in x["Publishers"] if p.get("PublishedPort")]})
    return _show(rows) if rows else "No containers created for this stack."


@mcp.tool()
@_safe
def docker_stack_file(stack: str, host: str = "") -> str:
    """Show the compose file of a stack. Secret values are hidden. The .env file is never shown."""
    h, err = _pick(host)
    if not h:
        return err
    st, e = _stack(h, stack)
    if not st:
        return e
    if h["ssh"]:
        rc, out, er = _exec(h, ["cat", "--", st[1]])
        if rc != 0:
            return _fail(rc, er)
    else:
        with open(st[1], encoding="utf-8", errors="replace") as f:
            out = f.read()
    return _redact_text(out)[:60000]


@mcp.tool()
@_safe
def docker_stack_config(stack: str, host: str = "") -> str:
    """Check a stack and show the final compose file with all variables filled in.

    Good for finding a missing or wrong value in the .env file. Secret values are hidden.
    """
    h, err = _pick(host)
    if not h:
        return err
    st, e = _stack(h, stack)
    if not st:
        return e
    rc, out, er = _docker(h, ["compose", "config"], cwd=st[0])
    if rc != 0:
        return _fail(rc, er)
    return _redact_text(out)[:60000]


# ---------------------------------------------------------------------------
# Change tools
# ---------------------------------------------------------------------------
@mcp.tool()
@_safe
def docker_container_action(container: str, action: str, host: str = "",
                            confirm: bool = False, confirm_phrase: str = "") -> str:
    """Start, stop, restart, pause or unpause one container. Needs confirm=true."""
    h, err = _pick(host)
    if not h:
        return err
    if action not in ("start", "stop", "restart", "pause", "unpause"):
        return "action must be start, stop, restart, pause or unpause."
    bad = _check_name("container", container)
    if bad:
        return bad
    stop = _gate(h, "change", f"{action} container {container}", f"docker {action} {container}", confirm, confirm_phrase)
    if stop:
        return stop
    rc, out, e = _docker(h, [action, container], long=True)
    return _fail(rc, e, out) if rc else f"Done: {action} {container}"


@mcp.tool()
@_safe
def docker_stack_action(stack: str, action: str, host: str = "",
                        confirm: bool = False, confirm_phrase: str = "") -> str:
    """Run a Compose action on one stack.

    action: up (create/start, same as docker compose up -d), pull (get new images),
    update (pull then up), start, stop, restart.
    These need confirm=true.
    down (removes the containers and network, keeps volumes) and
    down_volumes (also removes the stack's volumes) are destructive and also
    need confirm_phrase "<host> stack <stack> down" (or down_volumes).
    """
    h, err = _pick(host)
    if not h:
        return err
    plans = {
        "up": [["compose", "up", "-d"]],
        "pull": [["compose", "pull"]],
        "update": [["compose", "pull"], ["compose", "up", "-d"]],
        "start": [["compose", "start"]],
        "stop": [["compose", "stop"]],
        "restart": [["compose", "restart"]],
        "down": [["compose", "down"]],
        "down_volumes": [["compose", "down", "--volumes"]],
    }
    if action not in plans:
        return "action must be one of: " + ", ".join(plans)
    st, e = _stack(h, stack)
    if not st:
        return e
    tier = "destructive" if action.startswith("down") else "change"
    stop = _gate(h, tier, f"stack {stack} {action}", " then ".join("docker " + " ".join(p) for p in plans[action]), confirm, confirm_phrase)
    if stop:
        return stop
    log = []
    for cmd in plans[action]:
        rc, out, er = _docker(h, cmd, cwd=st[0], long=True)
        text = _redact_text((out + er).strip())[-3000:]
        if rc:
            return _fail(rc, er, out)
        log.append(text)
    return f"Done: {action} {stack}\n" + "\n".join(x for x in log if x)


@mcp.tool()
@_safe
def docker_pull_image(image: str, host: str = "", confirm: bool = False) -> str:
    """Download an image, for example ghcr.io/seerr-team/seerr:latest. Needs confirm=true."""
    h, err = _pick(host)
    if not h:
        return err
    bad = _check_name("image", image, image=True)
    if bad:
        return bad
    stop = _gate(h, "change", f"pull image {image}", f"docker pull {image}", confirm, "")
    if stop:
        return stop
    rc, out, e = _docker(h, ["pull", image], long=True)
    return _fail(rc, e, out) if rc else f"Done: pulled {image}\n{out.strip()[-500:]}"


# ---------------------------------------------------------------------------
# Destructive tools
# ---------------------------------------------------------------------------
@mcp.tool()
@_safe
def docker_remove(kind: str, name: str, host: str = "",
                  confirm: bool = False, confirm_phrase: str = "") -> str:
    """Delete one container, image, volume or network (kind).

    Destructive. Needs confirm=true and confirm_phrase "<host> remove <kind> <name>".
    A running container is not removed. Stop it first. Removing a volume
    deletes the data inside it. A volume with an NFS setting only holds the
    setting, not the files on the NAS.
    """
    h, err = _pick(host)
    if not h:
        return err
    cmds = {"container": ["rm"], "image": ["rmi"], "volume": ["volume", "rm"], "network": ["network", "rm"]}
    if kind not in cmds:
        return "kind must be container, image, volume or network."
    bad = _check_name(kind, name, image=(kind == "image"))
    if bad:
        return bad
    stop = _gate(h, "destructive", f"remove {kind} {name}", f"docker {' '.join(cmds[kind])} {name}", confirm, confirm_phrase)
    if stop:
        return stop
    rc, out, e = _docker(h, cmds[kind] + [name])
    return _fail(rc, e, out) if rc else f"Done: removed {kind} {name}"


@mcp.tool()
@_safe
def docker_prune(what: str, host: str = "", confirm: bool = False, confirm_phrase: str = "") -> str:
    """Clean up unused things. what: containers (stopped), images (unused, untagged only),
    networks (unused), volumes (not used by any container), builder (build cache).

    Destructive. Needs confirm=true and confirm_phrase "<host> prune <what>".
    """
    h, err = _pick(host)
    if not h:
        return err
    if what not in ("containers", "images", "networks", "volumes", "builder"):
        return "what must be containers, images, networks, volumes or builder."
    sub = {"containers": "container", "images": "image", "networks": "network", "volumes": "volume", "builder": "builder"}[what]
    stop = _gate(h, "destructive", f"prune {what}", f"docker {sub} prune -f", confirm, confirm_phrase)
    if stop:
        return stop
    rc, out, e = _docker(h, [sub, "prune", "-f"])
    return _fail(rc, e, out) if rc else f"Done: prune {what}\n{out.strip()[-1000:]}"


@mcp.tool()
@_safe
def docker_exec(container: str, command: str, host: str = "",
                confirm: bool = False, confirm_phrase: str = "") -> str:
    """Run one command inside a running container (no terminal, no input).

    Destructive, because the command can do anything inside the container.
    Needs confirm=true and confirm_phrase "<host> exec <container>".
    command is split like a shell would, but no shell is used (no pipes).
    """
    h, err = _pick(host)
    if not h:
        return err
    bad = _check_name("container", container)
    if bad:
        return bad
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return f"Bad command: {e}"
    if not parts:
        return "command is empty."
    stop = _gate(h, "destructive", f"exec {container}", f"{command}", confirm, confirm_phrase)
    if stop:
        return stop
    rc, out, e = _docker(h, ["exec", container] + parts)
    text = _redact_text((out + e).strip())[-8000:]
    return f"ERROR (exit {rc}): {text}" if rc else (text or "(no output)")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
