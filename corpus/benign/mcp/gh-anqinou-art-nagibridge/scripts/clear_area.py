"""
开垦skill：扫描区域 → 粗清(move_to) → 重扫 → 精补(warp)

用法:
    python clear_area.py <x1> <y1> <x2> <y2> [options]

参数:
    x1,y1  左上角坐标
    x2,y2  右下角坐标

选项:
    --port PORT   NagiBridge端口（默认 7842）
    --hits N      硬目标额外敲击次数（默认 2）

示例:
    python clear_area.py 50 20 70 30 --port 7842
"""

import argparse
import os
import time
from collections import defaultdict

parser = argparse.ArgumentParser()
parser.add_argument("x1", type=int)
parser.add_argument("y1", type=int)
parser.add_argument("x2", type=int)
parser.add_argument("y2", type=int)
parser.add_argument("--port", type=int, default=7842)
parser.add_argument("--hits", type=int, default=2)
args = parser.parse_args()

os.environ["NAGI_URL"] = f"http://localhost:{args.port}"
import stardew_api as api

TOOL_DELAY = 0.55
STAMINA_MIN = 12

TOOL_MAP = {
    "Weeds": ("Scythe", 1),
    "Grass": ("Scythe", 1),
    "Stone": ("Pickaxe", 2),
    "Twig": ("Axe", 1),
    "Tree": ("Axe", 18),
    "LargeStump": ("Axe", 15),
    "LargeLog": ("Axe", 15),
    "LargeBoulder": ("Pickaxe", 10),
    "MeteoriteOre": ("Pickaxe", 10),
}

TOOL_ORDER = ["Scythe", "Pickaxe", "Axe"]


def tile_target_name(tile):
    obj = tile.get("object", "")
    terrain = tile.get("terrain", "")
    resource = tile.get("resource", "")

    if obj in TOOL_MAP:
        return obj
    if resource in TOOL_MAP:
        return resource
    if terrain and terrain.startswith("Tree:"):
        return "Tree"
    if terrain == "Grass":
        return "Grass"
    return None


def inventory_counts():
    counts = defaultdict(int)
    for item in api.state().get("inventory", []):
        name = item.get("name")
        if name:
            counts[name] += int(item.get("stack", 1))
    return counts


def log_inventory_delta(before, after):
    gains = {}
    for name in sorted(set(before) | set(after)):
        delta = after.get(name, 0) - before.get(name, 0)
        if delta:
            gains[name] = delta
    api.log(f"Inventory delta: {gains if gains else '{}'}")


def stamina_ok():
    cur, mx = api.player_stamina()
    if cur < STAMINA_MIN:
        api.log(f"Stamina low: {cur:.1f}/{mx:.0f}, stopping")
        return False
    return True


def scan_area():
    cx = (args.x1 + args.x2) // 2
    cy = (args.y1 + args.y2) // 2
    radius = max(args.x2 - args.x1, args.y2 - args.y1) // 2 + 5

    if api.current_location() == "Farm":
        api._post("/position", {"x": cx, "y": cy})
    else:
        api.warp("Farm", cx, cy)
    time.sleep(0.6)
    data = api.surroundings(min(radius, 30))

    targets = []
    for t in data.get("tiles", []):
        x, y = t["x"], t["y"]
        if x < args.x1 or x > args.x2 or y < args.y1 or y > args.y2:
            continue

        name = tile_target_name(t)
        if not name:
            continue

        tool, hits = TOOL_MAP[name]
        targets.append((x, y, tool, name, hits))

    return targets


def snake_sort(items):
    rows = defaultdict(list)
    for item in items:
        rows[item[1]].append(item)
    ordered = []
    for i, y in enumerate(sorted(rows.keys())):
        row = sorted(rows[y], key=lambda t: t[0])
        if i % 2 == 1:
            row.reverse()
        ordered.extend(row)
    return ordered


def target_still_present(x, y, expected_name):
    data = api.surroundings(2)
    for t in data.get("tiles", []):
        if t.get("x") == x and t.get("y") == y:
            return tile_target_name(t) == expected_name
    return False


def stand_for_target(x, y, use_position):
    stand_x, stand_y = x, y - 1
    if use_position:
        if api.current_location() == "Farm":
            api._post("/position", {"x": stand_x, "y": stand_y})
        else:
            api.warp("Farm", stand_x, stand_y)
        time.sleep(0.3)
        api.face(2)
    else:
        api.move_to(stand_x, stand_y, timeout=8)
        d = api.face_toward(x, y)
        api.face(d)
    time.sleep(0.1)


def clear_pass(targets, use_warp=False):
    by_tool = defaultdict(list)
    for x, y, tool, name, hits in targets:
        by_tool[tool].append((x, y, name, hits))

    cleared = 0
    for tool in TOOL_ORDER:
        items = by_tool.get(tool, [])
        if not items:
            continue

        items = snake_sort(items)
        mode = "position" if use_warp else "move"
        api.log(f"--- {tool}: {len(items)} targets ({mode}) ---")
        api.select(tool)
        time.sleep(0.15)

        for x, y, name, hits in items:
            if not stamina_ok():
                return cleared

            stand_for_target(x, y, use_warp)

            actual_hits = 0
            for h in range(hits):
                if not stamina_ok():
                    return cleared
                if h > 0 and not target_still_present(x, y, name):
                    break
                api.use_tool(tool)
                time.sleep(TOOL_DELAY)
                actual_hits += 1
                if not target_still_present(x, y, name):
                    break
            if actual_hits < hits:
                api.log(f"  {name} at ({x},{y}) cleared after {actual_hits}/{hits} hits")

            cleared += 1
            if cleared % 20 == 0:
                api.log(f"  {cleared} cleared...")

    return cleared


def pickup_sweep():
    api.log("Pickup sweep...")
    for y in range(args.y1, args.y2 + 1):
        xs = range(args.x1, args.x2 + 1)
        if (y - args.y1) % 2 == 1:
            xs = reversed(list(xs))
        for x in xs:
            api.move_to(x, y, timeout=5)
            time.sleep(0.12)


def run():
    api.log(f"=== clear area: ({args.x1},{args.y1})-({args.x2},{args.y2}) ===")
    inv_before = inventory_counts()

    # Pass 1: scan + fast clear with move_to
    targets = scan_area()
    by_type = defaultdict(int)
    for _, _, _, name, _ in targets:
        by_type[name] += 1
    api.log(f"Pass 1: {dict(by_type)}, total={len(targets)}")

    if targets:
        n = clear_pass(targets, use_warp=False)
        api.log(f"Pass 1 done: cleared {n}")

    # Pass 2: rescan + precision clear with warp
    remaining = scan_area() if stamina_ok() else []
    if remaining:
        by_type = defaultdict(int)
        for _, _, _, name, _ in remaining:
            by_type[name] += 1
        api.log(f"Pass 2 (warp): {dict(by_type)}, total={len(remaining)}")
        n = clear_pass(remaining, use_warp=True)
        api.log(f"Pass 2 done: cleared {n}")

        # final check
        leftover = scan_area()
        if leftover:
            api.log(f"Still {len(leftover)} left (may need tool upgrade)")
        else:
            api.log("All clear!")
    else:
        api.log("All clear after pass 1!")

    pickup_sweep()
    log_inventory_delta(inv_before, inventory_counts())


if __name__ == "__main__":
    try:
        st = api.status()
        if not st.get("worldReady"):
            print("game not ready")
            exit(1)
    except Exception as e:
        print(f"cannot connect: {e}")
        exit(1)
    run()
