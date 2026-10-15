#!/usr/bin/env python3
"""Grok Lab Bridge — daily deterministic maintenance.

Run by cron (niced, low priority so production GPU workloads keep the machine).
Zero bot tokens: everything here is mechanical.

Does:
  - rotate audit.log / runner.log / outbox.jsonl / maintenance.log (gzip, keep N)
  - prune search_cache entries older than 2h (TTL is 1h)
  - prune done/error jobs older than 30 days (audit trail stays in audit.log)
  - reap jobs stuck in 'running' > 30 min (runner died mid-job) -> error + outbox
  - prune expired memories (expires_at < now)
  - VACUUM jobs.db / memory.db when pruning freed meaningful space
  - health checks: service active, job_runner heartbeat fresh (<15 min),
    public URL reachable (expects 401 without token; skipped if
    BRIDGE_PUBLIC_URL is unset), disk headroom
  - write CONFIG_DIR/maintenance-status.json + one audit line

Exits 0 always; anomalies are reported in the status JSON, not by failing.
"""
import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as bridge  # noqa: E402

CONFIG_DIR = bridge.CONFIG_DIR
AUDIT_LOG = bridge.AUDIT_LOG
RUNNER_LOG = CONFIG_DIR / "runner.log"
OUTBOX = bridge.OUTBOX
MAINT_LOG = CONFIG_DIR / "maintenance.log"
STATUS_FILE = CONFIG_DIR / "maintenance-status.json"

AUDIT_ROTATE_BYTES = 5_000_000
AUDIT_KEEP = 12
LOG_ROTATE_BYTES = 1_000_000
LOG_KEEP = 4
OUTBOX_ROTATE_BYTES = 1_000_000
OUTBOX_KEEP = 8
CACHE_MAX_AGE_H = 2
JOB_PRUNE_DAYS = 30
STUCK_JOB_MIN = 30
HEARTBEAT_MAX_MIN = 15
# e.g. "https://<your-host>.<your-tailnet>.ts.net:8443/mcp"; unset = skip check
PUBLIC_URL = os.environ.get("BRIDGE_PUBLIC_URL", "")


def rotate(path: Path, max_bytes: int, keep: int) -> str:
    """Rename + gzip a log over max_bytes. Returns human-readable action."""
    try:
        if not path.exists() or path.stat().st_size < max_bytes:
            return "ok"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        dest = path.with_name(f"{path.name}.{stamp}.gz")
        with open(path, "rb") as f_in, gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        path.write_text("")
        # prune old archives
        olds = sorted(path.parent.glob(f"{path.name}.*.gz"))
        for old in olds[:-keep] if len(olds) > keep else []:
            old.unlink()
        return f"rotated -> {dest.name}"
    except Exception as e:
        return f"FAILED: {e}"


def db(action_desc: str):
    """Context helper returning (jobs_con, mem_con) with busy timeout."""
    jc = sqlite3.connect(str(bridge.JOBS_DB))
    jc.execute("PRAGMA busy_timeout=30000")
    mc = sqlite3.connect(str(bridge.MEMORY_DB))
    mc.execute("PRAGMA busy_timeout=30000")
    return jc, mc


def main():
    now = datetime.now(timezone.utc)
    report = {"ts": now.isoformat(), "actions": {}, "health": {}, "anomalies": []}

    # ---- rotation -------------------------------------------------------
    report["actions"]["audit.log"] = rotate(AUDIT_LOG, AUDIT_ROTATE_BYTES, AUDIT_KEEP)
    report["actions"]["runner.log"] = rotate(RUNNER_LOG, LOG_ROTATE_BYTES, LOG_KEEP)
    report["actions"]["outbox.jsonl"] = rotate(OUTBOX, OUTBOX_ROTATE_BYTES, OUTBOX_KEEP)
    report["actions"]["maintenance.log"] = rotate(MAINT_LOG, LOG_ROTATE_BYTES, LOG_KEEP)

    jc, mc = db("maint")

    # ---- search cache prune ---------------------------------------------
    cur = jc.execute(
        "DELETE FROM search_cache WHERE fetched_at < ?",
        ((now - timedelta(hours=CACHE_MAX_AGE_H)).isoformat(),))
    report["actions"]["search_cache_pruned"] = cur.rowcount

    # ---- stuck job reaper ------------------------------------------------
    stuck = jc.execute(
        """SELECT id, name FROM jobs WHERE status='running'
           AND (started_at IS NULL OR started_at < ?)""",
        ((now - timedelta(minutes=STUCK_JOB_MIN)).isoformat(),)).fetchall()
    for job_id, name in stuck:
        jc.execute("UPDATE jobs SET status='error', result=? WHERE id=?",
                   (json.dumps({"error": "runner died mid-job; reaped by maintenance"}),
                    job_id))
        try:
            with open(OUTBOX, "a") as f:
                f.write(json.dumps({"ts": now.isoformat(), "job_id": job_id,
                                    "name": name, "tool": "?",
                                    "status": "reaped"}) + "\n")
        except Exception:
            pass
    report["actions"]["stuck_jobs_reaped"] = len(stuck)
    if stuck:
        report["anomalies"].append(f"{len(stuck)} stuck jobs reaped")

    # ---- old completed jobs prune (audit trail stays in audit.log) ------
    cur = jc.execute(
        "DELETE FROM jobs WHERE status IN ('done','error','reaped') AND run_at < ?",
        ((now - timedelta(days=JOB_PRUNE_DAYS)).isoformat(),))
    report["actions"]["old_jobs_pruned"] = cur.rowcount
    err_n = jc.execute("SELECT COUNT(*) FROM jobs WHERE status='error'").fetchone()[0]
    pend_n = jc.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
    overdue = jc.execute(
        "SELECT COUNT(*) FROM jobs WHERE status='pending' AND run_at < ?",
        (now.isoformat(),)).fetchone()[0]
    report["health"]["jobs_pending"] = pend_n
    report["health"]["jobs_overdue"] = overdue
    report["health"]["jobs_error"] = err_n
    if overdue:
        report["anomalies"].append(f"{overdue} jobs overdue (pending, run_at in past)")

    # ---- expired memories -------------------------------------------------
    cur = mc.execute(
        "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
        (now.isoformat(),))
    report["actions"]["expired_memories_pruned"] = cur.rowcount
    mem_n = mc.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    report["health"]["memories"] = mem_n

    # ---- vacuum if worthwhile ---------------------------------------------
    for label, con, dbpath in (("jobs.db", jc, bridge.JOBS_DB),
                               ("memory.db", mc, bridge.MEMORY_DB)):
        before = dbpath.stat().st_size
        freelist = con.execute("PRAGMA freelist_count").fetchone()[0]
        page = con.execute("PRAGMA page_size").fetchone()[0]
        if freelist * page > 1_000_000:
            con.commit()
            con.execute("VACUUM")
            after = dbpath.stat().st_size
            report["actions"][f"vacuum_{label}"] = f"{before}->{after} bytes"
        else:
            report["actions"][f"vacuum_{label}"] = "skipped (nothing to reclaim)"
    jc.commit()
    mc.commit()

    # ---- health: service ---------------------------------------------------
    try:
        r = subprocess.run(["systemctl", "--user", "is-active",
                            "grok-lab-bridge.service"],
                           capture_output=True, text=True, timeout=15)
        report["health"]["service"] = r.stdout.strip()
        if r.stdout.strip() != "active":
            report["anomalies"].append("bridge service not active")
    except Exception as e:
        report["health"]["service"] = f"check failed: {e}"
        report["anomalies"].append("service check failed")

    # ---- health: job_runner heartbeat --------------------------------------
    try:
        row = jc.execute("SELECT v FROM meta WHERE k='last_run'").fetchone()
        if row:
            age_min = (now - datetime.fromisoformat(row[0])).total_seconds() / 60
            report["health"]["runner_heartbeat_min_ago"] = round(age_min, 1)
            if age_min > HEARTBEAT_MAX_MIN:
                report["anomalies"].append(
                    f"job_runner heartbeat stale ({age_min:.0f} min)")
        else:
            report["health"]["runner_heartbeat_min_ago"] = None
            report["anomalies"].append("no job_runner heartbeat recorded yet")
    except Exception as e:
        report["health"]["runner_heartbeat_min_ago"] = f"check failed: {e}"

    # ---- health: funnel reachability (no token -> expect 401) --------------
    try:
        if not PUBLIC_URL:
            raise LookupError("BRIDGE_PUBLIC_URL unset")
        req = urllib.request.Request(PUBLIC_URL, method="POST",
                                     data=b"{}",
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=20)
            report["health"]["funnel"] = "unexpected 2xx without token"
            report["anomalies"].append("funnel returned 2xx without bearer token")
        except urllib.error.HTTPError as he:
            report["health"]["funnel"] = f"HTTP {he.code}"
            if he.code != 401:
                report["anomalies"].append(f"funnel unexpected status {he.code}")
    except LookupError:
        report["health"]["funnel"] = "skipped (BRIDGE_PUBLIC_URL unset)"
    except Exception as e:
        report["health"]["funnel"] = f"unreachable: {str(e)[:120]}"
        report["anomalies"].append("funnel unreachable from bridge host")

    # ---- health: disk -------------------------------------------------------
    try:
        du = sum(p.stat().st_size for p in CONFIG_DIR.rglob("*") if p.is_file())
        free = shutil.disk_usage(CONFIG_DIR).free
        report["health"]["config_dir_bytes"] = du
        report["health"]["disk_free_gb"] = round(free / 1e9, 1)
        if free < 1e9:
            report["anomalies"].append("disk free < 1GB")
    except Exception as e:
        report["health"]["disk"] = f"check failed: {e}"

    jc.close()
    mc.close()

    STATUS_FILE.write_text(json.dumps(report, indent=2))
    bridge.audit("maintenance", "-", f"{len(report['anomalies'])} anomalies", 0,
                 len(json.dumps(report)))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
