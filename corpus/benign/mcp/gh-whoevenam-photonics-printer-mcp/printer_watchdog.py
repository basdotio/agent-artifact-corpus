"""Runs beside Klipper via SSH; no firmware installation. Python 3.8 compatible."""
import fcntl
import json
import os
import re
import signal
import socket
import sys
import time

from printer_policy import MAX_Z_SPEED, SafetyError, check_execution_state, check_state, mesh_active, number, plan, plan_xy_start, same_position, startup_zero_report

SOCKET_PATH = '/tmp/klippy_uds'
LOCK_PATH = '/tmp/photonics-simple-motion.lock'
POLL_INTERVAL = 0.10
RESPONSE_TIMEOUT = 1.0
STARTUP_ZERO_WINDOW = 0.5
MAX_BYTES = 1048576


class API:
    def __init__(self, path=SOCKET_PATH):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(RESPONSE_TIMEOUT)
        try:
            self.sock.connect(path)
        except BaseException:
            self.sock.close()
            raise
        self.buffer, self.replies, self.counter = b'', {}, 0

    def close(self):
        self.sock.close()

    def send(self, method, params=None):
        self.counter += 1
        message = {'id': self.counter, 'method': method, 'params': params or {}}
        self.sock.sendall(json.dumps(message, allow_nan=False).encode() + b'\x03')
        return self.counter

    def result(self, ident):
        reply = self.replies.pop(ident)
        if 'error' in reply:
            raise RuntimeError('Klipper rejected request: ' + str(reply['error']))
        if not isinstance(reply.get('result'), dict):
            raise RuntimeError('Invalid Klipper response')
        return reply['result']

    def wait(self, ident, timeout=RESPONSE_TIMEOUT):
        deadline = time.monotonic() + timeout
        while ident not in self.replies:
            while b'\x03' not in self.buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Klipper status/response timeout')
                self.sock.settimeout(remaining)
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise RuntimeError('Klipper socket closed')
                self.buffer += chunk
                if len(self.buffer) > MAX_BYTES:
                    raise RuntimeError('Oversized Klipper response')
            frame, self.buffer = self.buffer.split(b'\x03', 1)
            reply = json.loads(frame)
            if not isinstance(reply, dict) or not isinstance(reply.get('id'), int):
                raise RuntimeError('Invalid Klipper response envelope')
            self.replies[reply['id']] = reply
            if len(self.replies) > 16:
                raise RuntimeError('Unexpected Klipper response backlog')
        return self.result(ident)

    def call(self, method, params=None, timeout=RESPONSE_TIMEOUT):
        deadline = time.monotonic() + timeout
        self.sock.settimeout(timeout)
        ident = self.send(method, params)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Klipper status/response timeout')
        return self.wait(ident, remaining)


def query_objects(api):
    available = api.call('objects/list').get('objects')
    if not isinstance(available, list):
        raise SafetyError('Printer object list is unavailable')
    wanted = ('webhooks', 'print_stats', 'toolhead', 'gcode_move', 'motion_report',
              'heater_bed', 'extruder', 'bed_mesh')
    return {name: None for name in wanted if name in available}


def snapshot(api, objects, timeout=RESPONSE_TIMEOUT):
    result = api.call('objects/query', {'objects': objects}, timeout=timeout)
    if not isinstance(result.get('status'), dict):
        raise SafetyError('Printer status is unavailable')
    eventtime = number(result.get('eventtime'), 'Status timestamp')
    return result['status'], eventtime


def emergency_stop(path=SOCKET_PATH):
    api = None
    try:
        api = API(path)
        api.call('emergency_stop')
        return True
    except Exception:
        return False
    finally:
        if api is not None:
            api.close()


def execute(api, objects, request, stop, poll_interval=POLL_INTERVAL):
    """One queued script; monitoring uses the same local socket, without SSH gaps."""
    state, stamp = snapshot(api, objects)
    prepared = (plan_xy_start(state) if request.get('action') == 'xy-start' else
                plan(state, request['steps'], request['speed_mm_s'], request.get('z_speed_mm_s', MAX_Z_SPEED)))
    if not same_position(prepared['start'], request['expected_start']):
        raise SafetyError('Position changed since preview; preview again')
    attempted = False
    try:
        dispatched_at = time.monotonic()
        deadline = dispatched_at + prepared['timeout']
        startup_deadline = dispatched_at + STARTUP_ZERO_WINDOW
        startup_open = True
        startup_zero_seen = False
        attempted = True
        move_id = api.send('gcode/script', {'script': prepared['script']})
        completed_at = None
        while True:
            now = time.monotonic()
            if now > deadline:
                raise TimeoutError('Sequence exceeded watchdog deadline')
            query_timeout = RESPONSE_TIMEOUT
            if startup_open:
                remaining = startup_deadline - now
                if remaining <= 0:
                    raise SafetyError('No confirmed live position within the 0.5-second startup window')
                query_timeout = min(query_timeout, remaining)
            state, next_stamp = snapshot(api, objects, timeout=query_timeout)
            observed_at = time.monotonic()
            if next_stamp <= stamp:
                raise SafetyError('Status timestamp did not advance')
            stamp = next_stamp
            if startup_open and observed_at >= startup_deadline:
                raise SafetyError('No confirmed live position within the 0.5-second startup window')
            allow_zero = startup_open and startup_zero_report(state)
            if allow_zero:
                startup_zero_seen = True
            else:
                startup_open = False
            queued, live = check_execution_state(state, prepared, allow_startup_zero=allow_zero)
            if move_id in api.replies:
                api.result(move_id)  # M400 completed, or Klipper rejected the script.
                completed_at = time.monotonic()
            if completed_at is not None:
                if (not allow_zero and same_position(queued, prepared['end']) and same_position(live, prepared['end'])
                        and state['motion_report']['live_velocity'] <= 0.001):
                    check_execution_state(state, prepared, stationary=True)
                    return {'ok': True, 'reported_position': live, 'commands': len(prepared['targets']),
                            'watchdog': 'active during execution', 'simulated': False,
                            'startup_zero_report_seen': startup_zero_seen}
                if time.monotonic() - completed_at > 1.5:
                    raise SafetyError('Final reported position does not match the plan')
            delay = poll_interval
            if startup_open:
                delay = min(delay, max(0.0, startup_deadline - time.monotonic()))
            time.sleep(delay)
    except BaseException as exc:
        if not attempted:
            raise
        confirmed = stop()
        return {'ok': False, 'error': str(exc) or type(exc).__name__,
                'command_may_have_executed': True, 'stop_requested': True,
                'stop_confirmed': confirmed,
                'startup_zero_report_seen': startup_zero_seen,
                'message': 'Inspect printer; manual recovery required. Do not automatically retry.'}


def validate_request(request):
    if not isinstance(request, dict):
        raise SafetyError('Invalid request')
    action = request.get('action')
    keys = {'status': {'action'}, 'stop': {'action'}, 'mesh-clear': {'action'},
            'xy-start-preview': {'action'}, 'xy-start': {'action', 'expected_start'},
            'mesh-load': {'action', 'profile'},
            'preview': {'action', 'steps', 'speed_mm_s'},
            'run': {'action', 'steps', 'speed_mm_s', 'expected_start'}}
    optional = {'z_speed_mm_s'} if action in ('preview', 'run') else set()
    if action not in keys or not keys[action] <= set(request) or not set(request) <= keys[action] | optional:
        raise SafetyError('Unsupported action or fields')
    if action == 'mesh-load' and (not isinstance(request['profile'], str) or
                                 not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', request['profile'])):
        raise SafetyError('Invalid mesh profile name')
    return action


def handle(request, path=SOCKET_PATH, lock_path=LOCK_PATH):
    action = validate_request(request)
    if action == 'stop':
        confirmed = emergency_stop(path)
        return {'ok': confirmed, 'stop_requested': True, 'stop_confirmed': confirmed}
    lock = api = None
    try:
        if action in ('run', 'xy-start', 'mesh-clear', 'mesh-load'):
            # Protect against concurrent simplified runners; other printer apps
            # do not participate in this lock and must remain idle.
            lock = open(lock_path, 'a')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise SafetyError('Another simplified runner is already active')
        api = API(path)
        objects = query_objects(api)
        if action in ('run', 'xy-start'):
            return execute(api, objects, request, lambda: emergency_stop(path))
        state, _ = snapshot(api, objects)
        if action == 'status':
            return {'ok': True, 'state': state, 'simulated': False}
        if action == 'xy-start-preview':
            return {'ok': True, 'plan': plan_xy_start(state), 'simulated': False}
        if action == 'preview':
            return {'ok': True, 'plan': plan(state, request['steps'], request['speed_mm_s'],
                                            request.get('z_speed_mm_s', MAX_Z_SPEED)), 'simulated': False}
        # Mesh management is explicit; coordinate mismatch is expected before clear.
        check_state(state)
        live = state['motion_report']
        if live['live_velocity'] > 0.001 or not same_position(live['live_position'], state['toolhead']['position']):
            raise SafetyError('Mesh changes require a stationary printer')
        mesh_active(state.get('bed_mesh'))  # Require a valid report before changing it.
        script = 'BED_MESH_CLEAR' if action == 'mesh-clear' else 'BED_MESH_PROFILE LOAD=' + request['profile']
        try:
            api.call('gcode/script', {'script': script})
            after, _ = snapshot(api, objects)
        except Exception as exc:
            return {'ok': False, 'error': str(exc), 'command_may_have_executed': True}
        active = mesh_active(after.get('bed_mesh'))
        if action == 'mesh-clear' and active:
            raise SafetyError('Mesh still active after clear; inspect before retrying')
        if action == 'mesh-load' and (not active or after['bed_mesh']['profile_name'] != request['profile']):
            raise SafetyError('Unexpected loaded mesh; inspect before retrying')
        return {'ok': True, 'bed_mesh': after['bed_mesh'], 'simulated': False}
    finally:
        if api is not None:
            api.close()
        if lock is not None:
            lock.close()


def interrupted(signum, frame):
    raise InterruptedError('Watchdog received signal %s' % signum)


def main():
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(sig, interrupted)
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise SafetyError('Request too large')
        result = handle(json.loads(raw))
    except Exception as exc:
        result = {'ok': False, 'error': str(exc)}
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
