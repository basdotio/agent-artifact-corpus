"""Owned SOAR resource lifecycle, not a workflow controller or verdict engine.

SQLite retains request identity before writes, so loss of the reply cannot cause
implicit replay after MCP restart. It records only this tool's remote resources.
"""
from contextlib import closing
import base64
import json
import os
from pathlib import Path
import re
import sqlite3

from .client import positive_id


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}', value):
        raise ValueError('identifier must be 1..64 lowercase letters/digits/underscores, starting with a letter')
    return value


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


class OwnedOperations:
    def __init__(self, client, namespace, source_root):
        self.client = client
        self.namespace = identifier(namespace)
        self.source_root = Path(source_root)
        if not self.source_root.is_absolute() or not self.source_root.is_dir():
            raise ValueError('playbook source root must be an existing absolute directory')
        if any(p.is_symlink() for p in [self.source_root, *self.source_root.parents]):
            raise ValueError('playbook source root must not contain symlinks')
        self.path = client.evidence.root / 'operations.sqlite3'
        if self.path.is_symlink():
            raise ValueError('operation state must not be a symlink')
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
        if self.path.stat().st_nlink != 1 or self.path.stat().st_mode & 0o077:
            raise ValueError('operation state must be private')
        binding = encoded([str(client.http.base_url), namespace, str(source_root)])
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS binding (id INTEGER PRIMARY KEY CHECK (id=1), value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, spec TEXT NOT NULL, result TEXT);
                CREATE TABLE IF NOT EXISTS names (kind TEXT, name TEXT, request_id TEXT, PRIMARY KEY(kind,name));
                CREATE TABLE IF NOT EXISTS resources (kind TEXT, id INTEGER, name TEXT NOT NULL, PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS artifact_parents (id INTEGER PRIMARY KEY, container_id INTEGER NOT NULL);
            ''')
            db.execute('INSERT OR IGNORE INTO binding VALUES (1,?)', (binding,))
            if db.execute('SELECT value FROM binding').fetchone()[0] != binding:
                raise ValueError('operation state binding differs from selected endpoint/namespace/source root')

    def inventory(self):
        with closing(sqlite3.connect(self.path)) as db:
            resources = [dict(kind=k, id=i, name=n) for k, i, n in db.execute(
                'SELECT kind,id,name FROM resources ORDER BY kind,id')]
            pending = [i for i, in db.execute('SELECT id FROM requests WHERE result IS NULL ORDER BY id')]
            unknown = [i for i, r in db.execute('SELECT id,result FROM requests WHERE result IS NOT NULL')
                       if json.loads(r).get('execution_state') == 'unknown']
        return dict(namespace=self.namespace, resources=resources,
                    pending_operation_ids=pending, unknown_operation_ids=unknown)

    def _name(self, suffix):
        return self.namespace + '_' + identifier(suffix)

    def _source_bytes(self, relative):
        path = Path(relative)
        if path.is_absolute() or not path.parts or any(p in ('.', '..') for p in path.parts):
            raise ValueError('source path must be relative within assigned source root')
        current = self.source_root
        for part in path.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError('source path must not contain symlinks')
        if not current.is_file() or current.stat().st_nlink != 1:
            raise ValueError('source must be an assigned regular file')
        return current.read_bytes()

    def _source(self, relative):
        return self._source_bytes(relative).decode('utf-8')

    def _owned(self, kind, identity):
        positive_id(identity)
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute('SELECT name FROM resources WHERE kind=? AND id=?', (kind, identity)).fetchone()
        if row is None:
            raise ValueError('resource is not owned by this scope')
        return row[0]

    def _perform(self, operation_id, spec, action, *, claim=None):
        identifier(operation_id)
        serialized = encoded(spec)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT spec,result FROM requests WHERE id=?', (operation_id,)).fetchone()
            if previous:
                if previous[0] != serialized:
                    raise ValueError('operation id already binds a different request')
                if previous[1] is not None:
                    return json.loads(previous[1])
                return dict(operation_id=operation_id, execution_state='unknown',
                    error=dict(kind='interrupted_operation', message='Prior request has no committed response; inspect retained evidence and remote state. It was not replayed.'))
            if claim and db.execute('SELECT 1 FROM names WHERE kind=? AND name=?', claim).fetchone():
                raise ValueError('resource name already belongs to an operation; use its original operation id to read back, not retry')
            db.execute('INSERT INTO requests VALUES (?,?,NULL)', (operation_id, serialized))
            if claim:
                db.execute('INSERT INTO names VALUES (?,?,?)', (*claim, operation_id))
        # Intentionally no automatic retry or exception-to-success conversion.
        result = action()
        result['operation_id'] = operation_id
        with closing(sqlite3.connect(self.path)) as db, db:
            owned = result.get('owned')
            if owned:
                db.execute('INSERT INTO resources VALUES (?,?,?)', (owned['kind'], owned['id'], owned['name']))
                if owned['kind'] == 'artifact':
                    db.execute('INSERT INTO artifact_parents VALUES (?,?)', (owned['id'], owned['container_id']))
            db.execute('UPDATE requests SET result=? WHERE id=?', (encoded(result), operation_id))
        return result

    def _body(self, result):
        if result.get('error') or not result['body_complete']:
            return None
        return json.loads(self.client.evidence.raw(result['evidence']['id']))

    def _write(self, method, path, body=None, *, created=None):
        result = self.client.request(method, path, body=body)
        data = self._body(result)
        if result.get('error'):
            # A server error can occur after applying a write. Preserve uncertainty.
            result['execution_state'] = 'unknown'
        elif isinstance(data, dict) and (data.get('failed') is True or data.get('success') is False):
            result.update(execution_state='rejected', error=dict(kind='operation_rejected', message='SOAR rejected the request; inspect the complete body'))
        elif created:
            key = 'playbook_run_id' if created[0] == 'playbook_run' else 'id'
            identity = data.get(key) if isinstance(data, dict) else None
            if isinstance(identity, str) and re.fullmatch('[1-9][0-9]*', identity):
                identity = int(identity)
            if type(identity) is not int or identity <= 0:
                result.update(execution_state='unknown', error=dict(kind='missing_created_id', message='Reply does not identify the created resource; no replay or adoption'))
            else:
                result.update(execution_state='response_received', owned=dict(kind=created[0], id=identity, name=created[1]))
        else:
            result['execution_state'] = 'response_received'
        return result

    def _create(self, operation_id, kind, path, body, *, container_id=None):
        name = body['name']
        def action():
            if container_id is not None:
                parent = self.get_owned('container', container_id)
                if parent.get('error'):
                    return dict(execution_state='not_sent', preflight=parent, error=parent['error'])
            before = self.client._get('/rest/' + kind, {'_filter_name': json.dumps(name)})
            data = self._body(before)
            if not isinstance(data, dict) or data.get('count') != 0 or data.get('data') != []:
                return dict(execution_state='not_sent', preflight=before,
                    error=dict(kind='name_conflict', message='Could not prove the selected name absent; nothing created or adopted'))
            result = self._write('POST', path, body, created=(kind, name))
            if container_id is not None and result.get('owned'):
                result['owned']['container_id'] = container_id
            return result
        return self._perform(operation_id, dict(kind=kind, path=path, body=body), action, claim=(kind, name))

    def create_asset(self, operation_id, name, app_id, configuration):
        positive_id(app_id)
        if not isinstance(configuration, dict):
            raise ValueError('asset configuration must be an object')
        return self._create(operation_id, 'asset', '/rest/asset', dict(
            name=self._name(name), app_id=app_id, configuration=configuration, disabled=False))

    def create_container(self, operation_id, name, label):
        if not isinstance(label, str) or not label.strip():
            raise ValueError('container label must be nonempty')
        return self._create(operation_id, 'container', '/rest/container', dict(
            name=self._name(name), label=label, source_data_identifier=self._name(name), data={}, run_automation=False))

    def save_playbook(self, operation_id, name, source_path, scm_id, labels, python_version):
        positive_id(scm_id)
        if not labels or any(not isinstance(v, str) or not v.strip() for v in labels):
            raise ValueError('playbook labels must be nonempty strings')
        if not isinstance(python_version, str) or not re.fullmatch(r'3\.[0-9]+', python_version):
            raise ValueError('select the installed Python 3 version explicitly')
        name = self._name(name)
        body = dict(name=name, python=self._source(source_path), labels=labels,
                    coa_data=dict(name=name), scm=scm_id, active=False,
                    draft_mode=False, python_version=python_version)
        return self._create(operation_id, 'playbook', '/coa/playbooks/', body)

    def create_artifact(self, operation_id, name, container_id, cef, label, cef_types=None):
        self._owned('container', container_id)
        if not isinstance(cef, dict) or (cef_types is not None and not isinstance(cef_types, dict)):
            raise ValueError('CEF and CEF types must be JSON objects')
        if not isinstance(label, str) or not label.strip():
            raise ValueError('artifact label must be nonempty')
        body = dict(name=self._name(name), container_id=container_id, cef=cef,
                    label=label, source_data_identifier=self._name(name), run_automation=False)
        if cef_types is not None:
            body['cef_types'] = cef_types
        return self._create(operation_id, 'artifact', '/rest/artifact', body, container_id=container_id)

    def import_playbook(self, operation_id, source_path, scm_id):
        from .bundles import validate_import
        positive_id(scm_id)
        raw = self._source_bytes(source_path)
        name = validate_import(raw, self.namespace)
        body = dict(playbook=base64.b64encode(raw).decode('ascii'), scm_id=scm_id, force=False)
        params = {'_filter_name': json.dumps(name), '_filter_scm': scm_id}
        def action():
            before = self.client._get('/rest/playbook', params)
            data = self._body(before)
            if not isinstance(data, dict) or data.get('count') != 0 or data.get('data') != []:
                return dict(execution_state='not_sent', preflight=before,
                            error=dict(kind='name_conflict', message='Cannot prove destination absent; no import sent'))
            result = self._write('POST', '/rest/import_playbook', body)
            if result.get('error'):
                return result
            ack = self._body(result)
            if not isinstance(ack, dict) or ack.get('success') is not True:
                result.update(execution_state='unknown', error=dict(kind='import_unconfirmed', message='No explicit import acknowledgment; do not replay'))
                return result
            # This documented API has no created ID. Resolve only after positive
            # acknowledgment, an absent-name preflight and force=False creation.
            after = self.client._get('/rest/playbook', params)
            result['identity_readback'] = after
            observed = self._body(after)
            rows = observed.get('data') if isinstance(observed, dict) else None
            row = rows[0] if isinstance(rows, list) and len(rows) == 1 and observed.get('count') == 1 else None
            if (not isinstance(row, dict) or row.get('name') != name or row.get('scm') != scm_id
                    or type(row.get('id')) is not int or row['id'] <= 0):
                result.update(execution_state='unknown', error=dict(kind='import_identity_unknown', message='Import acknowledged but exact unique identity is unconfirmed; no replay or adoption'))
                return result
            result['owned'] = dict(kind='playbook', id=row['id'], name=name)
            if row.get('active') is not False:
                result['error'] = dict(kind='import_not_inactive', message='New owned Playbook is not confirmed inactive; inspect and clean it, do not execute')
            return result
        return self._perform(operation_id, dict(import_playbook=body), action, claim=('playbook', name))

    def update_artifact_cef(self, operation_id, artifact_id, cef_patch):
        self._owned('artifact', artifact_id)
        if not isinstance(cef_patch, dict):
            raise ValueError('CEF patch must be a JSON object')
        def action():
            before = self.get_owned('artifact', artifact_id)
            if before.get('error'):
                return dict(execution_state='not_sent', preflight=before, error=before['error'])
            data = self._body(before)
            if not isinstance(data, dict) or not isinstance(data.get('cef'), dict):
                return dict(execution_state='not_sent', preflight=before,
                            error=dict(kind='invalid_cef', message='Current CEF is not an object; no update sent'))
            # SOAR replaces the CEF object. Merge explicit top-level keys only.
            return self._write('POST', f'/rest/artifact/{artifact_id}',
                               dict(cef={**data['cef'], **cef_patch}, run_automation=False))
        return self._perform(operation_id, dict(update_artifact=artifact_id, cef_patch=cef_patch), action)

    def get_owned(self, kind, resource_id):
        name = self._owned(kind, resource_id)
        result = self.client._get(f'/rest/{kind}/{resource_id}')
        data = self._body(result)
        if not result.get('error') and (not isinstance(data, dict) or data.get('name') != name or data.get('id') != resource_id):
            result['error'] = dict(kind='ownership_changed', message='Remote resource no longer matches its original identity/name')
        if kind == 'artifact' and not result.get('error'):
            with closing(sqlite3.connect(self.path)) as db:
                parent = db.execute('SELECT container_id FROM artifact_parents WHERE id=?', (resource_id,)).fetchone()
            if parent is None or data.get('container') != parent[0]:
                result['error'] = dict(kind='ownership_changed', message='Artifact parent no longer matches its owned container')
            else:
                checked = self.get_owned('container', parent[0])
                if checked.get('error'):
                    result.update(error=checked['error'], parent_readback=checked)
        return result

    def delete(self, operation_id, kind, resource_id):
        if kind not in ('asset', 'container', 'playbook', 'artifact'):
            raise ValueError('unsupported owned resource kind')
        self._owned(kind, resource_id)
        def action():
            before = self.get_owned(kind, resource_id)
            if before.get('error'):
                return dict(execution_state='not_sent', preflight=before, error=before['error'])
            if kind == 'playbook':
                return self._write('POST', '/playbooks', dict(delete=True, ids=[resource_id]))
            return self._write('DELETE', f'/rest/{kind}/{resource_id}')
        return self._perform(operation_id, dict(delete=kind, id=resource_id), action)

    def start_debugger(self, operation_id, playbook_id, container_id):
        name = self._owned('playbook', playbook_id)
        self._owned('container', container_id)
        def action():
            preflight = [self.get_owned('playbook', playbook_id), self.get_owned('container', container_id)]
            if any(r.get('error') for r in preflight):
                return dict(execution_state='not_sent', preflight=preflight,
                            error=dict(kind='preflight_failed', message='Owned resource readback failed'))
            playbook = self._body(preflight[0])
            if (playbook.get('active') is not False or playbook.get('disabled') is not False
                    or playbook.get('draft_mode') is not False or playbook.get('passed_validation') is not True
                    or not playbook.get('commit_hash')):
                return dict(execution_state='not_sent', preflight=preflight,
                            error=dict(kind='vpe_not_ready', message='Saved VPE must be validated, committed, inactive and not disabled/draft'))
            body = dict(playbook_id=playbook_id, container_id=container_id, run=True,
                        test_mode=True, dbg_token=self.namespace + '_' + operation_id,
                        run_as_user=True, scope='all')
            return self._write('POST', '/rest/playbook_run', body, created=('playbook_run', name))
        return self._perform(operation_id, dict(debugger_playbook=playbook_id, container=container_id), action)

    def cancel_run(self, operation_id, run_id):
        self._owned('playbook_run', run_id)
        return self._perform(operation_id, dict(cancel_run=run_id),
            lambda: self._write('POST', f'/rest/playbook_run/{run_id}', dict(cancel=True)))
