import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


class Conflict(ValueError):
    pass


def now():
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS members (
                    id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, owner_id TEXT NOT NULL,
                    due_at TEXT NOT NULL, priority INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open', version INTEGER NOT NULL DEFAULT 1,
                    proposed_owner TEXT, created_at TEXT NOT NULL,
                    FOREIGN KEY(owner_id) REFERENCES members(id),
                    FOREIGN KEY(proposed_owner) REFERENCES members(id));
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL, actor_id TEXT NOT NULL,
                    action TEXT NOT NULL, detail TEXT NOT NULL, at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                    task_id TEXT NOT NULL);
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def members(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute('SELECT * FROM members ORDER BY name')]

    def add_member(self, name):
        name = name.strip()
        if not 1 <= len(name) <= 60:
            raise ValueError('Name must be between 1 and 60 characters')
        with self.connection() as db:
            db.execute('INSERT OR IGNORE INTO members VALUES (?,?)', (uuid.uuid4().hex, name))
            return dict(db.execute('SELECT * FROM members WHERE name=?', (name,)).fetchone())

    @staticmethod
    def member(db, member_id):
        if not db.execute('SELECT 1 FROM members WHERE id=?', (member_id,)).fetchone():
            raise ValueError('Unknown household member')

    @staticmethod
    def task(db, task_id):
        r = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
        if not r:
            raise KeyError('Task not found')
        return dict(r)

    @staticmethod
    def log(db, task_id, actor, action, detail):
        db.execute('INSERT INTO events(task_id,actor_id,action,detail,at) VALUES (?,?,?,?,?)',
                   (task_id, actor, action, detail, now()))

    def create(self, title, owner_id, due_at, priority, request_id):
        title = title.strip()
        if not 1 <= len(title) <= 160:
            raise ValueError('Task title must be between 1 and 160 characters')
        if type(priority) is not int or priority not in (1, 2, 3):
            raise ValueError('Priority must be 1, 2 or 3')
        if not 1 <= len(request_id) <= 128:
            raise ValueError('Provide a request ID of at most 128 characters')
        due = datetime.fromisoformat(due_at)
        if due.tzinfo is None:
            raise ValueError('Due time must include its timezone')
        due_at = due.astimezone(UTC).isoformat()
        fingerprint = hashlib.sha256(json.dumps([title, owner_id, due_at, priority]).encode()).hexdigest()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            self.member(db, owner_id)
            previous = db.execute('SELECT * FROM requests WHERE request_id=?', (request_id,)).fetchone()
            if previous:
                if previous['fingerprint'] != fingerprint:
                    raise Conflict('Request ID already used for different task details')
                return self.task(db, previous['task_id'])
            task_id = uuid.uuid4().hex
            db.execute('INSERT INTO tasks(id,title,owner_id,due_at,priority,created_at) VALUES (?,?,?,?,?,?)',
                       (task_id, title, owner_id, due_at, priority, now()))
            db.execute('INSERT INTO requests VALUES (?,?,?)', (request_id, fingerprint, task_id))
            self.log(db, task_id, owner_id, 'created', title)
            return self.task(db, task_id)

    def list_tasks(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute('''
                SELECT tasks.*, members.name AS owner_name,
                target.name AS proposed_owner_name FROM tasks
                JOIN members ON owner_id=members.id
                LEFT JOIN members AS target ON proposed_owner=target.id
                ORDER BY CASE status WHEN 'done' THEN 1 ELSE 0 END, due_at, priority DESC
            ''')]

    def change(self, task_id, actor_id, version, action, target_id=None):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            self.member(db, actor_id)
            task = self.task(db, task_id)
            if task['version'] != version:
                raise Conflict('Task changed since you last read it. Refresh before confirming.')
            if task['status'] == 'done':
                raise Conflict('Completed tasks cannot be changed')
            if action == 'propose':
                if actor_id != task['owner_id']:
                    raise Conflict('Only the current owner can propose a handoff')
                self.member(db, target_id)
                if target_id == actor_id:
                    raise ValueError('Choose a different household member')
                db.execute('UPDATE tasks SET proposed_owner=?, version=version+1 WHERE id=?', (target_id, task_id))
            elif action in ('accept', 'decline'):
                if actor_id != task['proposed_owner']:
                    raise Conflict('Only the proposed recipient can respond to this handoff')
                new_owner = actor_id if action == 'accept' else task['owner_id']
                db.execute('UPDATE tasks SET owner_id=?, proposed_owner=NULL, version=version+1 WHERE id=?', (new_owner, task_id))
            elif action == 'complete':
                if actor_id != task['owner_id']:
                    raise Conflict('Only the current owner can mark this task complete')
                db.execute("UPDATE tasks SET status='done', proposed_owner=NULL, version=version+1 WHERE id=?", (task_id,))
            else:
                raise ValueError('Unknown action')
            self.log(db, task_id, actor_id, action, target_id or '')
            return self.task(db, task_id)

    def briefing(self, member_id):
        with self.connection() as db:
            self.member(db, member_id)
        tasks = self.list_tasks()
        current = now()
        owned = [t for t in tasks if t['owner_id'] == member_id and t['status'] == 'open']
        pending = [t for t in tasks if t['proposed_owner'] == member_id and t['status'] == 'open']
        overdue = [t for t in owned if t['due_at'] < current]
        task_word = 'task' if len(owned) == 1 else 'tasks'
        handoff_word = 'handoff' if len(pending) == 1 else 'handoffs'
        speech = f'You have {len(owned)} open {task_word}, {len(overdue)} overdue, and {len(pending)} {handoff_word} to review.'
        if owned:
            speech += ' Next: ' + owned[0]['title'] + '.'
        return {'spoken_summary': speech, 'open_tasks': owned, 'overdue_tasks': overdue,
                'pending_handoffs': pending, 'generated_at': current}

    def history(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute('''SELECT events.*, members.name AS actor_name
                FROM events JOIN members ON actor_id=members.id ORDER BY sequence DESC LIMIT 100''')]
