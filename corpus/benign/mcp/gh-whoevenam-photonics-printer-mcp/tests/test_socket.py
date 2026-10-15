"""Real local Unix sockets and streamed SSH helper; no physical printer I/O."""
import copy
import json
import re
import shlex
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from printer_client import SSHPrinter, mock_state
from printer_watchdog import handle
from simple_runner import fw, bc, x, y, z

SQUARE = [fw(x, 50), fw(y, 50), bc(x, 50), bc(y, 50)]
REAL_RUN = subprocess.run


class Handler(socketserver.BaseRequestHandler):
    def setup(self):
        self.send_lock = threading.Lock()

    def reply(self, ident, result=None, error=None):
        response = {'id': ident, 'error': error} if error else {'id': ident, 'result': result or {}}
        try:
            with self.send_lock:
                self.request.sendall(json.dumps(response).encode() + b'\x03')
        except OSError:
            pass

    def motion(self, ident, script):
        rows = script.splitlines()
        targets = []
        with self.server.state_lock:
            current = self.server.state['toolhead']['position'][:3]
        for row in rows[1:-1]:
            match = re.fullmatch(r'G1 X(-?\d+\.\d{3}) Y(-?\d+\.\d{3}) F(\d+\.\d{6})', row)
            z_match = re.fullmatch(r'G1 Z(-?\d+\.\d{3}) F(\d+\.\d{6})', row)
            if match:
                current[:2] = [float(v) for v in match.groups()[:2]]
                speed = float(match.group(3)) / 60
            elif z_match:
                current[2] = float(z_match.group(1))
                speed = float(z_match.group(2)) / 60
            else:
                self.reply(ident, error='Invalid movement script')
                return
            targets.append((current[:], speed))
        with self.server.state_lock:
            for obj, field in (('toolhead', 'position'), ('gcode_move', 'position'), ('gcode_move', 'gcode_position')):
                self.server.state[obj][field][:3] = targets[-1][0]
            if self.server.startup_zero_delay:
                self.server.state['motion_report']['live_position'][:3] = [0., 0., 0.]
                self.server.state['motion_report']['live_velocity'] = 0.
        self.server.entered.set()
        if self.server.startup_zero_delay:
            time.sleep(self.server.startup_zero_delay)
        for target, speed in targets:
            if self.server.stopped.is_set():
                self.reply(ident, error='Shutdown')
                return
            with self.server.state_lock:
                live = self.server.state['motion_report']
                live['live_position'][:3] = self.server.fault_position if self.server.fault else target
                live['live_velocity'] = speed
            time.sleep(0.15)
        with self.server.state_lock:
            self.server.state['motion_report']['live_velocity'] = 0.0
        self.reply(ident, {})

    def handle(self):
        buffer = b''
        while True:
            try:
                data = self.request.recv(65536)
            except OSError:
                return
            if not data:
                return
            buffer += data
            while b'\x03' in buffer:
                frame, buffer = buffer.split(b'\x03', 1)
                message = json.loads(frame)
                ident, method = message['id'], message['method']
                params = message.get('params', {})
                self.server.calls.append((method, params))
                if method == 'gcode/script':
                    threading.Thread(target=self.motion, args=(ident, params['script']), daemon=True).start()
                    continue
                with self.server.state_lock:
                    if method == 'objects/list':
                        result = {'objects': list(self.server.state)}
                    elif method == 'objects/query':
                        result = {'status': copy.deepcopy(self.server.state), 'eventtime': time.monotonic()}
                    elif method == 'emergency_stop':
                        self.server.state['webhooks']['state'] = 'shutdown'
                        self.server.stopped.set()
                        result = {}
                    else:
                        self.reply(ident, error='Unknown method')
                        continue
                self.reply(ident, result)


class SocketTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict('os.environ', {'SSH_HOST': 'printer.example.test'})
        environment.start()
        self.addCleanup(environment.stop)
        # Keep Unix-socket paths short on macOS and usable on Linux.
        self.temp = tempfile.TemporaryDirectory(prefix='pp-', dir='/tmp')
        self.path = str(Path(self.temp.name) / 'api.sock')
        self.lock_path = str(Path(self.temp.name) / 'guard.lock')
        self.server = socketserver.ThreadingUnixStreamServer(self.path, Handler)
        self.server.daemon_threads = True
        self.server.state_lock = threading.Lock()
        self.server.state, self.server.calls = mock_state(), []
        self.server.fault = False
        self.server.startup_zero_delay = 0.0
        self.server.fault_position = [201., 100., 5.]
        self.server.entered, self.server.stopped = threading.Event(), threading.Event()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.stopped.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def request(self):
        return {'action': 'run', 'steps': SQUARE, 'speed_mm_s': 20, 'expected_start': [100, 100, 5]}

    def test_complete_sequence_and_live_queries_share_one_connection(self):
        result = handle(self.request(), self.path, self.lock_path)
        self.assertTrue(result['ok'], result)
        commands = [p['script'] for m, p in self.server.calls if m == 'gcode/script']
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].count('G1 '), 4)
        self.assertEqual(commands[0].count('M400'), 1)
        self.assertGreater(sum(m == 'objects/query' for m, _ in self.server.calls), 2)

    def test_xy_entry_then_square_with_z_unhomed(self):
        from test_xy import home_state
        self.server.state = home_state()
        preview = handle({'action': 'xy-start-preview'}, self.path, self.lock_path)
        self.assertFalse(any(m == 'gcode/script' for m, _ in self.server.calls))
        result = handle({'action': 'xy-start', 'expected_start': preview['plan']['start']}, self.path, self.lock_path)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['reported_position'], [0, 0, 0])
        request = self.request()
        request['expected_start'] = [0, 0, 0]
        result = handle(request, self.path, self.lock_path)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['reported_position'], [0, 0, 0])
        self.assertFalse(self.server.stopped.is_set())

    def test_out_of_bounds_live_position_causes_dedicated_stop(self):
        self.server.fault = True
        result = handle(self.request(), self.path, self.lock_path)
        self.assertFalse(result['ok'])
        self.assertTrue(result['stop_confirmed'], result)
        self.assertTrue(self.server.stopped.is_set())

    def test_transient_startup_zero_recovers_over_real_socket(self):
        self.server.startup_zero_delay = 0.15
        result = handle(self.request(), self.path, self.lock_path)
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['startup_zero_report_seen'])
        self.assertFalse(self.server.stopped.is_set())

    def test_persistent_startup_zero_requests_stop_over_real_socket(self):
        self.server.startup_zero_delay = 0.7
        result = handle(self.request(), self.path, self.lock_path)
        self.assertFalse(result['ok'], result)
        self.assertIn('startup window', result['error'])
        self.assertTrue(result['stop_confirmed'])
        self.assertTrue(self.server.stopped.is_set())

    def test_z_out_of_bounds_causes_dedicated_stop(self):
        self.server.fault = True
        self.server.fault_position = [100., 100., 235.1]
        request = self.request()
        request['steps'] = [fw(z, 5), bc(z, 5)]
        result = handle(request, self.path, self.lock_path)
        self.assertFalse(result['ok'])
        self.assertTrue(result['stop_confirmed'], result)
        self.assertTrue(self.server.stopped.is_set())

    def test_z_raise_lower_and_mixed_sequence(self):
        request = self.request()
        request['steps'] = [fw(z, 5), fw(x, 5), bc(z, 2)]
        request['z_speed_mm_s'] = 1
        result = handle(request, self.path, self.lock_path)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['reported_position'], [105., 100., 8.])

    def test_second_runner_rejected_and_stop_bypasses_lock(self):
        results = []
        worker = threading.Thread(target=lambda: results.append(handle(self.request(), self.path, self.lock_path)))
        worker.start()
        self.assertTrue(self.server.entered.wait(2))
        with self.assertRaisesRegex(ValueError, 'already active'):
            handle(self.request(), self.path, self.lock_path)
        self.assertTrue(handle({'action': 'stop'}, self.path, self.lock_path)['stop_confirmed'])
        worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertFalse(results[0]['ok'])

    def test_streamed_code_and_json_transport(self):
        printer = SSHPrinter()
        printer.python = sys.executable
        original_source = printer.source()
        # Substitute only fixed test paths in the streamed watchdog source.
        source = original_source.replace('/tmp/klippy_uds', self.path).replace('/tmp/photonics-simple-motion.lock', self.lock_path)
        def fake_ssh(argv, **kwargs):
            self.assertIn('ProxyCommand=false', argv)
            if '-O' in argv:
                return subprocess.CompletedProcess(argv, 0, '', '')
            # Model an embedded SSH server's exec-command size limit. Code and
            # large requests must travel on stdin, not in the command string.
            if len(argv[-1].encode()) > 9000:
                return subprocess.CompletedProcess(argv, 255, '', '')
            self.assertLess(len(argv[-1].encode()), 512)
            self.assertGreater(len(kwargs['input'].encode()), 9000)
            return REAL_RUN(shlex.split(argv[-1]), **kwargs)
        with patch.object(printer, 'source', return_value=source), patch('printer_client.subprocess.run', side_effect=fake_ssh):
            self.assertTrue(printer.request({'action': 'status'})['ok'])
            preview = printer.request({'action': 'preview', 'steps': [fw(x, 0.1), bc(x, 0.1)] * 500,
                                       'speed_mm_s': 20})
            self.assertEqual(len(preview['plan']['targets']), 1000)
            self.assertFalse(any(method == 'gcode/script' for method, _ in self.server.calls))
            request = self.request()
            request['steps'] = [fw(z, 5), fw(x, 5), bc(z, 2)]
            request['z_speed_mm_s'] = 1
            result = printer.request(request)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['reported_position'], [105., 100., 8.])


if __name__ == '__main__':
    unittest.main()
