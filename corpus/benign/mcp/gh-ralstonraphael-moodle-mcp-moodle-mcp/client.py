"""Thin Moodle web-service client.

Talks to the REST endpoint (webservice/rest/server.php) with a user token,
the same kind the official Moodle app uses. Every helper returns plain
dicts/lists already trimmed down to the fields worth reading.
"""

from __future__ import annotations

import base64
import html
import io
import json
import os
import re
import time
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

DEFAULT_URL = "https://moodle.trincoll.edu"
CONFIG_PATH = Path(os.environ.get("MOODLE_MCP_CONFIG", "~/.config/moodle-mcp/config.json")).expanduser()


class MoodleError(RuntimeError):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------- config

def load_config() -> dict:
    cfg: dict = {}
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text())
    if os.environ.get("MOODLE_URL"):
        cfg["url"] = os.environ["MOODLE_URL"]
    if os.environ.get("MOODLE_TOKEN"):
        cfg["token"] = os.environ["MOODLE_TOKEN"]
    cfg.setdefault("url", DEFAULT_URL)
    return cfg


def clear_config() -> bool:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
        return True
    return False


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_PATH.parent, 0o700)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    os.chmod(CONFIG_PATH, 0o600)


def parse_token(raw: str) -> str:
    """Accept a bare token or the moodlemobile://token=... link the app launch page produces."""
    raw = raw.strip()
    m = re.search(r"token=([A-Za-z0-9+/=_-]+)", raw)
    if m:
        decoded = base64.b64decode(m.group(1) + "===").decode()
        parts = decoded.split(":::")
        if len(parts) < 2:
            raise ValueError("That link didn't contain a token.")
        return parts[1]
    if not re.fullmatch(r"[A-Za-z0-9]{20,64}", raw):
        raise ValueError("That doesn't look like a Moodle token (expected ~32 letters/digits).")
    return raw


# ---------------------------------------------------------------- formatting

class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "section"}

    def __init__(self):
        super().__init__()
        self.out: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in self.BLOCK:
            self.out.append("\n")
        elif tag == "a":
            href = dict(attrs).get("href")
            if href and href.startswith("http"):
                self._href = href
        elif tag in ("td", "th"):
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        elif tag == "a" and getattr(self, "_href", None):
            self.out.append(f" <{self._href}>")
            self._href = None
        elif tag in self.BLOCK and tag != "li":
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    p = _TextExtractor()
    p.feed(html)
    text = "".join(p.out).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def fmt_time(ts: int | None) -> str | None:
    if not ts:
        return None
    d = datetime.fromtimestamp(ts)
    # Built by hand because %-d / %-I don't exist on Windows.
    return f"{d:%a %b} {d.day} {d.year} {d.hour % 12 or 12}:{d:%M %p}"


def _flatten(prefix: str, value: Any, out: dict) -> None:
    """Moodle REST wants nested params as courseids[0]=1&options[0][name]=x."""
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f"{prefix}[{k}]" if prefix else k, v, out)
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _flatten(f"{prefix}[{i}]", v, out)
    elif isinstance(value, bool):
        out[prefix] = int(value)
    elif value is not None:
        out[prefix] = value


# ---------------------------------------------------------------- client

class Moodle:
    def __init__(self, url: str | None = None, token: str | None = None):
        cfg = load_config()
        self.url = (url or cfg["url"]).rstrip("/")
        self.token = token or cfg.get("token")
        if not self.token:
            raise MoodleError(
                "No Moodle token configured. Run `moodle auth` in a terminal to add one.", "notoken"
            )
        self.http = httpx.Client(timeout=60, follow_redirects=True,
                                 headers={"User-Agent": "moodle-mcp/0.1 (MoodleMobile)"})
        self._me: dict | None = None

    # -- raw ------------------------------------------------------------
    def call(self, wsfunction: str, **params) -> Any:
        data: dict = {}
        _flatten("", params, data)
        data.update(wstoken=self.token, wsfunction=wsfunction, moodlewsrestformat="json")
        r = self.http.post(f"{self.url}/webservice/rest/server.php", data=data)
        r.raise_for_status()
        out = r.json() if r.content else None
        if isinstance(out, dict) and "exception" in out:
            code = out.get("errorcode")
            msg = out.get("message", "Moodle error")
            if code in ("invalidtoken", "accessexception") and "token" in msg.lower():
                msg += " — the token is missing or expired; run `moodle auth` again."
            raise MoodleError(f"{wsfunction}: {msg}", code)
        return out

    @property
    def me(self) -> dict:
        if self._me is None:
            self._me = self.call("core_webservice_get_site_info")
        return self._me

    def whoami(self) -> dict:
        m = self.me
        return {
            "site": m.get("sitename"), "url": m.get("siteurl"), "release": m.get("release"),
            "userid": m.get("userid"), "username": m.get("username"), "fullname": m.get("fullname"),
            "functions_available": len(m.get("functions", [])),
        }

    def has_function(self, name: str) -> bool:
        return any(f.get("name") == name for f in self.me.get("functions", []))

    def functions(self, match: str | None = None) -> list[str]:
        """Names of every web-service function this token may call, optionally filtered by a substring."""
        names = sorted(f["name"] for f in self.me.get("functions", []))
        return [n for n in names if match.lower() in n.lower()] if match else names

    # -- courses ----------------------------------------------------------
    def courses(self, which: str = "inprogress") -> list[dict]:
        """which: inprogress | future | past | all"""
        if which != "all" and self.has_function("core_course_get_enrolled_courses_by_timeline_classification"):
            res = self.call("core_course_get_enrolled_courses_by_timeline_classification",
                            classification=which, limit=0)
            raw = res.get("courses", [])
        else:
            raw = self.call("core_enrol_get_users_courses", userid=self.me["userid"])
        return [{
            "id": c["id"], "shortname": _u(c.get("shortname")), "fullname": _u(c.get("fullname")),
            "start": fmt_time(c.get("startdate")), "end": fmt_time(c.get("enddate")),
            "progress": c.get("progress"), "url": f"{self.url}/course/view.php?id={c['id']}",
        } for c in raw]

    def course_contents(self, course_id: int, include_descriptions: bool = True) -> list[dict]:
        sections = self.call("core_course_get_contents", courseid=course_id)
        out = []
        for s in sections:
            mods = []
            for m in s.get("modules", []):
                if m.get("uservisible") is False:
                    continue
                mod = {"cmid": m["id"], "type": m.get("modname"), "name": _u(m.get("name")),
                       "instance": m.get("instance"), "url": m.get("url")}
                dates = [f"{d['label']} {fmt_time(d['timestamp'])}" for d in m.get("dates", []) if d.get("timestamp")]
                if dates:
                    mod["dates"] = dates
                if include_descriptions and m.get("description"):
                    mod["description"] = html_to_text(m["description"])[:1500]
                files = [{"filename": f["filename"], "fileurl": f.get("fileurl"), "size": f.get("filesize"),
                          "modified": fmt_time(f.get("timemodified"))}
                         for f in m.get("contents", []) if f.get("type") == "file"]
                if files:
                    mod["files"] = files
                if m.get("modname") == "url":
                    ext = [f.get("fileurl") for f in m.get("contents", []) if f.get("type") == "url"]
                    if ext:
                        mod["external_url"] = ext[0]
                comp = m.get("completiondata")
                if comp:
                    mod["completed"] = bool(comp.get("state"))
                mods.append(mod)
            sec = {"section": s.get("section"), "name": _u(s.get("name")), "modules": mods}
            if include_descriptions and s.get("summary"):
                sec["summary"] = html_to_text(s["summary"])[:3000]
            if mods or sec.get("summary"):
                out.append(sec)
        return out

    def search(self, query: str, course_ids: list[int] | None = None) -> list[dict]:
        """Case-insensitive search over module names, descriptions, section text and file names."""
        q = query.lower()
        ids = course_ids or [c["id"] for c in self.courses()]
        hits = []
        for cid in ids:
            for sec in self.course_contents(cid):
                if q in (sec.get("summary") or "").lower() or q in (sec.get("name") or "").lower():
                    hits.append({"course": cid, "section": sec["name"], "match": "section text",
                                 "excerpt": _excerpt(sec.get("summary") or sec["name"], q)})
                for m in sec["modules"]:
                    blob = " ".join([m.get("name") or "", m.get("description") or "",
                                     *[f["filename"] for f in m.get("files", [])]]).lower()
                    if q in blob:
                        hits.append({"course": cid, "section": sec["name"], "cmid": m["cmid"],
                                     "type": m["type"], "name": m["name"], "url": m["url"],
                                     "excerpt": _excerpt(m.get("description") or m["name"], q)})
        return hits

    # -- deadlines --------------------------------------------------------
    def deadlines(self, days_ahead: int = 14, days_back: int = 0, course_id: int | None = None) -> list[dict]:
        now = int(time.time())
        params = dict(timesortfrom=now - days_back * 86400, timesortto=now + days_ahead * 86400,
                      limitnum=50, limittononsuspendedevents=True)
        if course_id:
            res = self.call("core_calendar_get_action_events_by_course", courseid=course_id,
                            timesortfrom=params["timesortfrom"], timesortto=params["timesortto"], limitnum=50)
        else:
            res = self.call("core_calendar_get_action_events_by_timesort", **params)
        out = []
        for e in res.get("events", []):
            out.append({
                "name": _u(e.get("activityname") or e.get("name")),
                "course": _u((e.get("course") or {}).get("shortname")),
                "course_id": (e.get("course") or {}).get("id"),
                "type": e.get("modulename"), "cmid": _cmid(e.get("url")),
                "due": fmt_time(e.get("timesort")), "due_ts": e.get("timesort"),
                "overdue": e.get("timesort", now) < now or bool(e.get("overdue")),
                "action": (e.get("action") or {}).get("name"),
                "url": e.get("url"),
            })
        return out

    # -- assignments ------------------------------------------------------
    def assignments(self, course_ids: list[int] | None = None, include_status: bool = True,
                    only_open: bool = False) -> list[dict]:
        ids = course_ids or [c["id"] for c in self.courses()]
        res = self.call("mod_assign_get_assignments", courseids=ids)
        now = time.time()
        out = []
        for c in res.get("courses", []):
            for a in c.get("assignments", []):
                if only_open and a.get("duedate") and a.get("cutoffdate") and a["cutoffdate"] < now:
                    continue
                item = {
                    "assign_id": a["id"], "cmid": a["cmid"], "course": _u(c.get("shortname")), "course_id": c["id"],
                    "name": _u(a["name"]), "due": fmt_time(a.get("duedate")), "due_ts": a.get("duedate") or None,
                    "cutoff": fmt_time(a.get("cutoffdate")),
                    "url": f"{self.url}/mod/assign/view.php?id={a['cmid']}",
                }
                if include_status:
                    try:
                        item.update(self._assign_status_brief(a["id"]))
                    except MoodleError as e:
                        item["status_error"] = str(e)
                out.append(item)
        out.sort(key=lambda x: x.get("due_ts") or 1 << 40)
        return out

    def _assign_status_brief(self, assign_id: int) -> dict:
        st = self.call("mod_assign_get_submission_status", assignid=assign_id)
        last = st.get("lastattempt") or {}
        sub = last.get("submission") or (last.get("teamsubmission") or {})
        fb = st.get("feedback") or {}
        brief = {"submission": sub.get("status", "nosubmission"),
                 "grading": last.get("gradingstatus")}
        if fb.get("gradefordisplay"):
            brief["grade"] = html_to_text(fb["gradefordisplay"])
        return brief

    def assignment(self, assign_id: int | None = None, cmid: int | None = None) -> dict:
        """Full detail for one assignment: instructions, attachments, dates, submission, feedback."""
        if assign_id is None:
            if cmid is None:
                raise MoodleError("Give assign_id or cmid.")
            cm = self.call("core_course_get_course_module", cmid=cmid)["cm"]
            assign_id, course_id = cm["instance"], cm["course"]
        else:
            course_id = None
        res = self.call("mod_assign_get_assignments", courseids=[course_id] if course_id else [])
        a = next((a for c in res.get("courses", []) for a in c.get("assignments", []) if a["id"] == assign_id), None)
        if not a:
            raise MoodleError(f"Assignment {assign_id} not found in your courses.")
        st = self.call("mod_assign_get_submission_status", assignid=assign_id)
        last = st.get("lastattempt") or {}
        sub = last.get("submission") or {}
        sub_files, sub_text = [], None
        for p in sub.get("plugins", []):
            for fa in p.get("fileareas", []) or []:
                sub_files += [{"filename": f["filename"], "fileurl": f.get("fileurl")} for f in fa.get("files", [])]
            for ef in p.get("editorfields", []) or []:
                if ef.get("text"):
                    sub_text = html_to_text(ef["text"])
        plugins = [c["plugin"] for c in a.get("configs", [])
                   if c.get("subtype") == "assignsubmission" and c.get("name") == "enabled" and c.get("value") == "1"
                   and c.get("plugin") != "comments"]
        fb = st.get("feedback") or {}
        feedback_text = []
        for p in fb.get("plugins", []) or []:
            for ef in p.get("editorfields", []) or []:
                if ef.get("text"):
                    feedback_text.append(html_to_text(ef["text"]))
        return {
            "assign_id": a["id"], "cmid": a["cmid"], "name": _u(a["name"]),
            "url": f"{self.url}/mod/assign/view.php?id={a['cmid']}",
            "opens": fmt_time(a.get("allowsubmissionsfromdate")), "due": fmt_time(a.get("duedate")),
            "cutoff": fmt_time(a.get("cutoffdate")), "grading_due": fmt_time(a.get("gradingduedate")),
            "submission_types": plugins,
            "requires_submit_button": bool(a.get("submissiondrafts")),
            "requires_statement": bool(a.get("requiresubmissionstatement")),
            "instructions": html_to_text(a.get("intro")),
            "attachments": [{"filename": f["filename"], "fileurl": f.get("fileurl")} for f in a.get("introattachments", [])],
            "submission_status": sub.get("status", "nosubmission"),
            "last_modified": fmt_time(sub.get("timemodified")),
            "grading_status": last.get("gradingstatus"),
            "can_edit": last.get("canedit"), "can_submit": last.get("cansubmit"),
            "submitted_files": sub_files, "submitted_text": sub_text,
            "grade": html_to_text(fb.get("gradefordisplay")) or None,
            "feedback": "\n\n".join(feedback_text) or None,
            "time_remaining": None if not a.get("duedate") else _remaining(a["duedate"]),
        }

    # -- grades -----------------------------------------------------------
    def grades(self, course_id: int) -> list[dict]:
        res = self.call("gradereport_user_get_grade_items", courseid=course_id, userid=self.me["userid"])
        items = []
        for ug in res.get("usergrades", []):
            for g in ug.get("gradeitems", []):
                items.append({
                    "item": g.get("itemname") or ("Course total" if g.get("itemtype") == "course" else g.get("itemtype")),
                    "type": g.get("itemmodule") or g.get("itemtype"), "cmid": g.get("cmid"),
                    "grade": g.get("gradeformatted"), "max": g.get("grademax"),
                    "percent": g.get("percentageformatted"), "weight": g.get("weightformatted"),
                    "feedback": html_to_text(g.get("feedback")) or None,
                })
        return items

    def course_overview_grades(self) -> list[dict]:
        res = self.call("gradereport_overview_get_course_grades", userid=self.me["userid"])
        names = {c["id"]: c["shortname"] for c in self.courses("all")}
        return [{"course_id": g["courseid"], "course": names.get(g["courseid"]), "grade": g.get("grade")}
                for g in res.get("grades", [])]

    # -- modules ----------------------------------------------------------
    def read_module(self, cmid: int) -> dict:
        """Open any course activity/resource by its cmid and return what's readable in it."""
        cm = self.call("core_course_get_course_module", cmid=cmid)["cm"]
        kind, inst, course = cm["modname"], cm["instance"], cm["course"]
        base = {"cmid": cmid, "type": kind, "name": _u(cm.get("name")), "course_id": course,
                "url": f"{self.url}/mod/{kind}/view.php?id={cmid}"}

        def by_course(fn: str, key: str) -> dict:
            res = self.call(fn, courseids=[course])
            return next((x for x in res.get(key, []) if x.get("id") == inst or x.get("coursemodule") == cmid), {})

        if kind == "assign":
            return {**base, **self.assignment(assign_id=inst)}
        if kind == "page":
            p = by_course("mod_page_get_pages_by_courses", "pages")
            return {**base, "intro": html_to_text(p.get("intro")), "content": html_to_text(p.get("content")),
                    "files": _files(p.get("contentfiles"))}
        if kind == "resource":
            r = by_course("mod_resource_get_resources_by_courses", "resources")
            return {**base, "intro": html_to_text(r.get("intro")), "files": _files(r.get("contentfiles"))}
        if kind == "url":
            u = by_course("mod_url_get_urls_by_courses", "urls")
            return {**base, "external_url": u.get("externalurl"), "intro": html_to_text(u.get("intro"))}
        if kind == "folder":
            f = by_course("mod_folder_get_folders_by_courses", "folders")
            contents = self.call("core_course_get_contents", courseid=course,
                                 options=[{"name": "cmid", "value": cmid}])
            files = [{"filename": c["filename"], "path": c.get("filepath"), "fileurl": c.get("fileurl")}
                     for s in contents for m in s.get("modules", []) if m["id"] == cmid
                     for c in m.get("contents", []) if c.get("type") == "file"]
            return {**base, "intro": html_to_text(f.get("intro")), "files": files}
        if kind == "label":
            lb = by_course("mod_label_get_labels_by_courses", "labels")
            return {**base, "content": html_to_text(lb.get("intro"))}
        if kind == "forum":
            return {**base, "discussions": self.forum_discussions(inst)}
        if kind == "quiz":
            q = by_course("mod_quiz_get_quizzes_by_courses", "quizzes")
            att = self.call("mod_quiz_get_user_attempts", quizid=inst, status="all").get("attempts", [])
            best = None
            try:
                best = self.call("mod_quiz_get_user_best_grade", quizid=inst).get("grade")
            except MoodleError:
                pass
            return {**base, "intro": html_to_text(q.get("intro")), "opens": fmt_time(q.get("timeopen")),
                    "closes": fmt_time(q.get("timeclose")), "time_limit_min": (q.get("timelimit") or 0) // 60 or None,
                    "attempts_allowed": q.get("attempts") or "unlimited", "grade_max": q.get("grade"),
                    "your_attempts": [{"state": a["state"], "finished": fmt_time(a.get("timefinish")),
                                       "grade": a.get("sumgrades")} for a in att],
                    "best_grade": best}
        # Fallback: whatever core_course_get_contents knows about it.
        return {**base, "note": f"No dedicated reader for '{kind}'; showing the course listing entry.",
                "entry": next((m for s in self.course_contents(course) for m in s["modules"] if m["cmid"] == cmid), None)}

    # -- forums -----------------------------------------------------------
    def forum_discussions(self, forum_id: int, limit: int = 15) -> list[dict]:
        res = self.call("mod_forum_get_forum_discussions", forumid=forum_id, sortorder=-1, page=0, perpage=limit)
        return [{"discussion_id": d["discussion"], "subject": _u(d.get("subject") or d.get("name")),
                 "author": d.get("userfullname"), "posted": fmt_time(d.get("created")), "posted_ts": d.get("created"),
                 "replies": d.get("numreplies"), "message": html_to_text(d.get("message"))[:2500],
                 "attachments": _files(d.get("attachments"))}
                for d in res.get("discussions", [])]

    def discussion(self, discussion_id: int) -> list[dict]:
        res = self.call("mod_forum_get_discussion_posts", discussionid=discussion_id, sortby="created",
                        sortdirection="ASC")
        return [{"author": (p.get("author") or {}).get("fullname"), "posted": fmt_time(p.get("timecreated")),
                 "subject": _u(p.get("subject")), "message": html_to_text(p.get("message")),
                 "attachments": _files(p.get("attachments"))} for p in res.get("posts", [])]

    def announcements(self, course_ids: list[int] | None = None, per_course: int = 5) -> list[dict]:
        ids = course_ids or [c["id"] for c in self.courses()]
        forums = self.call("mod_forum_get_forums_by_courses", courseids=ids)
        out = []
        for f in forums:
            if f.get("type") != "news":
                continue
            for d in self.forum_discussions(f["id"], per_course):
                out.append({"course_id": f["course"], **d})
        out.sort(key=lambda d: d.get("posted_ts") or 0, reverse=True)
        return out

    def notifications(self, limit: int = 20, unread_only: bool = False) -> list[dict]:
        res = self.call("message_popup_get_popup_notifications", useridto=self.me["userid"],
                        newestfirst=1, limit=limit, offset=0)
        out = [{"subject": _u(n.get("subject")), "read": n.get("read"), "when": fmt_time(n.get("timecreated")),
                "text": html_to_text(n.get("smallmessage") or n.get("fullmessage"))[:600],
                "url": n.get("contexturl")} for n in res.get("notifications", [])]
        return [n for n in out if not n["read"]] if unread_only else out

    # -- files ------------------------------------------------------------
    def _file_url(self, fileurl: str) -> str:
        if "/webservice/pluginfile.php" not in fileurl and "/pluginfile.php" in fileurl:
            fileurl = fileurl.replace("/pluginfile.php", "/webservice/pluginfile.php", 1)
        sep = "&" if "?" in fileurl else "?"
        return f"{fileurl}{sep}token={self.token}"

    def fetch_file(self, fileurl: str) -> tuple[bytes, str, str]:
        r = self.http.get(self._file_url(fileurl))
        r.raise_for_status()
        ctype = r.headers.get("content-type", "")
        if "application/json" in ctype and r.content[:1] == b"{":
            err = r.json()
            raise MoodleError(err.get("error") or err.get("message") or "File download failed", err.get("errorcode"))
        name = unquote(Path(urlparse(fileurl).path).name)
        return r.content, ctype, name

    def download(self, fileurl: str, dest: str = "~/Downloads/Moodle") -> str:
        data, _, name = self.fetch_file(fileurl)
        d = Path(dest).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        path = d / name
        path.write_bytes(data)
        return str(path)

    def file_text(self, fileurl: str) -> str:
        data, ctype, name = self.fetch_file(fileurl)
        return extract_text(data, ctype, name)

    # -- writes -----------------------------------------------------------
    def upload_draft(self, path: str, itemid: int = 0) -> int:
        p = Path(path).expanduser()
        with p.open("rb") as fh:
            r = self.http.post(f"{self.url}/webservice/upload.php",
                               data={"token": self.token, "filearea": "draft", "itemid": itemid},
                               files={"file_1": (p.name, fh)})
        r.raise_for_status()
        res = r.json()
        if isinstance(res, dict) and ("error" in res or "exception" in res):
            raise MoodleError(res.get("error") or res.get("message"), res.get("errorcode"))
        return res[0]["itemid"]

    def save_submission(self, assign_id: int, text_html: str | None = None,
                        file_paths: list[str] | None = None, submit_for_grading: bool = False) -> dict:
        plugindata: dict = {}
        if text_html is not None:
            plugindata["onlinetext_editor"] = {"text": text_html, "format": 1, "itemid": 0}
        if file_paths:
            itemid = 0
            for fp in file_paths:
                itemid = self.upload_draft(fp, itemid)
            plugindata["files_filemanager"] = itemid
        if not plugindata:
            raise MoodleError("Nothing to submit: give text and/or files.")
        warnings = self.call("mod_assign_save_submission", assignmentid=assign_id, plugindata=plugindata)
        result = {"saved": True, "warnings": warnings or []}
        if submit_for_grading:
            w2 = self.call("mod_assign_submit_for_grading", assignmentid=assign_id, acceptsubmissionstatement=1)
            result["submitted_for_grading"] = True
            result["warnings"] += w2 or []
        result["status_now"] = self._assign_status_brief(assign_id)
        return result


# ---------------------------------------------------------------- helpers

def _u(s):
    return html.unescape(s) if isinstance(s, str) else s


def _files(lst) -> list[dict]:
    return [{"filename": f.get("filename"), "fileurl": f.get("fileurl"), "size": f.get("filesize")}
            for f in (lst or [])]


def _cmid(url: str | None) -> int | None:
    m = re.search(r"[?&]id=(\d+)", url or "")
    return int(m.group(1)) if m else None


def _excerpt(text: str, q: str, width: int = 160) -> str:
    i = text.lower().find(q)
    if i < 0:
        return text[:width]
    s = max(0, i - width // 2)
    return ("…" if s else "") + text[s:s + width].replace("\n", " ") + "…"


def _remaining(due: int) -> str:
    delta = due - time.time()
    sign = "" if delta >= 0 else "overdue by "
    delta = abs(delta)
    d, h = int(delta // 86400), int(delta % 86400 // 3600)
    return f"{sign}{d}d {h}h" if d else f"{sign}{h}h {int(delta % 3600 // 60)}m"


def extract_text(data: bytes, ctype: str, name: str) -> str:
    low = name.lower()
    if low.endswith(".pdf") or "pdf" in ctype:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(f"--- page {i + 1} ---\n{(pg.extract_text() or '').strip()}"
                           for i, pg in enumerate(reader.pages))
    if low.endswith((".docx", ".pptx", ".xlsx")):
        z = zipfile.ZipFile(io.BytesIO(data))
        if low.endswith(".docx"):
            parts = ["word/document.xml"]
        elif low.endswith(".pptx"):
            parts = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                           key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)))
        else:
            parts = ["xl/sharedStrings.xml"]
        chunks = []
        for i, part in enumerate(parts):
            xml = z.read(part).decode("utf8", "ignore")
            xml = re.sub(r"</w:p>|</a:p>|</si>", "\n", xml)
            txt = re.sub(r"<[^>]+>", "", xml)
            chunks.append((f"--- slide {i + 1} ---\n" if low.endswith(".pptx") else "") + txt.strip())
        return "\n\n".join(chunks)
    if "html" in ctype or low.endswith((".html", ".htm")):
        return html_to_text(data.decode("utf8", "ignore"))
    if ctype.startswith("text/") or low.endswith((".txt", ".md", ".c", ".h", ".py", ".java", ".csv", ".json", ".s")):
        return data.decode("utf8", "ignore")
    raise MoodleError(f"Can't extract text from {name} ({ctype}); use download instead.")
