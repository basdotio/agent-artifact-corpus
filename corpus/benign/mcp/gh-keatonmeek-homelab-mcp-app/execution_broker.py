"""Private Unix-socket command broker; no TCP listener and no shell sandbox."""
import asyncio
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import struct
import sys
import time
import uuid

MAX_FRAME = 1_048_576
MAX_OUTPUT = 131_072
MAX_JOBS = 64
MAX_RUNNING = 8


def redact(text):
    """Best effort only: arbitrary, split, encoded or unfamiliar secrets can survive."""
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?(?:-----END [^-]*PRIVATE KEY-----|$)',
                  '[REDACTED PRIVATE KEY]', text, flags=re.S)
    text = re.sub(r'\b(?:gh[pousr]_[A-Za-z0-9_]{15,}|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{15,})',
                  '[REDACTED TOKEN]', text)
    text = re.sub(r'''(?im)((?:authorization|password|passwd|client_secret|access_token|refresh_token|api_key|secret|HOMELAB_JWT_SIGNING_KEY|HOMELAB_STORAGE_ENCRYPTION_KEY)\s*["']?\s*[:=]\s*["']?)([^\s,"'}]+)''',
                  r'\1[REDACTED]', text)
    return re.sub(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b', '[REDACTED JWT]', text)


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('integer_out_of_bounds')
    return value


def absolute(value):
    if not isinstance(value, str) or not value.startswith('/') or '\0' in value:
        raise ValueError('absolute_path_required')
    return value


def private_directory(path, owner_uid):
    """Require a pre-created real directory with no symlink components."""
    path = Path(absolute(str(path)))
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('symlink_directory_refused')
    for parent in path.parents:
        info = parent.stat()
        sticky_root = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
        if info.st_uid not in (0, owner_uid) or (info.st_mode & 0o022 and not sticky_root):
            raise ValueError('unsafe_directory_ancestor')
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != owner_uid or info.st_mode & 0o077:
        raise ValueError('private_directory_required')
    return path


class Broker:
    def __init__(self, *, prefix=(), audit=None, enabled=False, python=None):
        self.prefix = list(prefix)
        self.python = python or sys.executable
        self.worker = Path(__file__).with_name('host_actions.py').read_text()
        self.jobs = collections.OrderedDict()
        self.audit = Path(audit) if audit else None
        self.enabled = enabled
        self.launch_lock = asyncio.Lock()
        self.closing = False

    def record(self, method, job_id=None, command=None, status=None):
        if not self.audit:
            return
        row = {'at': time.time(), 'method': method, 'job_id': job_id, 'status': status}
        if command is not None:
            row['command_sha256'] = hashlib.sha256(command.encode()).hexdigest()
        # Metadata only. Do not let an audit sink follow a symlink or log payloads.
        fd = os.open(self.audit, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        with os.fdopen(fd, 'a') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
                raise ValueError('unsafe_audit_file')
            if info.st_size > 2_000_000:
                raise ValueError('audit_full_rotate_offline')
            stream.write(json.dumps(row) + '\n')

    async def launch(self, method, params, timeout=30, output_limit=65536):
        integer(timeout, 1, 3600)
        integer(output_limit, 1024, MAX_OUTPUT)
        async with self.launch_lock:
            if self.closing:
                raise RuntimeError('broker_shutting_down')
            if sum(j['state'] == 'running' for j in self.jobs.values()) >= MAX_RUNNING:
                raise ValueError('concurrency_limit')
            if len(self.jobs) >= MAX_JOBS:
                done = next((key for key, j in self.jobs.items() if j['task'].done()), None)
                if done is None:
                    raise ValueError('job_capacity')
                del self.jobs[done]
            job_id = uuid.uuid4().hex
            self.record(method, job_id, params.get('command'), status='starting')
            process = await asyncio.create_subprocess_exec(
                *self.prefix, self.python, '-I', '-B', '-c', self.worker,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT, start_new_session=True,
                env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
            job = {'id': job_id, 'state': 'running', 'started_at': time.time(),
                   'process': process, 'raw': bytearray(), 'output_limit': output_limit,
                   'truncated': False, 'returncode': None, 'method': method}
            self.jobs[job_id] = job
            job['task'] = asyncio.create_task(self.monitor(job, timeout))
            try:
                process.stdin.write(json.dumps({'method': method, 'params': params}, ensure_ascii=False).encode() + b'\n')
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                process.stdin.close()
            return job_id

    async def monitor(self, job, timeout):
        async def read():
            while chunk := await job['process'].stdout.read(8192):
                room = job['output_limit'] - len(job['raw'])
                job['raw'].extend(chunk[:max(0, room)])
                if len(chunk) > room:
                    job['truncated'] = True
        reader = asyncio.create_task(read())
        try:
            await asyncio.wait_for(job['process'].wait(), timeout)
            if job['state'] == 'running':
                job['state'] = 'completed'
        except asyncio.TimeoutError:
            if job['state'] == 'running':
                job['state'] = 'timed_out'
            await self.stop(job)
        finally:
            try:
                await asyncio.wait_for(reader, 2)
            except asyncio.TimeoutError:
                job['truncated'] = True
            job['returncode'] = job['process'].returncode
            job['finished_at'] = time.time()
            try:
                self.record(job['method'], job['id'], status=job['state'])
            except (OSError, ValueError):
                job['audit_error'] = True

    async def stop(self, job):
        # A process-group kill cannot catch deliberately detached descendants.
        try:
            os.killpg(job['process'].pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(job['process'].wait(), 2)
        except asyncio.TimeoutError:
            try:
                os.killpg(job['process'].pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(job['process'].wait(), 2)
            except asyncio.TimeoutError:
                job['truncated'] = True

    def result(self, job_id, include_output=True):
        if not isinstance(job_id, str) or not re.fullmatch('[0-9a-f]{32}', job_id):
            raise ValueError('invalid_job_id')
        j = self.jobs[job_id]
        out = {k: j.get(k) for k in ['id', 'state', 'started_at', 'finished_at', 'returncode', 'truncated']}
        if j.get('audit_error'):
            out['audit_error'] = True
        if include_output:
            raw = bytes(j['raw']).decode('utf-8', errors='replace')
            if j['method'] == 'file_read':
                try:
                    value = json.loads(raw)
                    if 'text' in value:
                        value['text'] = redact(value['text'])
                    out['output'] = json.dumps(value, ensure_ascii=False)
                except ValueError:
                    out['output'] = '[File response exceeded decoding bounds; use a smaller read limit]'
            else:
                out['output'] = redact(raw)
        return out

    async def handle(self, request):
        if not self.enabled:
            raise PermissionError('execution_disabled')
        if not isinstance(request, dict) or not isinstance(request.get('params', {}), dict):
            raise ValueError('invalid_request')
        method = request['method']
        p = request.get('params', {})
        if method in ('job_status', 'job_output', 'job_cancel'):
            result = self.result(p['job_id'], method == 'job_output')
            if method != 'job_cancel':
                return result
            j = self.jobs[p['job_id']]
            if j['state'] == 'running':
                j['state'] = 'cancelled'
                await self.stop(j)
                await asyncio.shield(j['task'])
            self.record(method, p['job_id'])
            return self.result(p['job_id'], False)
        if method in ('command_run', 'command_start'):
            if not isinstance(p.get('command'), str) or not 1 <= len(p['command']) <= 32768 or '\0' in p['command']:
                raise ValueError('command_bounds')
            absolute(p.get('cwd'))
            op = 'command'
        elif method in ('file_read', 'file_write', 'file_move'):
            op = method
            absolute(p.get('path'))
            if method == 'file_read':
                integer(p.get('limit', 65536), 1, 65536)
                integer(p.get('offset', 0), 0, 2**63 - 1)
            if method == 'file_write':
                if not isinstance(p.get('text'), str) or len(p['text'].encode()) > 131072:
                    raise ValueError('write_bounds')
                integer(p.get('mode', 384), 0, 511)
                if type(p.get('create_parents', False)) is not bool:
                    raise ValueError('boolean_required')
            if method == 'file_move':
                absolute(p.get('destination'))
                if type(p.get('overwrite', False)) is not bool:
                    raise ValueError('boolean_required')
        else:
            raise ValueError('unknown_method')
        job = await self.launch(op, p, p.get('timeout', 30),
                                p.get('output_limit', 65536) if op == 'command' else MAX_OUTPUT)
        if method != 'command_start':
            await asyncio.shield(self.jobs[job]['task'])
        return self.result(job)

    async def close(self):
        async with self.launch_lock:
            self.closing = True
            jobs = list(self.jobs.values())
        for job in jobs:
            if job['state'] == 'running':
                job['state'] = 'cancelled'
                await self.stop(job)
        await asyncio.gather(*(j['task'] for j in jobs), return_exceptions=True)


def environment_options(env=None):
    env = os.environ if env is None else env
    if env.get('HOMELAB_ENABLE_EXECUTION', 'false') != 'true':
        raise ValueError('Set HOMELAB_ENABLE_EXECUTION=true to start the broker')
    mode = env.get('HOMELAB_BROKER_MODE', 'local')
    if mode not in ('local', 'host-root'):
        raise ValueError('unknown_broker_mode')
    if (os.getuid() == 0 or mode == 'host-root') and env.get('HOMELAB_ALLOW_ROOT') != 'true':
        raise ValueError('root_requires_explicit_HOMELAB_ALLOW_ROOT=true')
    if mode == 'host-root' and os.getuid() != 0:
        raise ValueError('host_root_mode_requires_uid_zero')
    prefix = [] if mode == 'local' else [
        '/usr/bin/nsenter', '--target', '1', '--mount', '--uts', '--ipc', '--net', '--pid', '--root', '--wd=/', '--']
    uid = int(env.get('HOMELAB_ALLOWED_UID', str(os.getuid())))
    integer(uid, 0, 2**32 - 2)
    path = Path(absolute(env.get('HOMELAB_BROKER_SOCKET', '/run/homelab-mcp/broker.sock')))
    return prefix, uid, path


async def main():
    os.umask(0o077)
    prefix, uid, path = environment_options()
    private_directory(path.parent, uid)
    # Do not remove an existing socket: a live or stale socket needs operator attention.
    if path.exists() or path.is_symlink():
        raise FileExistsError('broker_socket_exists')
    audit = os.environ.get('HOMELAB_AUDIT_PATH')
    if audit:
        private_directory(Path(absolute(audit)).parent, os.getuid())
    broker = Broker(prefix=prefix, audit=audit, enabled=True,
                    python='/usr/bin/python3' if prefix else sys.executable)
    active_clients = set()

    async def client(reader, writer):
        task = asyncio.current_task()
        active_clients.add(task)
        try:
            if len(active_clients) > 16:
                raise ValueError('client_limit')
            creds = writer.get_extra_info('socket').getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
            _, peer_uid, _ = struct.unpack('3i', creds)
            if peer_uid != uid:
                raise PermissionError('peer_uid_not_allowed')
            line = await asyncio.wait_for(reader.readline(), 5)
            if not line.endswith(b'\n') or len(line) > MAX_FRAME:
                raise ValueError('frame_bounds')
            result = await broker.handle(json.loads(line))
        except Exception as exc:
            result = {'error': type(exc).__name__}
        try:
            writer.write(json.dumps(result, ensure_ascii=False).encode() + b'\n')
            await asyncio.wait_for(writer.drain(), 5)
        except (OSError, asyncio.TimeoutError):
            pass
        finally:
            writer.close()
            active_clients.discard(task)

    server = await asyncio.start_unix_server(client, str(path), limit=MAX_FRAME + 1)
    os.chown(path, uid, -1)
    os.chmod(path, 0o600)
    socket_inode = path.stat().st_ino
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)
    try:
        async with server:
            await stop_event.wait()
    finally:
        await broker.close()
        for task in list(active_clients):
            task.cancel()
        await asyncio.gather(*list(active_clients), return_exceptions=True)
        if path.exists() and path.lstat().st_ino == socket_inode and stat.S_ISSOCK(path.lstat().st_mode):
            path.unlink()


if __name__ == '__main__':
    asyncio.run(main())
