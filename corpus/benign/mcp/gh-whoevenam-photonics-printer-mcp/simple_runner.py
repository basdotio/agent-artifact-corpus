"""Terminal interface. Full-sequence preview and one operator confirmation."""
import argparse
import json
import sys

from printer_client import MockPrinter, PrinterError, SSHPrinter, checked, run_prepared
from printer_policy import MAX_Z_SPEED, SafetyError, check_xy, mesh_active, number, xyz

x, y, z = 'x', 'y', 'z'


def fw(axis, mm):
    if axis not in (x, y, z):
        raise SafetyError('Axis must be x, y or z')
    mm = number(mm, 'Distance')
    if mm <= 0:
        raise SafetyError('Distance must be positive; use bc() for negative movement')
    return {'axis': axis, 'distance_mm': mm}


def bc(axis, mm):
    result = fw(axis, mm)
    result['distance_mm'] *= -1
    return result


def confirm(token, simulated):
    if simulated:
        return
    if not sys.stdin.isatty():
        raise PrinterError('Use an interactive terminal for hardware; --preview sends no motion')
    if input('Type %s to proceed: ' % token).strip() != token:
        raise PrinterError('Cancelled; no command sent')


def run(steps, speed=20.0, argv=None, z_speed=MAX_Z_SPEED):
    parser = argparse.ArgumentParser(description='Smooth X/Y/Z sequences with an on-printer software watchdog.')
    parser.add_argument('--mock', action='store_true', help='Simulation only; no SSH access.')
    parser.add_argument('--speed', type=float, default=speed, help='X/Y speed in mm/s, maximum 20.')
    parser.add_argument('--z-speed', type=float, default=z_speed, help='Z speed in mm/s, maximum 2.')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--preview', action='store_true')
    action.add_argument('--status', action='store_true')
    action.add_argument('--stop', action='store_true')
    action.add_argument('--mesh-clear', action='store_true')
    action.add_argument('--mesh-load', metavar='PROFILE')
    action.add_argument('--xy-start', action='store_true', help='Confirm a fixed X/Y entry to (0,0) at 5 mm/s.')
    action.add_argument('--xy-start-preview', action='store_true', help='Preview that entry without moving.')
    action.add_argument('--test-move', action='store_true', help='Move X +5 mm and back at the selected X/Y speed.')
    args = parser.parse_args(argv)
    try:
        printer = MockPrinter() if args.mock else SSHPrinter()
        if args.status or args.stop:
            print(json.dumps(checked(printer, {'action': 'stop' if args.stop else 'status'}), indent=2))
            return 0
        if args.mesh_clear or args.mesh_load:
            print('Unload mesh compensation (saved calibration retained).' if args.mesh_clear else
                  'Load saved mesh profile %r.' % args.mesh_load)
            confirm('CLEAR' if args.mesh_clear else 'LOAD', printer.simulated)
            request = {'action': 'mesh-clear'} if args.mesh_clear else {'action': 'mesh-load', 'profile': args.mesh_load}
            print(json.dumps(checked(printer, request), indent=2))
            return 0
        entry = args.xy_start or args.xy_start_preview
        if args.test_move:
            steps = [fw(x, 5), bc(x, 5)]
        if entry and printer.simulated:
            printer.state['toolhead']['homed_axes'] = 'xy'
            for obj, field in (('toolhead', 'position'), ('gcode_move', 'position'),
                               ('gcode_move', 'gcode_position'), ('motion_report', 'live_position')):
                printer.state[obj][field][:3] = [-12.0, -15.0, 0.0]
        state = checked(printer, {'action': 'status'})['state']
        toolhead = state.get('toolhead', {})
        position = xyz(toolhead.get('position'), 'Toolhead position')
        print('Reported position: X=%.3f Y=%.3f Z=%.3f; homed axes: %s.' %
              (*position, toolhead.get('homed_axes') or 'none'))
        if entry:
            try:
                check_xy(position)
            except SafetyError:
                pass
            else:
                print('Already inside X/Y 0..200 mm. No entry move needed; no command sent.\n'
                      'Run ./printerctl test-move for X +5 mm and back, or ./printerctl for simple.py steps.')
                return 0
        if mesh_active(state.get('bed_mesh')):
            print('Bed-mesh compensation is active. Unload it for this fixed-height movement test; saved calibration is retained.')
            if args.preview or args.xy_start_preview:
                print('Preview blocked by active mesh. Run ./printerctl mesh-clear and type CLEAR, then preview again.')
                return 1
            confirm('CLEAR', printer.simulated)
            checked(printer, {'action': 'mesh-clear'})
            print('Mesh unloaded. Restore for printing with ./printerctl mesh-load default.')
        request = ({'action': 'xy-start-preview'} if entry else
                   {'action': 'preview', 'steps': steps, 'speed_mm_s': args.speed,
                    'z_speed_mm_s': args.z_speed})
        prepared = checked(printer, request)['plan']
        print('SIMULATION' if printer.simulated else 'REAL PRINTER — firmware-estimated positions')
        if entry:
            print('ENTRY MOVE: straight line from %s to %s at 5 mm/s; no Z command.' %
                  (prepared['start'], prepared['end']))
            print('This move alone permits negative coordinates: X %g..%g, Y %g..%g mm.' % tuple(prepared['bounds']))
            print('Normal steps retain X/Y bounds 0..200 mm. Coordinates are not reset.')
        else:
            print('Bounds: X/Y 0..200 mm; Z 0..235 mm. Start: %s' % prepared['start'])
        if not prepared['moves_z']:
            print('X/Y-only: X and Y must be firmware-homed; reported Z must stay unchanged.')
        if prepared['start'][2] == 0:
            print('Reported Z is 0. Confirm the nozzle is physically clear of the bed for the entire path.')
        print('Speeds: X/Y %g mm/s; Z %g mm/s.' % (prepared['speed_mm_s'], prepared['z_speed_mm_s']))
        for index, target in enumerate(prepared['targets'], 1):
            print('  %d: X=%.3f Y=%.3f Z=%.3f at %g mm/s' %
                  (index, target[0], target[1], target[2], prepared['step_speeds_mm_s'][index - 1]))
        print('One queued sequence; no SSH pauses between steps.')
        print('Startup safeguard: an exact zero position/velocity report may be ignored for up to 0.5 seconds.')
        if args.preview or args.xy_start_preview:
            print('Preview only; no motion sent.')
            return 0
        print('Confirm the displayed path is physically clear. Keep other printer controls idle.\n'
              'Emergency stop from another terminal: ./printerctl stop')
        confirm('ENTER' if entry else 'MOVE', printer.simulated)
        result = run_prepared(printer, steps, args.speed, prepared)
        if result.get('startup_zero_report_seen'):
            print('A startup zero-position report occurred and recovered within 0.5 seconds.')
        print('Completed%s. Reported position: %s' % (' (simulation)' if printer.simulated else '', result['reported_position']))
        return 0
    except (SafetyError, PrinterError, ValueError, TypeError, EOFError) as exc:
        print('Stopped: ' + str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nCancelled before movement.', file=sys.stderr)
        return 130
