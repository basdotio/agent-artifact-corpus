"""Durable task state and sanitized stage diagnostics owned by Shaniu."""
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager


class PersistentState:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            rows = db.execute('SELECT task_id,data FROM tasks').fetchall()
            for task_id, raw in rows:
                data = json.loads(raw)
                if data.get('state') not in {-1, 1}:
                    data.update(state=-1, failure_reason='service_restarted')
                    db.execute('UPDATE tasks SET data=? WHERE task_id=?', (json.dumps(data), task_id))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def update_task(self, task_id, state=4, progress=None, **kwargs):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM tasks WHERE task_id=?', (task_id,)).fetchone()
            data = json.loads(row[0]) if row else dict(task_id=task_id, progress=0)
            data.update(state=state, **kwargs)
            if progress is not None:
                data['progress'] = max(0, min(100, int(progress)))
            db.execute('INSERT OR REPLACE INTO tasks VALUES (?,?)', (task_id, json.dumps(data, ensure_ascii=False)))

    def get_task(self, task_id):
        with self.connect() as db:
            row = db.execute('SELECT data FROM tasks WHERE task_id=?', (task_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def get_all_tasks(self, page, page_size):
        with self.connect() as db:
            count = db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
            rows = db.execute('SELECT data FROM tasks ORDER BY rowid DESC LIMIT ? OFFSET ?', (page_size, (page-1)*page_size)).fetchall()
        return [json.loads(row[0]) for row in rows], count

    def delete_task(self, task_id):
        with self.connect() as db:
            db.execute('DELETE FROM tasks WHERE task_id=?', (task_id,))


def track_stage(function, stage, state):
    def run(task_id, *args, **kwargs):
        state.update_task(task_id, shaniu_stage=stage)
        try:
            result = function(task_id, *args, **kwargs)
        except Exception as error:
            reason = getattr(error, 'failure_reason', '')
            if stage != 'audio' or reason not in {'audio_fallback_failed', 'audio_online_failed'}:
                reason = stage+'_failed'
            state.update_task(task_id, state=-1, failure_reason=reason)
            raise
        llm_error = stage in {'script', 'terms'} and isinstance(result, str) and result.startswith('Error:')
        failed = not result or (stage == 'audio' and not result[0]) or llm_error
        if failed and stage != 'subtitle':
            state.update_task(task_id, state=-1, failure_reason=stage+'_failed')
        if llm_error:
            # Upstream represents model errors as nonempty strings. Never narrate
            # an error message or pass it to the stock-video search pipeline.
            return None
        if stage == 'audio' and not failed:
            maker = result[2]
            state.update_task(task_id, speech_provider=getattr(maker, 'shaniu_provider', 'upstream'),
                              speech_warning=getattr(maker, 'shaniu_warning', ''),
                              subtitle_alignment=getattr(maker, 'shaniu_alignment', 'word_boundary'))
        return result
    return run
