"""XY homing policy and explicit home-area entry; no hardware access."""
import contextlib
import copy
import io
import unittest
from unittest.mock import Mock, patch

from printer_client import MockPrinter, PrinterError, mock_state, run_prepared
from printer_policy import SafetyError, check_execution_state, plan, plan_xy_start
from printer_watchdog import execute, validate_request
from simple_runner import fw, run, x, z
from test_simple import FakeAPI


def set_position(state, point):
    for obj, field in (('toolhead', 'position'), ('gcode_move', 'position'),
                       ('gcode_move', 'gcode_position'), ('motion_report', 'live_position')):
        state[obj][field][:3] = point


def home_state():
    state = mock_state()
    state['toolhead']['homed_axes'] = 'xy'
    set_position(state, [-12., -15., 0.])
    return state


class XYTests(unittest.TestCase):
    def test_observed_idle_roundoff_does_not_block_entry(self):
        state = home_state()
        state['motion_report']['live_velocity'] = -7.105427357601002e-15
        state['motion_report']['live_position'][1] = -15.000000000000002
        prepared = plan_xy_start(state)
        self.assertEqual(prepared['end'], [0, 0, 0])
        state['motion_report']['live_velocity'] = -0.000001
        with self.assertRaises(SafetyError):
            plan_xy_start(state)
        state['motion_report']['live_velocity'] = 0
        state['motion_report']['live_position'][1] = -15.000001
        with self.assertRaises(SafetyError):
            plan_xy_start(state)
        state = mock_state()
        set_position(state, [200, 100, 5])
        with self.assertRaises(SafetyError):
            plan(state, [fw(x, 5e-10)], 20)

    def test_xy_plan_with_z_unhomed_and_z_plan_rejected(self):
        state = home_state()
        set_position(state, [0., 0., 0.])
        prepared = plan(state, [fw(x, 50)], 20)
        self.assertEqual(prepared['end'], [50, 0, 0])
        self.assertNotIn(' Z', prepared['script'])
        with self.assertRaisesRegex(SafetyError, 'Home all axes'):
            plan(state, [fw(x, 5), fw(z, 5)], 20)
        for axes in ('', 'x', 'y', 'z', 'xz', 'yz', 'xyy', 'xyjunk', None):
            state['toolhead']['homed_axes'] = axes
            with self.subTest(axes=axes), self.assertRaises(SafetyError):
                plan(state, [fw(x, 5)], 20)

    def test_unhomed_z_requires_mesh_inactive_and_reports_fixed_z(self):
        state = home_state()
        set_position(state, [0, 0, 0])
        prepared = plan(state, [fw(x, 5)], 20)
        for mesh in (None, {'profile_name': 'default', 'mesh_matrix': [[0.0]]},
                     {'profile_name': '', 'mesh_matrix': [[0.0]]}):
            state['bed_mesh'] = mesh
            with self.subTest(mesh=mesh), self.assertRaises(SafetyError):
                check_execution_state(state, prepared)
        state['bed_mesh'] = {'profile_name': '', 'mesh_matrix': [[]]}
        state['motion_report']['live_position'][2] = 0.01
        with self.assertRaisesRegex(SafetyError, 'Unexpected Z'):
            check_execution_state(state, prepared)

    def test_entry_is_fixed_and_normal_bounds_stay_strict(self):
        state = home_state()
        prepared = plan_xy_start(state)
        self.assertEqual(prepared['script'], 'G90\nG1 X0.000 Y0.000 F300.000000\nM400')
        self.assertEqual(prepared['bounds'], [-12, 0, -15, 0])
        self.assertEqual(prepared['end'], [0, 0, 0])
        with self.assertRaisesRegex(SafetyError, 'outside operator bounds'):
            plan(state, [fw(x, 50)], 20)
        for point in ([-12.001, -15, 0], [-12, -15.001, 0], [1, -15, 0],
                      [-12, 1, 0], [0, 0, 0], [-12, -15, -0.001]):
            state = home_state()
            set_position(state, point)
            with self.subTest(point=point), self.assertRaises(SafetyError):
                plan_xy_start(state)
        state = home_state()
        state['toolhead']['axis_maximum'][0] = -1
        with self.assertRaisesRegex(SafetyError, 'target exceeds firmware'):
            plan_xy_start(state)

    def test_entry_watchdog_uses_actual_start_corridor_and_mesh_guard(self):
        state = home_state()
        set_position(state, [-5, -6, 0])
        prepared = plan_xy_start(state)
        self.assertEqual(prepared['bounds'], [-5, 0, -6, 0])
        for point in ([-5.01, -6, 0], [0.01, -6, 0], [-5, -6.01, 0], [-5, 0.01, 0], [-5, -6, 0.01]):
            fault = copy.deepcopy(state)
            fault['motion_report']['live_position'][:3] = point
            with self.subTest(point=point), self.assertRaises(SafetyError):
                check_execution_state(fault, prepared)
        state['toolhead']['homed_axes'] = 'xyz'
        state['bed_mesh'] = {'profile_name': 'default', 'mesh_matrix': [[0.0]]}
        with self.assertRaisesRegex(SafetyError, 'inactive bed mesh'):
            check_execution_state(state, prepared)

    def test_entry_api_does_not_accept_custom_bounds_speed_or_script(self):
        for action in ('xy-start', 'xy-start-preview'):
            request = {'action': action}
            if action == 'xy-start':
                request['expected_start'] = [-12, -15, 0]
            self.assertEqual(validate_request(request), action)
            for key, value in (('bounds', [-20, 200, -20, 200]), ('speed_mm_s', 20),
                               ('script', 'G28'), ('steps', [fw(z, 5)])):
                with self.subTest(action=action, key=key), self.assertRaises(SafetyError):
                    validate_request(dict(request, **{key: value}))

    def test_entry_preflight_change_rejects_without_dispatch_or_stop(self):
        api, stop = FakeAPI(), Mock()
        api.state = home_state()
        with self.assertRaisesRegex(SafetyError, 'Position changed'):
            execute(api, {}, {'action': 'xy-start', 'expected_start': [-11, -15, 0]}, stop, 0)
        self.assertEqual(api.calls, [])
        stop.assert_not_called()

    def test_entry_live_violation_requests_stop(self):
        def mutate(state):
            state['motion_report']['live_position'][:3] = [-12.1, -15, 0]
        api, stop = FakeAPI(mutate), Mock(return_value=True)
        api.state = home_state()
        result = execute(api, {}, {'action': 'xy-start', 'expected_start': [-12, -15, 0]}, stop, 0)
        self.assertTrue(result['stop_confirmed'], result)
        stop.assert_called_once()

    def test_entry_then_xy_steps_simulated(self):
        printer = MockPrinter()
        printer.state = home_state()
        prepared = printer.request({'action': 'xy-start-preview'})['plan']
        self.assertEqual(printer.submitted_scripts, [])
        result = run_prepared(printer, [], 20, prepared)
        self.assertEqual(result['reported_position'], [0, 0, 0])
        prepared = plan(printer.state, [fw(x, 50)], 20)
        self.assertEqual(run_prepared(printer, [fw(x, 50)], 20, prepared)['reported_position'], [50, 0, 0])
        self.assertEqual(len(printer.submitted_scripts), 2)

    def test_entry_transport_failure_stops_without_retry(self):
        printer = Mock()
        printer.request.side_effect = [PrinterError('lost'), {'ok': True, 'stop_confirmed': True}]
        with self.assertRaises(PrinterError):
            run_prepared(printer, [], 20, plan_xy_start(home_state()))
        self.assertEqual([c.args[0]['action'] for c in printer.request.call_args_list], ['xy-start', 'stop'])

    def test_entry_preview_and_cancel_never_move(self):
        for arguments, answer, expected_code in ((['--xy-start-preview'], '', 0), (['--xy-start'], 'MOVE', 1)):
            printer = MockPrinter()
            printer.state, printer.simulated = home_state(), False
            output = io.StringIO()
            with patch('simple_runner.SSHPrinter', return_value=printer), patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value=answer), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                self.assertEqual(run([fw(x, 50)], argv=arguments), expected_code)
            self.assertEqual(printer.submitted_scripts, [])
            self.assertIn('negative coordinates', output.getvalue())
            self.assertIn('nozzle is physically clear', output.getvalue())


if __name__ == '__main__':
    unittest.main()
