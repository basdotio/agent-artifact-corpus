"""Terminal preparation keeps confirmation and read-only previews distinct."""
import contextlib
import copy
import io
import unittest
from unittest.mock import patch

from printer_client import MockPrinter
from simple_runner import fw, run, x


class FlowTests(unittest.TestCase):
    def printer(self, mesh=False):
        printer = MockPrinter()
        printer.simulated = False
        if mesh:
            printer.state['bed_mesh'] = {'profile_name': 'default', 'mesh_matrix': [[0.0]]}
        return printer

    def invoke(self, printer, args, answers=()):
        output, actions = io.StringIO(), []
        original = printer.request
        def tracked(request):
            actions.append(copy.deepcopy(request))
            return original(request)
        with patch('simple_runner.SSHPrinter', return_value=printer), patch.object(printer, 'request', side_effect=tracked), patch('sys.stdin.isatty', return_value=True), patch('builtins.input', side_effect=answers), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = run([fw(x, 50)], argv=args)
        return code, output.getvalue(), actions

    def test_entry_inside_area_exits_without_moving_or_clearing_mesh(self):
        for point in (0, 120, 200):
            for args in (['--xy-start'], ['--xy-start-preview']):
                printer = self.printer(mesh=True)
                for obj, field in (('toolhead', 'position'), ('motion_report', 'live_position'), ('gcode_move', 'position'), ('gcode_move', 'gcode_position')):
                    printer.state[obj][field][:2] = [point, point]
                code, output, actions = self.invoke(printer, args)
                self.assertEqual(code, 0, output)
                self.assertIn('No entry move needed', output)
                self.assertEqual([r['action'] for r in actions], ['status'])
                self.assertEqual(printer.submitted_scripts, [])

    def test_preview_with_mesh_does_not_prompt_or_mutate(self):
        printer = self.printer(mesh=True)
        code, output, actions = self.invoke(printer, ['--preview'])
        self.assertEqual(code, 1)
        self.assertIn('mesh-clear', output)
        self.assertEqual([r['action'] for r in actions], ['status'])

    def test_declining_mesh_clear_changes_nothing(self):
        printer = self.printer(mesh=True)
        code, output, actions = self.invoke(printer, [], ['NO'])
        self.assertEqual(code, 1)
        self.assertEqual([r['action'] for r in actions], ['status'])
        self.assertEqual(printer.state['bed_mesh']['profile_name'], 'default')

    def test_mesh_clear_then_separate_movement_confirmation(self):
        printer = self.printer(mesh=True)
        code, output, actions = self.invoke(printer, ['--test-move'], ['CLEAR', 'MOVE'])
        self.assertEqual(code, 0, output)
        self.assertEqual([r['action'] for r in actions], ['status', 'mesh-clear', 'preview', 'run'])
        self.assertEqual(actions[-1]['steps'], [{'axis': 'x', 'distance_mm': 5.0}, {'axis': 'x', 'distance_mm': -5.0}])
        self.assertEqual(printer.submitted_scripts, ['G90\nG1 X105.000 Y100.000 F1200.000000\nG1 X100.000 Y100.000 F1200.000000\nM400'])

    def test_clear_does_not_implicitly_approve_motion(self):
        printer = self.printer(mesh=True)
        code, output, actions = self.invoke(printer, [], ['CLEAR', 'NO'])
        self.assertEqual(code, 1)
        self.assertEqual([r['action'] for r in actions], ['status', 'mesh-clear', 'preview'])
        self.assertEqual(printer.submitted_scripts, [])

    def test_test_move_checks_far_boundary_before_dispatch(self):
        printer = self.printer()
        for obj, field in (('toolhead', 'position'), ('motion_report', 'live_position'), ('gcode_move', 'position'), ('gcode_move', 'gcode_position')):
            printer.state[obj][field][0] = 198
        code, output, actions = self.invoke(printer, ['--test-move'])
        self.assertEqual(code, 1)
        self.assertIn('X=203.000000', output)
        self.assertEqual([r['action'] for r in actions], ['status', 'preview'])
        self.assertEqual(printer.submitted_scripts, [])


if __name__ == '__main__':
    unittest.main()
