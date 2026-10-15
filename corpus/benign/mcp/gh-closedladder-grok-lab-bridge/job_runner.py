#!/usr/bin/env python3
"""Grok Lab Bridge — scheduled job runner.

Invoked by cron every 5 minutes. Executes due jobs by calling the bridge's own
tool functions in-process (imported from server.py, NOT via HTTP), writes results
to the jobs table, and appends a line per job to the outbox JSONL.

Allowed job tools: exec, web_search, web_fetch, memory_write, gpu_status.
The exec denylist is enforced inside the tool itself.

Robustness:
  - meta.last_run heartbeat lets maintenance.py detect a dead cron/runner.
  - jobs carry attempts/max_attempts; on transient error a job with retries
    left is requeued as pending with exponential backoff (5min * 2^attempts).
    Exhausted jobs land in 'error' = the dead-letter queue, visible via
    job_results/list_jobs.
  - jobs stuck in 'running' (runner killed mid-job) are reaped by maintenance.py.
"""
import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as bridge  # noqa: E402

OUTBOX = bridge.CONFIG_DIR / "outbox.jsonl"
RETRY_BASE_SECONDS = 300
RETRY_MAX = 5


def _ensure_columns(con):
    for col in ("attempts INTEGER DEFAULT 0",
                "max_attempts INTEGER DEFAULT 0",
                "started_at TEXT"):
        name = col.split()[0]
        cols = [r[1] for r in con.execute("PRAGMA table_info(jobs)").fetchall()]
        if name not in cols:
            con.execute(f"ALTER TABLE jobs ADD COLUMN {col}")
    con.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
    con.commit()


def main():
    now = datetime.now(timezone.utc)
    con = bridge._jobs_db()
    _ensure_columns(con)
    con.execute("INSERT INTO meta(k, v) VALUES ('last_run', ?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (now.isoformat(),))
    con.commit()
    due = con.execute(
        "SELECT id, name, tool, arguments, attempts, max_attempts FROM jobs "
        "WHERE status='pending' AND run_at <= ?",
        (now.isoformat(),)).fetchall()
    for job_id, name, tool, args_json, attempts, max_attempts in due:
        con.execute("UPDATE jobs SET status='running', started_at=? WHERE id=?",
                    (now.isoformat(), job_id))
        con.commit()
        status, result = "done", {}
        try:
            if tool not in bridge.ALLOWED_JOB_TOOLS:
                raise ValueError(f"tool '{tool}' not allowed for scheduled jobs")
            fn = getattr(bridge, tool)  # in-process call, no HTTP round-trip
            args = json.loads(args_json)
            if not isinstance(args, dict):
                raise ValueError("job arguments must be a JSON object")
            result = fn(**args)
            json.dumps(result)  # must be JSON-serializable
        except Exception as e:
            attempts = (attempts or 0) + 1
            if attempts <= (max_attempts or 0):
                # transient failure: requeue with exponential backoff
                delay = RETRY_BASE_SECONDS * (2 ** (attempts - 1))
                run_at = (now + timedelta(seconds=delay)).isoformat()
                con.execute("UPDATE jobs SET status='pending', run_at=?, "
                            "attempts=?, started_at=NULL WHERE id=?",
                            (run_at, attempts, job_id))
                con.commit()
                status, result = "retrying", {
                    "error": str(e)[:500],
                    "attempt": attempts,
                    "next_run_at": run_at,
                }
            else:
                status = "error"
                result = {"error": str(e)[:500], "attempts": attempts}
        if status != "retrying":
            con.execute("UPDATE jobs SET status=?, result=?, attempts=? WHERE id=?",
                        (status, json.dumps(result, default=str),
                         attempts or 0, job_id))
            con.commit()
        else:
            # record the transient error on the job row for visibility
            con.execute("UPDATE jobs SET result=? WHERE id=?",
                        (json.dumps(result, default=str), job_id))
            con.commit()
        line = json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id, "name": name, "tool": tool, "status": status,
        })
        try:
            with open(OUTBOX, "a") as f:
                f.write(line + "\n")
        except Exception:
            traceback.print_exc()
    con.close()


if __name__ == "__main__":
    main()
