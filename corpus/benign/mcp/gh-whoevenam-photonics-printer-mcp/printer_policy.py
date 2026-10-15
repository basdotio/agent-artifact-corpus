"""Shared, pure movement checks. Python 3.8 compatible for the printer."""
import math

BOUNDS = (0.0, 200.0, 0.0, 200.0)
Z_BOUNDS = (0.0, 235.0)
MAX_SPEED = 20.0
MAX_Z_SPEED = 2.0
POSITION_TOLERANCE = 0.002
# Arithmetic noise seen in the firmware's interpolated idle reports. Applies
# only to telemetry; planned/rounded command targets retain strict bounds.
REPORT_ROUNDOFF = 1e-9


class SafetyError(ValueError):
    pass


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SafetyError(name + ' must be a finite number')
    try:
        value = float(value)
    except (ValueError, OverflowError):
        raise SafetyError(name + ' must be a finite number')
    if not math.isfinite(value):
        raise SafetyError(name + ' must be a finite number')
    return value


def xyz(value, name):
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        raise SafetyError(name + ' is missing or invalid')
    return [number(v, name) for v in value[:3]]


def obj(state, name):
    if not isinstance(state, dict) or not isinstance(state.get(name), dict):
        raise SafetyError(name + ' status is unavailable')
    return state[name]


def same_position(actual, expected):
    return all(abs(a - b) <= POSITION_TOLERANCE
               for a, b in zip(xyz(actual, 'Position'), xyz(expected, 'Expected position')))


def check_xy(position, bounds=BOUNDS, tolerance=0.0):
    position = xyz(position, 'Position')
    for value, low, high, name in ((position[0], bounds[0], bounds[1], 'X'),
                                    (position[1], bounds[2], bounds[3], 'Y')):
        if not low - tolerance <= value <= high + tolerance:
            raise SafetyError('%s=%.6f is outside operator bounds %g..%g mm' % (name, value, low, high))


def check_z(position, tolerance=0.0):
    if not Z_BOUNDS[0] - tolerance <= xyz(position, 'Position')[2] <= Z_BOUNDS[1] + tolerance:
        raise SafetyError('Z is outside operator bounds 0..235 mm')


def mesh_active(mesh):
    if not isinstance(mesh, dict) or not isinstance(mesh.get('profile_name'), str):
        raise SafetyError('Bed-mesh status is unavailable')
    matrix = mesh.get('mesh_matrix')
    if not isinstance(matrix, list) or any(not isinstance(row, list) for row in matrix):
        raise SafetyError('Bed-mesh matrix is invalid')
    if matrix and any(len(row) != len(matrix[0]) for row in matrix):
        raise SafetyError('Bed-mesh matrix is ragged')
    for row in matrix:
        for v in row:
            number(v, 'Bed-mesh point')
    return bool(mesh['profile_name']) or any(len(row) for row in matrix)


def startup_zero_report(state):
    report = obj(state, 'motion_report')
    return (xyz(report.get('live_position'), 'Live position') == [0.0, 0.0, 0.0]
            and number(report.get('live_velocity'), 'Live velocity') == 0.0)


def check_state(state, start_z=None, stationary=False, z_range=None, speed_limit=MAX_SPEED,
                allow_startup_zero=False, required_axes='xyz', bounds=BOUNDS):
    """Checks both interpolated live position and queued toolhead position."""
    if obj(state, 'webhooks').get('state') != 'ready':
        raise SafetyError('Klipper is not ready')
    if obj(state, 'print_stats').get('state') not in ('standby', 'complete', 'cancelled'):
        raise SafetyError('Printer must be idle, not printing or paused')
    th = obj(state, 'toolhead')
    homed = th.get('homed_axes')
    if (not isinstance(homed, str) or len(set(homed)) != len(homed)
            or not set(homed) <= set('xyz') or not set(required_axes) <= set(homed)):
        raise SafetyError('Home %s using the printer controls before running; placing an axis by hand does not home it' %
                          ('X and Y' if required_axes == 'xy' else 'all axes'))
    if 'z' not in homed and mesh_active(state.get('bed_mesh')):
        raise SafetyError('X/Y-only movement with Z unhomed requires an inactive bed mesh')
    for name in ('heater_bed', 'extruder'):
        if name == 'heater_bed' or name in state:
            if number(obj(state, name).get('target'), name + ' target') != 0:
                raise SafetyError('Heater targets must be zero')
    move = obj(state, 'gcode_move')
    if any(xyz(move.get('homing_origin'), 'Homing origin')):
        raise SafetyError('Nonzero coordinate offsets are unsupported')
    if number(move.get('speed_factor'), 'Speed override') != 1.0:
        raise SafetyError('Speed override must be 100%')
    machine = xyz(move.get('position'), 'G-code machine position')
    gcode = xyz(move.get('gcode_position'), 'G-code position')
    if any(abs(a - b) > 1e-6 for a, b in zip(machine, gcode)):
        raise SafetyError('G92 coordinate offsets are unsupported')
    queued = xyz(th.get('position'), 'Toolhead position')
    live_obj = obj(state, 'motion_report')
    live = xyz(live_obj.get('live_position'), 'Live position')
    velocity = number(live_obj.get('live_velocity'), 'Live velocity')
    if -REPORT_ROUNDOFF <= velocity < 0:
        velocity = 0.0
    if velocity < 0 or velocity > speed_limit + 0.01:
        raise SafetyError('Live velocity exceeds the allowed %g mm/s' % speed_limit)
    mins, maxs = xyz(th.get('axis_minimum'), 'Firmware minimum'), xyz(th.get('axis_maximum'), 'Firmware maximum')
    for label, point in (('queued', queued), ('live', live)):
        check_xy(point, bounds, REPORT_ROUNDOFF)
        check_z(point, REPORT_ROUNDOFF)
        for i in range(3):
            if not mins[i] < maxs[i] or not mins[i] - REPORT_ROUNDOFF <= point[i] <= maxs[i] + REPORT_ROUNDOFF:
                raise SafetyError('Reported position is outside firmware travel limits')
        missing_live = (label == 'live' and allow_startup_zero and not stationary
                        and point == [0.0, 0.0, 0.0] and velocity == 0.0)
        if not missing_live and start_z is not None and abs(point[2] - start_z) > POSITION_TOLERANCE:
            raise SafetyError('Unexpected Z change: %s Z=%.6f mm; expected Z=%.6f mm; '
                              'queued XYZ=%r; live XYZ=%r; live velocity=%r mm/s' %
                              (label, point[2], start_z, queued, live, velocity))
        if not missing_live and z_range is not None and not z_range[0] - POSITION_TOLERANCE <= point[2] <= z_range[1] + POSITION_TOLERANCE:
            raise SafetyError('Reported Z is outside the planned Z range')
    if stationary:
        if velocity > 0.001 or not same_position(live, queued):
            raise SafetyError('Printer is moving, has queued motion, or live status has not settled')
        if any(abs(a - b) > 1e-6 for a, b in zip(queued, machine)):
            raise SafetyError('Toolhead and G-code positions disagree; check bed mesh with --status')
    return queued, live


def check_execution_state(state, prepared, stationary=False, allow_startup_zero=False):
    if prepared.get('xy_start') and mesh_active(state.get('bed_mesh')):
        raise SafetyError('XY entry requires an inactive bed mesh')
    return check_state(state, start_z=prepared['start'][2] if not prepared['moves_z'] else None,
                       stationary=stationary, z_range=prepared['z_range'],
                       speed_limit=max(prepared['step_speeds_mm_s']), allow_startup_zero=allow_startup_zero,
                       required_axes='xyz' if prepared['moves_z'] else 'xy', bounds=prepared['bounds'])


def plan(state, steps, speed, z_speed=MAX_Z_SPEED):
    speed = number(speed, 'Speed')
    if not 0 < speed <= MAX_SPEED:
        raise SafetyError('Speed must be >0 and <=20 mm/s')
    feed = float('%.6f' % (speed * 60))
    if feed <= 0 or feed > 1200:
        raise SafetyError('Rounded feed rate is invalid')
    speed = feed / 60
    z_speed = number(z_speed, 'Z speed')
    if not 0 < z_speed <= MAX_Z_SPEED:
        raise SafetyError('Z speed must be >0 and <=2 mm/s')
    z_feed = float('%.6f' % (z_speed * 60))
    if z_feed <= 0 or z_feed > MAX_Z_SPEED * 60:
        raise SafetyError('Rounded Z feed rate is invalid')
    z_speed = z_feed / 60
    if not isinstance(steps, list) or not 1 <= len(steps) <= 1000:
        raise SafetyError('Provide 1..1000 movement steps')
    for step in steps:
        if not isinstance(step, dict) or set(step) != {'axis', 'distance_mm'} or step['axis'] not in ('x', 'y', 'z'):
            raise SafetyError('Each step needs axis x/y/z and distance_mm')
    moves_z = any(step['axis'] == 'z' for step in steps)
    start, _ = check_state(state, stationary=True, required_axes='xyz' if moves_z else 'xy')
    current = list(start)
    minimum = xyz(state['toolhead']['axis_minimum'], 'Firmware minimum')
    maximum = xyz(state['toolhead']['axis_maximum'], 'Firmware maximum')
    targets, lines, nominal, step_speeds = [], ['G90'], 0.0, []
    for step in steps:
        if not isinstance(step, dict) or set(step) != {'axis', 'distance_mm'} or step['axis'] not in ('x', 'y', 'z'):
            raise SafetyError('Each step needs axis x/y/z and distance_mm')
        delta = number(step['distance_mm'], 'Distance')
        if delta == 0:
            raise SafetyError('Step distance must be nonzero')
        i = ('x', 'y', 'z').index(step['axis'])
        target = list(current)
        target[i] += delta
        rounded = list(target)
        indices = (2,) if i == 2 else (0, 1)
        for j in indices:
            rounded[j] = float('%.3f' % target[j])
        for point in (target, rounded):
            check_xy(point)
            check_z(point)
            if any(not minimum[j] <= point[j] <= maximum[j] for j in range(3)):
                raise SafetyError('Target exceeds firmware travel limits')
        target = rounded
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, current)))
        if distance == 0:
            raise SafetyError('Step rounds to zero at 0.001 mm resolution')
        step_speed = z_speed if i == 2 else speed
        nominal += distance / step_speed
        step_speeds.append(step_speed)
        targets.append(target)
        if i == 2:
            lines.append('G1 Z%.3f F%.6f' % (target[2], z_feed))
        else:
            lines.append('G1 X%.3f Y%.3f F%.6f' % (target[0], target[1], feed))
        current = target
    timeout = 20 + nominal * 2 + len(steps) * 0.1
    if timeout > 300:
        raise SafetyError('Sequence is too long/slow for the 300-second watchdog deadline')
    lines.append('M400')
    heights = [start[2]] + [target[2] for target in targets]
    return {'start': start, 'targets': targets, 'end': current, 'bounds': list(BOUNDS),
            'z_bounds': list(Z_BOUNDS), 'z_range': [min(heights), max(heights)],
            'moves_z': moves_z,
            'z_speed_mm_s': z_speed, 'step_speeds_mm_s': step_speeds,
            'speed_mm_s': speed, 'nominal_seconds': nominal, 'timeout': timeout,
            'script': '\n'.join(lines)}


def plan_xy_start(state):
    """Separate operator-confirmed entry from the observed XY homing area.

    No caller-supplied bounds, speed, destination, homing or coordinate reset.
    The ordinary planner continues to reject negative XY coordinates.
    """
    start, _ = check_state(state, stationary=True, required_axes='xy',
                           bounds=(-12.0, 0.0, -15.0, 0.0), speed_limit=5.0)
    if mesh_active(state.get('bed_mesh')):
        raise SafetyError('XY entry requires an inactive bed mesh')
    if start[:2] == [0.0, 0.0]:
        raise SafetyError('Already at X=0 Y=0; use ./printerctl --preview for your steps')
    end = [0.0, 0.0, start[2]]
    minimum = xyz(state['toolhead']['axis_minimum'], 'Firmware minimum')
    maximum = xyz(state['toolhead']['axis_maximum'], 'Firmware maximum')
    if any(not minimum[i] <= end[i] <= maximum[i] for i in range(3)):
        raise SafetyError('Entry target exceeds firmware travel limits')
    nominal = math.hypot(start[0], start[1]) / 5.0
    return {'start': start, 'targets': [end], 'end': end,
            'bounds': [start[0], 0.0, start[1], 0.0],
            'z_bounds': list(Z_BOUNDS), 'z_range': [start[2], start[2]],
            'moves_z': False, 'xy_start': True, 'z_speed_mm_s': MAX_Z_SPEED,
            'step_speeds_mm_s': [5.0], 'speed_mm_s': 5.0,
            'nominal_seconds': nominal, 'timeout': 20.0 + nominal * 2,
            'script': 'G90\nG1 X0.000 Y0.000 F300.000000\nM400'}
