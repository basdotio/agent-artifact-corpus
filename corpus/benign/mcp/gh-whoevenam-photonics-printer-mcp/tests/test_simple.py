import ast
import contextlib
import copy
import io
import json
import subprocess
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from printer_client import MockPrinter, PrinterError, SSHPrinter, mock_state, run_prepared
from printer_policy import SafetyError, check_state, mesh_active, plan
from printer_watchdog import execute, handle, validate_request
from simple_runner import bc, fw, run, x, y, z

SQUARE = [fw(x, 50), fw(y, 50), bc(x, 50), bc(y, 50)]


class PolicyTests(unittest.TestCase):
    def test_square_is_four_moves_with_one_completion_wait(self):
        result = plan(mock_state(), SQUARE, 20)
        self.assertEqual(result['end'], [100, 100, 5])
        self.assertEqual(result['nominal_seconds'], 10)
        self.assertEqual(result['script'].count('G1 '), 4)
        self.assertEqual(result['script'].count('M400'), 1)
        self.assertEqual(result['script'].count('F1200.000000'), 4)
        self.assertNotIn(' Z', result['script'])

    def test_bad_later_target_rejects_whole_path(self):
        with self.assertRaises(SafetyError):
            plan(mock_state(), [fw(x, 50), fw(x, 51)], 20)

    def test_request_and_rounded_bounds_are_both_checked(self):
        with self.assertRaises(SafetyError):
            plan(mock_state(), [fw(x, 100.0001)], 20)
        self.assertEqual(plan(mock_state(), [fw(x, 100)], 20)['end'][0], 200)
        with self.assertRaises(SafetyError):
            plan(mock_state(), [fw(x, 0.0001)], 20)

    def test_invalid_inputs(self):
        for speed in (False, 0, -1, 21, float('inf'), float('nan'), '20', 1e-15):
            with self.subTest(speed=speed), self.assertRaises(SafetyError):
                plan(mock_state(), SQUARE, speed)
        for steps in ([], [{'axis': 'e', 'distance_mm': 1}], [{'axis': 'x', 'distance_mm': True}],
                      [{'axis': 'x', 'distance_mm': 0}], [{'axis': 'x', 'distance_mm': float('nan')}],
                      [{'axis': 'x', 'distance_mm': 1, 'gcode': 'G28'}]):
            with self.subTest(steps=steps), self.assertRaises(SafetyError):
                plan(mock_state(), steps, 20)

    def test_long_slow_sequence_rejected(self):
        with self.assertRaises(SafetyError):
            plan(mock_state(), SQUARE, 0.1)

    def test_mixed_xyz_feeds_targets_and_timing(self):
        result = plan(mock_state(), [fw(z, 5), fw(x, 50), bc(z, 5), bc(x, 50)], 20)
        self.assertEqual(result['end'], [100, 100, 5])
        self.assertEqual(result['targets'][1], [150, 100, 10])
        self.assertEqual(result['step_speeds_mm_s'], [2, 20, 2, 20])
        self.assertEqual(result['nominal_seconds'], 10)
        self.assertEqual(result['script'], 'G90\nG1 Z10.000 F120.000000\nG1 X150.000 Y100.000 F1200.000000\nG1 Z5.000 F120.000000\nG1 X100.000 Y100.000 F1200.000000\nM400')
        self.assertEqual(result['z_range'], [5, 10])
        self.assertEqual(result['z_bounds'], [0, 235])

    def test_z_requested_rounded_and_firmware_limits(self):
        for steps in ([bc(z, 5.0001)], [fw(z, 230.0001)],
                      [fw(z, 5), bc(z, 10.0001)], [fw(z, 0.0001)]):
            with self.subTest(steps=steps), self.assertRaises(SafetyError):
                plan(mock_state(), steps, 20)
        for distance, end in ((-5, 0), (230, 235)):
            result = plan(mock_state(), [{'axis': z, 'distance_mm': distance}], 20)
            self.assertEqual(result['end'][2], end)
        state = mock_state()
        state['toolhead']['axis_maximum'][2] = 9
        with self.assertRaisesRegex(SafetyError, 'firmware'):
            plan(state, [fw(z, 5)], 20)
        for height in (-0.001, 235.001):
            state = mock_state()
            for obj, field in (('toolhead', 'position'), ('motion_report', 'live_position'),
                               ('gcode_move', 'position'), ('gcode_move', 'gcode_position')):
                state[obj][field][2] = height
            with self.assertRaisesRegex(SafetyError, 'Z is outside'):
                plan(state, [fw(x, 5)], 20)

    def test_z_speed_validation_and_deadline(self):
        for speed in (False, 0, -1, 2.01, float('nan'), float('inf'), '2', 1e-15):
            with self.subTest(speed=speed), self.assertRaises(SafetyError):
                plan(mock_state(), [fw(z, 5)], 20, speed)
        result = plan(mock_state(), [fw(z, 5)], 20, 1)
        self.assertEqual(result['nominal_seconds'], 5)
        self.assertIn('F60.000000', result['script'])
        with self.assertRaisesRegex(SafetyError, 'deadline'):
            plan(mock_state(), [fw(z, 230)], 20, 1)

    def test_unsafe_initial_states(self):
        mutations = [('toolhead', 'homed_axes', ''), ('webhooks', 'state', 'shutdown'),
                     ('print_stats', 'state', 'printing'), ('heater_bed', 'target', 1),
                     ('gcode_move', 'speed_factor', 2), ('gcode_move', 'homing_origin', [1, 0, 0]),
                     ('gcode_move', 'gcode_position', [99, 100, 5]),
                     ('gcode_move', 'position', [100, 100, 5.03]),
                     ('motion_report', 'live_position', None), ('motion_report', 'live_velocity', 21),
                     ('motion_report', 'live_position', [201, 100, 5]),
                     ('toolhead', 'axis_maximum', [99, 200, 240]),
                     ('toolhead', 'position', [100, 100, float('nan')])]
        for obj, field, value in mutations:
            state = mock_state()
            state[obj][field] = value
            with self.subTest(obj=obj, field=field), self.assertRaises(SafetyError):
                plan(state, SQUARE, 20)
        state = mock_state()
        del state['motion_report']
        with self.assertRaises(SafetyError):
            plan(state, SQUARE, 20)

    def test_empty_mesh_representation(self):
        self.assertFalse(mesh_active({'profile_name': '', 'mesh_matrix': [[]]}))
        self.assertTrue(mesh_active({'profile_name': '', 'mesh_matrix': [[0.0]]}))

    def test_remote_code_is_python38_compatible(self):
        for name in ('printer_policy.py', 'printer_watchdog.py'):
            ast.parse((Path(__file__).parents[1] / name).read_text(), feature_version=(3, 8))

    def test_no_arbitrary_remote_actions(self):
        for request in ({'action': 'gcode', 'script': 'G28'},
                        {'action': 'stop', 'script': 'G28'},
                        {'action': 'mesh-load', 'profile': 'default\nG28'}):
            with self.assertRaises(SafetyError):
                validate_request(request)


class FakeAPI:
    def __init__(self, mutation=None, fail=False, stale=False, script_error=False):
        self.state, self.replies = mock_state(), {}
        self.calls, self.stamp = [], 0
        self.mutation, self.fail, self.stale, self.script_error = mutation, fail, stale, script_error

    def send(self, method, params):
        self.calls.append((method, params))
        return 1

    def call(self, method, params, timeout=1):
        if self.calls:
            if self.fail:
                raise TimeoutError('Missing telemetry')
            if self.mutation:
                self.mutation(self.state)
            self.replies[1] = {}
        self.stamp += 0 if self.stale else 1
        return {'status': copy.deepcopy(self.state), 'eventtime': self.stamp}

    def result(self, ident):
        self.replies.pop(ident)
        if self.script_error:
            raise RuntimeError('G-code failure')
        return {}


class StartupAPI(FakeAPI):
    """Advance a fake clock with each reply; repeat the last sample if needed."""
    def __init__(self, samples):
        super().__init__()
        self.samples, self.now, self.reads, self.timeouts = samples, 0.0, 0, []

    def call(self, method, params, timeout=1):
        result = super().call(method, params, timeout)
        if self.calls:
            self.timeouts.append(timeout)
            sample = self.samples[min(self.reads, len(self.samples) - 1)]
            self.reads += 1
            self.now += sample.get('elapsed', 0.1)
            for name, fields in sample.get('state', {}).items():
                result['status'][name].update(fields)
            if not sample.get('complete', False):
                self.replies.clear()
        return result


class WatchdogTests(unittest.TestCase):
    def startup_result(self, samples):
        api, stop = StartupAPI(samples), Mock(return_value=True)
        with patch('printer_watchdog.time.monotonic', side_effect=lambda: api.now):
            result = execute(api, {}, self.request(), stop, 0)
        return result, api, stop

    def test_startup_zero_recovers_without_false_completion_or_stop(self):
        zero = {'state': {'motion_report': {'live_position': [0, 0, 0, 0]}}, 'complete': True}
        result, api, stop = self.startup_result([zero, {'complete': True}])
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['startup_zero_report_seen'])
        self.assertEqual(api.reads, 2)
        self.assertEqual(api.timeouts, [0.5, 0.4])
        stop.assert_not_called()

    def test_persistent_startup_zero_stops_at_window_deadline(self):
        zero = {'state': {'motion_report': {'live_position': [0, 0, 0, 0]}}}
        result, api, stop = self.startup_result([zero])
        self.assertFalse(result['ok'])
        self.assertIn('0.5-second startup window', result['error'])
        self.assertLessEqual(api.now, 0.5)
        stop.assert_called_once()

    def test_late_first_valid_sample_cannot_extend_startup_window(self):
        result, api, stop = self.startup_result([{'elapsed': 0.501, 'complete': True}])
        self.assertFalse(result['ok'])
        self.assertIn('0.5-second startup window', result['error'])
        self.assertEqual(api.timeouts, [0.5])
        stop.assert_called_once()

    def test_startup_exception_does_not_hide_other_faults(self):
        for extra in (
            {'toolhead': {'position': [100, 100, 5.1, 0]}},
            {'toolhead': {'position': [201, 100, 5, 0]}},
            {'toolhead': {'homed_axes': ''}},
            {'heater_bed': {'target': 1}},
            {'gcode_move': {'speed_factor': 2}},
            {'motion_report': {'live_position': [100, 100, 0, 0]}},
            {'motion_report': {'live_position': [0, 0, 0, 0], 'live_velocity': 1}},
        ):
            state = {'motion_report': {'live_position': [0, 0, 0, 0]}}
            state.update(extra)
            with self.subTest(extra=extra):
                result, api, stop = self.startup_result([{'state': state}])
                self.assertFalse(result['ok'])
                self.assertEqual(api.reads, 1)
                stop.assert_called_once()

    def test_zero_before_dispatch_is_still_rejected(self):
        api, stop = FakeAPI(), Mock(return_value=True)
        api.state['motion_report']['live_position'] = [0, 0, 0, 0]
        with self.assertRaises(SafetyError):
            execute(api, {}, self.request(), stop, 0)
        self.assertEqual(api.calls, [])
        stop.assert_not_called()

    def test_normal_timeouts_resume_only_after_valid_live_sample(self):
        result, api, stop = self.startup_result([{}, {'complete': True}])
        self.assertTrue(result['ok'])
        self.assertFalse(result['startup_zero_report_seen'])
        self.assertEqual(api.timeouts, [0.5, 1.0])
        stop.assert_not_called()

    def test_zero_live_position_stops_and_reports_the_observed_values(self):
        class LaterZeroAPI(FakeAPI):
            reads = 0
            def call(self, method, params, timeout=1):
                result = super().call(method, params, timeout)
                if self.calls:
                    self.reads += 1
                    self.replies.clear()
                    if self.reads > 1:
                        result['status']['motion_report']['live_position'] = [0, 0, 0, 0]
                return result
        api, stop = LaterZeroAPI(), Mock(return_value=True)
        result = execute(api, {}, self.request(), stop, 0)
        self.assertTrue(result['stop_confirmed'])
        self.assertIn('live Z=0.000000 mm; expected Z=5.000000 mm', result['error'])
        self.assertIn('queued XYZ=[100.0, 100.0, 5.0]', result['error'])
        self.assertIn('live XYZ=[0.0, 0.0, 0.0]', result['error'])
        stop.assert_called_once()

    def request(self):
        return {'steps': SQUARE, 'speed_mm_s': 20, 'expected_start': [100, 100, 5]}

    def test_clean_completion_sends_only_one_script(self):
        api, stop = FakeAPI(), Mock(return_value=True)
        result = execute(api, {}, self.request(), stop, 0)
        self.assertTrue(result['ok'])
        self.assertEqual(len(api.calls), 1)
        stop.assert_not_called()

    def test_live_bounds_z_heater_and_state_faults_stop(self):
        changes = [('motion_report', 'live_position', [200.001, 100, 5]),
                   ('motion_report', 'live_position', [100, -0.001, 5]),
                   ('motion_report', 'live_position', [100, 100, 5.1]),
                   ('motion_report', 'live_position', [100, float('nan'), 5]),
                   ('motion_report', 'live_velocity', 21), ('heater_bed', 'target', 100),
                   ('webhooks', 'state', 'shutdown'), ('gcode_move', 'speed_factor', 2)]
        for obj, field, value in changes:
            def mutate(state):
                state[obj][field] = value
            api, stop = FakeAPI(mutate), Mock(return_value=True)
            with self.subTest(obj=obj, field=field):
                result = execute(api, {}, self.request(), stop, 0)
                self.assertFalse(result['ok'])
                self.assertTrue(result['stop_confirmed'])
                self.assertEqual(len(api.calls), 1)
                stop.assert_called_once()

    def test_missing_stale_or_error_response_requests_stop(self):
        for settings in ({'fail': True}, {'stale': True}, {'script_error': True}):
            api, stop = FakeAPI(**settings), Mock(return_value=False)
            result = execute(api, {}, self.request(), stop, 0)
            self.assertFalse(result['ok'])
            self.assertTrue(result['stop_requested'])
            self.assertFalse(result['stop_confirmed'])
            stop.assert_called_once()

    def test_z_motion_completes_at_changed_height(self):
        def mutate(state):
            for obj, field in (('toolhead', 'position'), ('motion_report', 'live_position'),
                               ('gcode_move', 'position'), ('gcode_move', 'gcode_position')):
                state[obj][field][2] = 10
        api, stop = FakeAPI(mutate), Mock(return_value=True)
        request = {'steps': [fw(z, 5)], 'speed_mm_s': 20, 'expected_start': [100, 100, 5]}
        result = execute(api, {}, request, stop, 0)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['reported_position'], [100, 100, 10])
        stop.assert_not_called()

    def test_z_queued_live_and_speed_violations_stop(self):
        request = {'steps': [fw(z, 5), bc(z, 5)], 'speed_mm_s': 20,
                   'z_speed_mm_s': 1, 'expected_start': [100, 100, 5]}
        for obj, field, value in (
                ('motion_report', 'live_position', [100, 100, -0.001]),
                ('motion_report', 'live_position', [100, 100, 235.001]),
                ('toolhead', 'position', [100, 100, 235.001]),
                ('motion_report', 'live_position', [100, 100, 10.1]),
                ('toolhead', 'position', [100, 100, 4.9]),
                ('motion_report', 'live_velocity', 1.02)):
            def mutate(state):
                state[obj][field] = value
            api, stop = FakeAPI(mutate), Mock(return_value=True)
            with self.subTest(obj=obj, value=value):
                result = execute(api, {}, request, stop, 0)
                self.assertFalse(result['ok'])
                self.assertTrue(result['stop_confirmed'])
                stop.assert_called_once()

    def test_invalid_z_later_step_prevents_dispatch(self):
        api, stop = FakeAPI(), Mock()
        request = {'steps': [fw(z, 5), bc(z, 11)], 'speed_mm_s': 20,
                   'expected_start': [100, 100, 5]}
        with self.assertRaises(SafetyError):
            execute(api, {}, request, stop, 0)
        self.assertEqual(api.calls, [])
        stop.assert_not_called()

    def test_changed_start_prevents_dispatch_without_stop(self):
        api, stop = FakeAPI(), Mock()
        request = self.request()
        request['expected_start'] = [99, 100, 5]
        with self.assertRaises(SafetyError):
            execute(api, {}, request, stop, 0)
        self.assertEqual(api.calls, [])
        stop.assert_not_called()

    def test_deadline_requests_stop(self):
        api, stop = FakeAPI(), Mock(return_value=True)
        with patch('printer_watchdog.time.monotonic', side_effect=[0, 1000]):
            result = execute(api, {}, self.request(), stop, 0)
        self.assertTrue(result['stop_requested'])

    def test_cached_final_velocity_gets_time_to_settle(self):
        class SettlingAPI(FakeAPI):
            reads = 0
            def call(self, method, params, timeout=1):
                reply = super().call(method, params, timeout)
                if self.calls:
                    self.reads += 1
                    reply['status']['motion_report']['live_velocity'] = 20.0 if self.reads == 1 else 0.0
                    if self.reads > 1:
                        self.replies.clear()
                return reply
        api, stop = SettlingAPI(), Mock(return_value=True)
        result = execute(api, {}, self.request(), stop, 0)
        self.assertTrue(result['ok'])
        self.assertEqual(api.reads, 2)
        stop.assert_not_called()

    def test_wrong_final_position_eventually_stops(self):
        class WrongFinalAPI(FakeAPI):
            completed = False
            def call(self, method, params, timeout=1):
                result = super().call(method, params, timeout)
                if self.calls:
                    for obj, field in (('toolhead', 'position'), ('motion_report', 'live_position'),
                                       ('gcode_move', 'position'), ('gcode_move', 'gcode_position')):
                        result['status'][obj][field][0] = 101
                    if self.completed:
                        self.replies.clear()
                    self.completed = True
                return result
        api, stop = WrongFinalAPI(), Mock(return_value=True)
        clock = iter([i * 0.05 for i in range(200)])
        with patch('printer_watchdog.time.monotonic', side_effect=lambda: next(clock)):
            result = execute(api, {}, self.request(), stop, 0)
        self.assertFalse(result['ok'])
        self.assertIn('Final reported position', result['error'])
        stop.assert_called_once()


class ClientTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict('os.environ', {'SSH_HOST': 'printer.example.test'})
        environment.start()
        self.addCleanup(environment.stop)

    def test_hardware_requires_explicit_host(self):
        with patch.dict('os.environ', {'SSH_HOST': ''}):
            with self.assertRaisesRegex(PrinterError, 'Set SSH_HOST'):
                SSHPrinter()

    def test_empty_ssh_255_explains_connection_failure(self):
        replies = [subprocess.CompletedProcess([], 0, '', ''),
                   subprocess.CompletedProcess([], 255, '', '')]
        with patch('printer_client.subprocess.run', side_effect=replies) as process:
            with self.assertRaisesRegex(PrinterError, 'Connection closed.*exit 255'):
                SSHPrinter().request({'action': 'status'})
        self.assertEqual(process.call_count, 2)

    def test_cli_z_speed_and_preview_report_height(self):
        output = io.StringIO()
        with patch('simple_runner.SSHPrinter', side_effect=AssertionError('SSH accessed')), contextlib.redirect_stdout(output):
            self.assertEqual(run([fw(z, 5), bc(z, 5)], argv=['--mock', '--z-speed', '1']), 0)
        self.assertIn('Z=10.000 at 1 mm/s', output.getvalue())
        self.assertIn('Z=5.000 at 1 mm/s', output.getvalue())

    def test_mock_square_and_preview(self):
        printer = MockPrinter()
        prepared = printer.request({'action': 'preview', 'steps': SQUARE, 'speed_mm_s': 20})['plan']
        self.assertEqual(printer.submitted_scripts, [])
        reply = run_prepared(printer, SQUARE, 20, prepared)
        self.assertEqual(reply['reported_position'], [100, 100, 5])
        self.assertEqual(len(printer.submitted_scripts), 1)

    def test_transport_failure_requests_stop_without_motion_retry(self):
        printer = Mock()
        printer.request.side_effect = [PrinterError('SSH lost'), {'ok': True, 'stop_confirmed': True}]
        with self.assertRaises(PrinterError):
            run_prepared(printer, SQUARE, 20, {'start': [100, 100, 5]})
        self.assertEqual([c.args[0]['action'] for c in printer.request.call_args_list], ['run', 'stop'])

    def test_preflight_rejection_does_not_send_stop(self):
        printer = Mock()
        printer.request.return_value = {'ok': False, 'error': 'Position changed'}
        with self.assertRaises(PrinterError):
            run_prepared(printer, SQUARE, 20, {'start': [100, 100, 5]})
        self.assertEqual(printer.request.call_count, 1)

    def test_cli_requires_confirmation_and_mock_never_uses_ssh(self):
        with (patch('simple_runner.SSHPrinter', side_effect=AssertionError('SSH accessed')),
              contextlib.redirect_stdout(io.StringIO())):
            self.assertEqual(run(SQUARE, 20, ['--mock']), 0)

    def test_cli_cancel_sends_no_run(self):
        printer = MockPrinter()
        printer.simulated = False
        with patch('simple_runner.SSHPrinter', return_value=printer), patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='NO'), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run(SQUARE, 20, []), 1)
        self.assertEqual(printer.submitted_scripts, [])

    def test_import_has_no_hardware_side_effect(self):
        with patch('subprocess.run', side_effect=AssertionError('SSH accessed')):
            import simple
        self.assertEqual(len(simple.STEPS), 4)


if __name__ == '__main__':
    unittest.main()
