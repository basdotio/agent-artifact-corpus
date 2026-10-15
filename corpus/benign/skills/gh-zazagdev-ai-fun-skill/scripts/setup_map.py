"""Draw your Claude Code setup as one 3D page: read ~/.claude and every project Claude
Code has been opened in, then write setup-map.html with the setup's shape baked in.

Reads names, kinds, one-line frontmatter descriptions and counts only. Never copies
settings values, env, commands, URLs or file contents beyond a frontmatter description.
Sends nothing anywhere. Writes one HTML file.

Usage:
  python setup_map.py [PROJECTS_DIR] [--out FILE] [--open] [--projects-json FILE]

Projects are every folder listed in ~/.claude.json (where Claude Code was opened),
skipping folders that are gone and git worktrees. A folder inside another project is
part of it, unless it has a .claude folder of its own.

PROJECTS_DIR  optional: a folder to look for more projects in, and its subfolders
              (3 levels deep).
--out         where to write the page. Default: ~/setup-map/setup-map.html
--open        open the page in the default browser afterwards.
--projects-json  a JSON file listing more projects, read if it is there:
                 {"projects": [{"name": ..., "path": ...}], "scanRoots": [folder, ...]}
                 Every folder in a scan root counts as a project.
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys
import tempfile
import webbrowser
from pathlib import Path

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "map.tpl.html")
DESC_MAX = 2000  # full descriptions; the page folds long ones behind Read more
DEPTH = 3
SCRIPT = re.compile(r"[\w\-.]+\.(?:py|sh|js|mjs|cjs|ts|ps1|cmd|bat)")
SKIP = {"node_modules", "$recycle.bin", "system volume information", "worktrees", "dist", "build",
        "venv", "__pycache__", "library", "appdata", "applications", "program files", "program files (x86)", "windows"}
sources, unread = {}, []


def frontmatter(path):
    try:
        text = open(path, encoding="utf-8", errors="replace").read(4000)
    except OSError:
        return {}
    m = re.match(r"﻿?---\s*\n(.*?)\n---", text, re.S)
    out = {}
    if m:
        key = None
        for line in m.group(1).splitlines():
            if line.startswith((" ", "\t")) and key:
                # continuation of a folded (>) or literal (|) value
                out[key] = (out[key] + " " + line.strip()).strip()
                continue
            k, _, v = line.partition(":")
            if not v:
                key = None
                continue
            key, v = k.strip(), v.strip().strip('"')
            out[key] = "" if v in (">", "|", ">-", "|-") else v
    return out


def short(text):
    text = text or ""
    return text if len(text) <= DESC_MAX else text[: DESC_MAX - 1].rstrip() + "…"


def load_json(path, label=None):
    try:
        return json.load(open(path, encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        unread.append(f"{label or path}: {type(e).__name__}")
        return {}


def real(p):
    try:
        return os.path.realpath(p).replace("\\", "/").rstrip("/").lower()
    except OSError:
        return p.lower()


def slug(path):
    """The folder name Claude Code gives a project under ~/.claude/projects."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(path))


def md_items(folder, desc=None):
    return [{"name": os.path.basename(p)[:-3], "desc": short(frontmatter(p).get("description") or desc)}
            for p in sorted(glob.glob(os.path.join(folder, "*.md")))]


def hooks_from(cfg, origin):
    out = []
    for event, groups in (cfg.get("hooks") or {}).items():
        for g in groups or []:
            for h in g.get("hooks", []):
                names = SCRIPT.findall(h.get("command", "") or "")
                out.append({"name": names[-1] if names else f"inline {event} hook",
                            "desc": f"{origin}, runs on {event}", "event": event})
    return out


def merge(items):
    """One node per name; where it comes from is joined into its description."""
    out = {}
    for i in items:
        if i["name"] in out:
            if i["desc"] not in out[i["name"]]["desc"]:
                out[i["name"]]["desc"] += "; " + i["desc"]
            out[i["name"]]["count"] = out[i["name"]].get("count", 1) + i.get("count", 1)
        else:
            out[i["name"]] = dict(i)
    return list(out.values())


def looks_like_project(path):
    return any(os.path.exists(os.path.join(path, m)) for m in (".git", ".claude", "CLAUDE.md", ".mcp.json"))


def nested_name(parent, path):
    """A project inside another project, named by where it sits in it."""
    rel = os.path.relpath(os.path.realpath(path), os.path.realpath(parent["path"]))
    return parent["name"] + "/" + rel.replace(os.sep, "/")


def read_history():
    """One entry per folder under ~/.claude/projects: the working folder its sessions ran in,
    how many sessions there are and when the newest one was last written. Takes only the
    `cwd` field of a session's first lines and file times; never reads what was said."""
    out = []
    for d in sorted(glob.glob(os.path.join(CLAUDE, "projects", "*"))):
        files = glob.glob(os.path.join(d, "*.jsonl"))
        if not files:
            continue
        cwd = None
        for f in sorted(files, key=os.path.getmtime, reverse=True):
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    for _, line in zip(range(40), fh):
                        try:
                            cwd = json.loads(line).get("cwd")
                        except (ValueError, AttributeError):
                            continue
                        if cwd:
                            break
            except OSError:
                continue
            if cwd:
                break
        out.append({"slug": os.path.basename(d), "cwd": cwd, "sessions": len(files),
                    "last": max(os.path.getmtime(f) for f in files)})
    return out


def find_projects(root, projects_json, user_json, history):
    """Every folder Claude Code has worked in (its session history and the projects list in
    ~/.claude.json), plus a folder the user passes and its subfolders, plus an optional
    projects list. Returns the projects and a function giving the project a path belongs to."""
    found, seen = [], set()
    skip = {real(HOME), real(CLAUDE)}
    temp = real(tempfile.gettempdir())

    def add(path, name=None):
        if not path or not os.path.isdir(path):
            return
        r = real(path)
        if r in seen or r in skip or os.path.dirname(r) == r or r.startswith((real(CLAUDE) + "/", temp + "/")):
            return  # the home folder, a drive root, ~/.claude and throwaway temp folders are not projects
        if os.path.isfile(os.path.join(path, ".git")):
            return  # a git worktree: a second checkout of a project already on the map
        seen.add(r)
        found.append({"name": name or os.path.basename(os.path.abspath(path).rstrip("\\/")) or path, "path": path, "real": r})

    for h in history:
        add(h["cwd"])
    for path in user_json.get("projects") or {}:
        add(path)
    sources["projects"] = ("every folder Claude Code has worked in: the working folder of the sessions under "
                           "~/.claude/projects (paths and file times only) and the projects list in ~/.claude.json")
    if root:
        add(root)
        for top, dirs, _ in os.walk(root):
            depth = os.path.relpath(top, root).count(os.sep) + (top != root)
            dirs[:] = sorted((d for d in dirs if d.lower() not in SKIP and not d.startswith(".")), key=str.lower) if depth < DEPTH else []
            if top != root and looks_like_project(top):
                add(top)
        sources["projects"] += f"; plus folders under {root} ({DEPTH} levels deep) with a .git, .claude, CLAUDE.md or .mcp.json"
    if projects_json:
        cfg = load_json(projects_json, "projects list")
        if cfg:
            for scan in cfg.get("scanRoots") or []:
                try:
                    for d in sorted(os.scandir(scan), key=lambda d: d.name.lower()):
                        if d.is_dir() and not d.name.startswith("."):
                            add(d.path, d.name)
                except OSError:
                    unread.append(f"scan root {scan}: missing")
            for p in cfg.get("projects", []):
                add(p.get("path", ""), p.get("name"))
            sources["projects"] += f"; plus the projects listed in {projects_json}"

    # a folder inside another project's git repo is part of it, unless it has a setup of its own;
    # a plain folder that only holds projects (no .git) does not swallow them, nor does a repo hold another repo
    found.sort(key=lambda p: len(p["real"]))
    projects = []
    is_repo = lambda p: os.path.isdir(os.path.join(p["path"], ".git"))
    for p in found:
        parent = None if is_repo(p) else next(
            (q for q in reversed(projects) if is_repo(q) and p["real"].startswith(q["real"] + "/")), None)
        if parent and not os.path.isdir(os.path.join(p["path"], ".claude")):
            continue
        if parent:
            p["name"] = nested_name(parent, p["path"])
        projects.append(p)

    def owner(path):
        r = real(path) if path else ""
        return next((q for q in sorted(projects, key=lambda q: -len(q["real"]))
                     if r == q["real"] or r.startswith(q["real"] + "/")), None)

    # activity: sessions and last use, a worktree's or subfolder's counting for its project
    for h in history:
        q = owner(h["cwd"])
        if q:
            q["sessions"] = q.get("sessions", 0) + h["sessions"]
            q["lastTs"] = max(q.get("lastTs", 0), h["last"])
    projects.sort(key=lambda p: p["name"].lower())
    return projects, owner


def own_setup(path, name, user_json):
    cl = os.path.join(path, ".claude")
    own = {}
    # an agent file declares itself in front matter; reference docs kept beside agents do not
    own["agents"] = [{"name": fm["name"], "desc": short(fm.get("description"))}
                     for fm in (frontmatter(f) for f in sorted(glob.glob(os.path.join(cl, "agents", "**", "*.md"), recursive=True)))
                     if fm.get("name")]
    own["skills"] = [{"name": frontmatter(f).get("name") or os.path.basename(os.path.dirname(f)), "desc": short(frontmatter(f).get("description"))}
                     for f in sorted(glob.glob(os.path.join(cl, "skills", "*", "SKILL.md")))]
    own["commands"] = [{"name": "/" + os.path.relpath(f, os.path.join(cl, "commands"))[:-3].replace(os.sep, ":"), "desc": short(frontmatter(f).get("description"))}
                       for f in sorted(glob.glob(os.path.join(cl, "commands", "**", "*.md"), recursive=True))]
    own["hooks"] = merge(hooks_from(load_json(os.path.join(cl, "settings.json"), f"{name}/.claude/settings.json"), "Project hook")
                         + hooks_from(load_json(os.path.join(cl, "settings.local.json"), f"{name}/.claude/settings.local.json"), "Project hook, local"))
    for h in own["hooks"]:
        h.pop("count", None)
    mcps = [{"name": srv, "desc": "Shared in .mcp.json"} for srv in (load_json(os.path.join(path, ".mcp.json")).get("mcpServers") or {})]
    for k, v in (user_json.get("projects") or {}).items():
        if real(k) == real(path):
            mcps += [{"name": srv, "desc": "Local to this project"} for srv in (v.get("mcpServers") or {})]
    own["mcp"] = merge(mcps)
    for m in own["mcp"]:
        m.pop("count", None)
    rules = [{"name": "CLAUDE.md", "desc": "Project instructions"}] if os.path.exists(os.path.join(path, "CLAUDE.md")) else []
    if os.path.exists(os.path.join(cl, "CLAUDE.md")):
        rules.append({"name": ".claude/CLAUDE.md", "desc": "Project instructions"})
    rules += [{"name": os.path.basename(f)[:-3], "desc": short(frontmatter(f).get("description") or "Project rule file")}
              for f in sorted(glob.glob(os.path.join(cl, "rules", "*.md")))]
    own["rules"] = rules
    return {k: v for k, v in own.items() if v}


def collect(root=None, projects_json=None):
    settings = load_json(os.path.join(CLAUDE, "settings.json"), "~/.claude/settings.json")
    user_json = load_json(os.path.join(HOME, ".claude.json"), "~/.claude.json")
    history = read_history()
    projects, owner = find_projects(root, projects_json, user_json, history)

    # ---- skills, agents, commands, output styles ----
    skills = []
    for p in sorted(glob.glob(os.path.join(CLAUDE, "skills", "*", "SKILL.md"))):
        fm = frontmatter(p)
        skills.append({"name": fm.get("name") or os.path.basename(os.path.dirname(p)), "desc": short(fm.get("description"))})
    sources["skills"] = "~/.claude/skills/*/SKILL.md"
    agents = md_items(os.path.join(CLAUDE, "agents"))
    sources["agents"] = "~/.claude/agents"
    commands = [dict(i, name="/" + i["name"]) for i in md_items(os.path.join(CLAUDE, "commands"))]
    sources["commands"] = "~/.claude/commands"
    styles = md_items(os.path.join(CLAUDE, "output-styles"), "Output style")
    active = settings.get("outputStyle")
    for s in styles:
        if s["name"] == active:
            s["desc"] = "Active. " + s["desc"]
    sources["styles"] = "~/.claude/output-styles (active one from settings.json)"

    # ---- rules: global CLAUDE.md, what it imports, rules/*.md ----
    rules = []
    gclaude = os.path.join(CLAUDE, "CLAUDE.md")
    if os.path.exists(gclaude):
        rules.append({"name": "CLAUDE.md", "desc": "Global instructions loaded in every session"})
        for imp in re.findall(r"^@(\S+)", open(gclaude, encoding="utf-8", errors="replace").read(), re.M):
            rules.append({"name": os.path.basename(imp), "desc": "Imported by the global CLAUDE.md"})
    rules += md_items(os.path.join(CLAUDE, "rules"), "Rule file loaded in every session")
    sources["rules"] = "~/.claude/CLAUDE.md (and its @imports) + ~/.claude/rules"

    # ---- memory: one node per project memory folder, with its file count ----
    by_slug = {slug(p["path"]): p["name"] for p in projects}
    by_slug.update({h["slug"]: owner(h["cwd"])["name"] for h in history if owner(h["cwd"])})
    home_slug = slug(HOME) + "-"
    memory = {}
    for d in sorted(glob.glob(os.path.join(CLAUDE, "projects", "*", "memory"))):
        files = {os.path.basename(f) for f in glob.glob(os.path.join(d, "*.md"))} - {"MEMORY.md"}
        if files:
            s = os.path.basename(os.path.dirname(d))
            # the same project reached by another path (a second drive, a symlink) still ends in its folder name
            tail = max((p["name"] for p in projects if s.endswith("-" + re.sub(r"[^A-Za-z0-9]", "-", p["name"]))), key=len, default=None)
            name = by_slug.get(s) or tail or re.sub(r"^[A-Za-z]--", "", s[len(home_slug):] if s.startswith(home_slug) else s).lstrip("-") or s
            memory.setdefault(name, set()).update(files)
    memory = [{"name": k, "desc": f"{len(v)} memory file{'s' * (len(v) != 1)}", "count": len(v)} for k, v in memory.items()]
    sources["memory"] = "~/.claude/projects/*/memory/*.md (file counts only)"

    # ---- plugins: enabled ones, at their installed version ----
    installed = load_json(os.path.join(CLAUDE, "plugins", "installed_plugins.json"), "installed_plugins.json")
    installed = installed.get("plugins", installed)
    plugins, mcp, hooks = [], [], hooks_from(settings, "Global settings")
    for key, on in (settings.get("enabledPlugins") or {}).items():
        if not on:
            continue
        name, _, market = key.partition("@")
        recs = installed.get(key) or []
        rec = next((r for r in recs if r.get("scope") == "user"), recs[0] if recs else None)
        root_dir = rec and rec.get("installPath")
        if not root_dir or not os.path.isdir(root_dir):
            unread.append(f"plugin {key}: enabled but not found on disk")
            plugins.append({"name": name, "market": market, "desc": "", "skills": []})
            continue
        meta = load_json(os.path.join(root_dir, ".claude-plugin", "plugin.json"))
        psk = sorted({os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(root_dir, "skills", "*", "SKILL.md"))})
        pag = sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(root_dir, "agents", "*.md")))
        pcm = sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(root_dir, "commands", "*.md")))
        mj = load_json(os.path.join(root_dir, ".mcp.json"))
        for srv in (mj.get("mcpServers") or mj):
            if isinstance(srv, str):
                mcp.append({"name": srv, "desc": f"From the {name} plugin", "scope": "plugin"})
        hooks += hooks_from(load_json(os.path.join(root_dir, "hooks", "hooks.json")), f"From the {name} plugin")
        plugins.append({"name": name, "market": market, "desc": short(meta.get("description")),
                        "skills": psk, "agents": pag, "commands": pcm})
    sources["plugins"] = "enabledPlugins in settings.json, read at the install path in plugins/installed_plugins.json"

    # ---- MCP servers: user scope, local scope per project, project .mcp.json, plugins ----
    def add_mcp(name, desc, scope):
        for m in mcp:
            if m["name"] == name:
                if desc not in m["desc"]:
                    m["desc"] += "; " + desc
                return
        mcp.append({"name": name, "desc": desc, "scope": scope})

    for srv in user_json.get("mcpServers") or {}:
        add_mcp(srv, "User scope, every project", "user")
    for path, v in (user_json.get("projects") or {}).items():
        folder = os.path.basename(path.rstrip("/\\"))
        for srv in v.get("mcpServers") or {}:
            add_mcp(srv, f"Local to {folder}", "local")

    # ---- each project's own setup ----
    for p in projects:
        for srv in (load_json(os.path.join(p["path"], ".mcp.json"), f"{p['name']}/.mcp.json").get("mcpServers") or {}):
            add_mcp(srv, f"Shared in {p['name']}/.mcp.json", "project")
        hooks += hooks_from(load_json(os.path.join(p["path"], ".claude", "settings.json"), f"{p['name']}/.claude/settings.json"), f"Project {p['name']}")
        p["own"] = own_setup(p["path"], p["name"], user_json)
    sources["mcp"] = "~/.claude.json (user and per-project local), each project's .mcp.json, enabled plugins' .mcp.json"
    hooks = merge(hooks)
    sources["hooks"] = "settings.json, enabled plugins' hooks/hooks.json, each project's .claude/settings.json"
    sources["own"] = ("per project: .claude/agents/**/*.md, .claude/skills/*/SKILL.md, .claude/commands/**/*.md, "
                      ".claude/settings(.local).json hooks, .mcp.json and ~/.claude.json local MCP servers, CLAUDE.md and .claude/rules/*.md")
    unread.append("claude.ai connectors: account-level, not stored on this computer, so not shown")

    for p in projects:
        p["desc"] = "Project"
        p["sessions"] = p.get("sessions", 0)
        if p.get("lastTs"):
            p["last"] = datetime.date.fromtimestamp(p["lastTs"]).isoformat()
        if not p["own"]:
            del p["own"]
        for k in ("path", "real", "lastTs"):
            p.pop(k, None)

    return {
        "title": "Claude Code",
        "model": settings.get("model", ""),
        "outputStyle": active or "",
        "kinds": {"skills": skills, "plugins": plugins, "agents": agents, "mcp": mcp, "hooks": hooks,
                  "commands": commands, "styles": styles, "rules": rules, "memory": memory, "projects": projects},
        "sources": sources,
        "unread": unread,
    }


def render(data, out):
    page = open(TEMPLATE, encoding="utf-8").read()
    safe = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = page.replace("/*SETUP_DATA*/null", safe, 1)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)


def main():
    ap = argparse.ArgumentParser(description="Draw your Claude Code setup as one 3D HTML page.")
    ap.add_argument("projects", nargs="?", help="a folder to look for more projects in, with its subfolders")
    ap.add_argument("--out", default=os.path.join(HOME, "setup-map", "setup-map.html"))
    ap.add_argument("--open", action="store_true", help="open the page afterwards")
    ap.add_argument("--projects-json", help="JSON file listing more projects; read if present")
    a = ap.parse_args()
    root = a.projects and os.path.abspath(os.path.expanduser(a.projects))
    if root and not os.path.isdir(root):
        sys.exit(f"Not a folder: {root}")
    if not os.path.isdir(CLAUDE):
        sys.exit(f"No Claude Code setup found at {CLAUDE}")
    data = collect(root, a.projects_json)
    render(data, a.out)
    sys.stdout.reconfigure(encoding="utf-8")
    print(os.path.abspath(a.out))
    k = data["kinds"]
    print(", ".join(f"{len(v)} {key}" for key, v in k.items()))
    print(f"{sum(1 for p in k['projects'] if p.get('own'))} of {len(k['projects'])} projects have a setup of their own")
    for u in data["unread"]:
        print("not shown:", u)
    if a.open:
        webbrowser.open(Path(os.path.abspath(a.out)).as_uri())


if __name__ == "__main__":
    main()
