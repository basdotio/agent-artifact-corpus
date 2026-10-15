"""Small explicit SOAR requests with complete evidence and no retry loop."""
from datetime import datetime, timezone
import json
import ssl
import time

import httpx

from .config import Settings
from .evidence import EvidenceStore


def positive_id(value):
    if type(value) is not int or value <= 0:
        raise ValueError('resource id must be a positive integer')
    return value


def page_params(page, page_size):
    if type(page) is not int or page < 0 or type(page_size) is not int or not 1 <= page_size <= 100:
        raise ValueError('page must be nonnegative and page_size must be 1..100')
    return {'page': page, 'page_size': page_size}


def reject_non_json_constant(value):
    raise ValueError(f'non-JSON numeric constant: {value}')


class SoarClient:
    def __init__(self, settings: Settings, *, transport=None):
        self.evidence = EvidenceStore(settings.evidence_dir)
        context = ssl.create_default_context(cafile=str(settings.ca_file) if settings.ca_file else None)
        self.http = httpx.Client(base_url=settings.base_url.rstrip('/'),
            headers={'ph-auth-token': settings.token, 'Accept': 'application/json'},
            verify=context, timeout=httpx.Timeout(settings.request_timeout, connect=min(5, settings.request_timeout)),
            follow_redirects=False, trust_env=False, transport=transport)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.http.close()

    def get_app(self, app_id):
        return self._get(f'/rest/app/{positive_id(app_id)}', {'pretty': ''})

    def list_app_actions(self, app_id, *, page=0, page_size=20):
        return self._get(f'/rest/app/{positive_id(app_id)}/actions', page_params(page, page_size))

    def get_app_action(self, app_action_id):
        return self._get(f'/rest/app_action/{positive_id(app_action_id)}')

    def get_artifact(self, artifact_id):
        return self._get(f'/rest/artifact/{positive_id(artifact_id)}')

    def export_playbook(self, playbook_id):
        result = self.request('GET', f'/rest/playbook/{positive_id(playbook_id)}/export', binary_response=True)
        if not result.get('error'):
            from .bundles import read_bundle
            try:
                name, files, document = read_bundle(self.evidence.raw(result['evidence']['id']))
                result.update(playbook_name=name, members=[dict(name=n, bytes=len(b)) for n, b in files.items()])
            except ValueError as exc:
                result['error'] = dict(kind='invalid_playbook_bundle', message=str(exc))
        return result

    def inspect_playbook_bundle(self, evidence_id):
        from .bundles import read_bundle
        name, files, document = read_bundle(self.evidence.raw(evidence_id))
        result = dict(playbook_name=name, bundle_evidence_id=evidence_id,
                      graph_fields_present=[key for key in ('nodes', 'edges') if key in document['coa']['data']])
        for kind, suffix in (('python', '.py'), ('definition', '.json')):
            receipt = self.evidence.save(files[name + suffix],
                dict(source='playbook_bundle_member', bundle_evidence_id=evidence_id, member=name + suffix))
            result[kind] = dict(evidence=receipt, view=self.evidence.read(receipt['id']))
        return result

    def list_artifacts(self, container_id, *, page=0, page_size=20):
        return self._get(f'/rest/container/{positive_id(container_id)}/artifacts', page_params(page, page_size))

    def get_run(self, kind, run_id):
        if kind not in ('playbook_run', 'action_run', 'app_run'):
            raise ValueError('unsupported run kind')
        return self._get(f'/rest/{kind}/{positive_id(run_id)}')

    def playbook_logs(self, run_id, *, page=0, page_size=20, message_contains=None):
        path = f'/rest/playbook_run/{positive_id(run_id)}/log'
        params = page_params(page, page_size)
        if message_contains is not None:
            if not isinstance(message_contains, str):
                raise ValueError('message filter must be a string')
            params['_filter_message__icontains'] = json.dumps(message_contains)
        return self._get(path, params)

    def list_records(self, kind, *, page=0, page_size=20, parent_id=None):
        if kind not in ('app', 'action_run', 'app_run'):
            raise ValueError('unsupported list kind')
        params = page_params(page, page_size)
        if kind != 'app':
            parent = 'playbook_run' if kind == 'action_run' else 'action_run'
            params['_filter_' + parent] = positive_id(parent_id)
        elif parent_id is not None:
            raise ValueError('app list has no parent run')
        return self._get(f'/rest/{kind}', params)

    def action_results(self, app_run_id, *, page=0, page_size=20):
        return self._get(f'/rest/app_run/{positive_id(app_run_id)}/action_result',
                         page_params(page, page_size))

    def _get(self, path, params=None):
        return self.request('GET', path, params=params)

    def request(self, method, path, *, params=None, body=None, binary_response=False):
        started = time.monotonic()
        metadata = dict(method=method, path=path, params=params,
                        started_at=datetime.now(timezone.utc).isoformat())
        if body is not None:
            metadata['request_body'] = body
        error = None
        status, complete, source = None, False, 'http_response'
        content_type = None
        chunks = []
        try:
            with self.http.stream(method, path, params=params, json=body) as response:
                status = response.status_code
                content_type = response.headers.get('content-type')
                for chunk in response.iter_bytes():
                    chunks.append(chunk)
                complete = True
            if not 200 <= status < 300:
                error = dict(kind='http_error', message=f'SOAR returned HTTP {status}; no retry or redirect followed')
        except httpx.TransportError as exc:
            error = dict(kind='transport_error', exception_type=type(exc).__name__, message=str(exc))
        raw = b''.join(chunks)
        if status is None and error is not None:
            source = 'transport_diagnostic'
            raw = json.dumps(error, ensure_ascii=False).encode()
        result = dict(http_status=status, elapsed_seconds=time.monotonic() - started,
                      body_complete=complete, body_source=source, body_included=False, content_type=content_type)
        if binary_response and error is None and complete:
            metadata.update(http_status=status, elapsed_seconds=result['elapsed_seconds'],
                            body_complete=complete, body_source=source, content_type=content_type, error=None)
            result['evidence'] = self.evidence.save(raw, metadata)
            return result
        needs_preview = False
        try:
            if not complete:
                raise ValueError('no complete HTTP response')
            text = raw.decode('utf-8')
            body = json.loads(text, parse_constant=reject_non_json_constant)
            if len(text) <= 16000:
                result.update(body=body, body_included=True)
            else:
                result.update(preview=text[:16000], next_offset=16000,
                              offset_units='unicode_characters', total_characters=len(text))
        except (ValueError, UnicodeDecodeError):
            if error is None:
                error = dict(kind='non_json_response', message='HTTP body is not valid UTF-8 JSON; full bytes retained')
            needs_preview = True
        metadata.update(http_status=status, elapsed_seconds=result['elapsed_seconds'],
                        body_complete=complete, body_source=source, error=error)
        receipt = self.evidence.save(raw, metadata)
        result['evidence'] = receipt
        if needs_preview:
            page = self.evidence.read(receipt['id'])
            result.update(preview=page['text'], encoding=page['encoding'],
                          next_offset=page['next_offset'], offset_units=page['offset_units'])
        if error is not None:
            result['error'] = error
        return result
