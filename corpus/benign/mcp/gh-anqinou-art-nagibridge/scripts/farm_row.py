"""
种田skill：翻地 → 播种 → 浇水（蛇形走位，带体力/水量检测）

用法:
    python farm_row.py <start_x> <start_y> <length> [options]

选项:
    --seed NAME        种子名（默认 Parsnip Seeds）
    --dir DIR          种植方向: right/left/down/up（默认 right）
    --rows N           种几排（默认 1）
    --row-spacing N    排间距（默认 1）
    --skip-water       跳过浇水
    --port PORT        NagiBridge端口（默认 7843）
"""

import sys
import time
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("start_x", type=int)
parser.add_argument("start_y", type=int)
parser.add_argument("length", type=int)
parser.add_argument("--seed", default="Parsnip Seeds")
parser.add_argument("--dir", default="right", choices=["right", "left", "down", "up"])
parser.add_argument("--rows", type=int, default=1)
parser.add_argument("--row-spacing", type=int, default=1)
parser.add_argument("--skip-water", action="store_true")
parser.add_argument("--port", type=int, default=7843)
args = parser.parse_args()

os.environ["NAGI_URL"] = f"http://localhost:{args.port}"
import stardew_api as api

TOOL_DELAY = 0.55
STAMINA_THRESHOLD = 0.15

DIR_MAP = {
    "right": (1, 0),
    "left":  (-1, 0),
    "down":  (0, 1),
    "up":    (0, -1),
}

ROW_OFFSET = {
    "right": (0, 1),
    "left":  (0, 1),
    "down":  (1, 0),
    "up":    (1, 0),
}


def calc_tiles(sx, sy, length, direction, rows, row_spacing):
    dx, dy = DIR_MAP[direction]
    rdx, rdy = ROW_OFFSET[direction]
    tiles = []
    for r in range(rows):
        row = []
        for i in range(length):
            tx = sx + dx * i + rdx * r * row_spacing
            ty = sy + dy * i + rdy * r * row_spacing
            row.append((tx, ty))
        if r % 2 == 1:
            row.reverse()
        tiles.append(row)
    return tiles


def check_stamina():
    cur, mx = api.player_stamina()
    if cur / mx < STAMINA_THRESHOLD:
        api.log(f"stamina low: {cur}/{mx} ({cur/mx:.0%}), stopping")
        return False
    return True


def refill_water():
    api.log("watering can empty, refilling...")
    result = api.refill_water()
    if result.get("ok"):
        api.log(f"refilled: {result.get('water')}/{result.get('max')}")
        api.select("Watering Can")
        time.sleep(0.15)
        return True
    api.log("could not refill")
    return False


def flatten_tiles(tiles):
    """Flatten multi-row tiles into a single snake-ordered list."""
    flat = []
    for row in tiles:
        flat.extend(row)
    return flat


def do_action(tx, ty, tool_or_item, is_watering):
    """Move to tile and use tool/item."""
    if not check_stamina():
        api.log(f"stopped at ({tx},{ty}) due to low stamina")
        return False

    if is_watering:
        water, _ = api.watering_can_water()
        if water is not None and water <= 0:
            if not refill_water():
                return False
            api.select("Watering Can")
            time.sleep(0.15)

    stand_x, stand_y = tx, ty - 1
    api._post("/position", {"x": stand_x, "y": stand_y})
    time.sleep(0.1)
    s = api.state()
    px, py = s["player"]["x"], s["player"]["y"]
    if px != stand_x or py != stand_y:
        api.log(f"could not stand at ({stand_x},{stand_y}) for target ({tx},{ty}); actual=({px},{py})")
        return False
    api.face(2)
    time.sleep(0.1)
    api.use_item()
    time.sleep(TOOL_DELAY)
    return True


def run():
    # --- Pre-checks ---
    api.log("=== pre-check ===")
    errors = api.precheck_farm(args.seed)
    if errors:
        for e in errors:
            api.log(f"FAIL: {e}")
        api.log("=== pre-check failed, aborting ===")
        return

    api.clear_menu()
    api.drain_alerts()

    tiles = calc_tiles(args.start_x, args.start_y, args.length,
                       args.dir, args.rows, args.row_spacing)
    flat = flatten_tiles(tiles)
    total = len(flat)

    blocked = api.precheck_area(flat)
    if blocked:
        api.log(f"BLOCKED: {len(blocked)} obstacles in planting area:")
        for pos, name in blocked:
            api.log(f"  ({pos[0]},{pos[1]}): {name}")
        api.log("=== aborting — clear obstacles first or choose another area ===")
        sys.exit(2)

    api.log(f"=== farm skill: {len(flat)}/{total} tiles, dir={args.dir}, rows={args.rows}, seed={args.seed} ===")

    phases = [("Hoe", "till", False)]
    phases.append((args.seed, "plant", False))
    if not args.skip_water:
        phases.append(("Watering Can", "water", True))

    for phase_idx, (tool, phase_name, is_watering) in enumerate(phases):
        api.log(f"--- {phase_name}: {tool} ---")
        api.select(tool)
        time.sleep(0.15)

        order = flat if phase_idx % 2 == 0 else list(reversed(flat))

        for tx, ty in order:
            if not do_action(tx, ty, tool, is_watering):
                api.log(f"=== stopped during {phase_name} ===")
                return

    # --- Post-check ---
    api.postcheck_menu()
    api.log(f"=== done ===")


if __name__ == "__main__":
    try:
        st = api.status()
        if not st.get("worldReady"):
            print("game not ready")
            sys.exit(1)
    except Exception as e:
        print(f"cannot connect: {e}")
        sys.exit(1)
    run()
