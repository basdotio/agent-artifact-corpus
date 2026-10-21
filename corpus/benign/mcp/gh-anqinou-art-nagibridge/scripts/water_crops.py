"""Water all unwatered crops in a region — snake pattern, water level detection."""

import argparse
import os
import time

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=7842)
args = parser.parse_args()

os.environ["NAGI_URL"] = f"http://localhost:{args.port}"
import stardew_api as api

TOOL_DELAY = 0.45


def find_unwatered(radius=25):
    data = api.surroundings(radius)
    tiles = data.get("tiles", [])
    return [(t["x"], t["y"]) for t in tiles
            if t.get("terrain") == "HoeDirt" and not t.get("watered") and t.get("crop")]


def snake_sort(tiles):
    rows = {}
    for x, y in tiles:
        rows.setdefault(y, []).append(x)
    ordered = []
    for i, y in enumerate(sorted(rows.keys())):
        xs = sorted(rows[y])
        if i % 2 == 1:
            xs.reverse()
        for x in xs:
            ordered.append((x, y))
    return ordered


def face_toward(tx, ty):
    s = api.state()
    px, py = s["player"]["x"], s["player"]["y"]
    dx, dy = tx - px, ty - py
    if dx == 0 and dy == 0:
        return 2
    if abs(dx) > abs(dy):
        return 1 if dx > 0 else 3
    return 2 if dy > 0 else 0


def check_water():
    water, _ = api.watering_can_water()
    if water is not None and water <= 0:
        api.log("  Refilling watering can...")
        api._post("/refill")
        time.sleep(0.2)
        api.select("Watering Can")
        time.sleep(0.15)


def run():
    api.log("=== Water Crops ===")
    unwatered = find_unwatered()
    if not unwatered:
        api.log("Nothing to water!")
        return

    ordered = snake_sort(unwatered)
    api.log(f"Watering {len(ordered)} crops (snake pattern)")

    api._post("/refill")
    api.select("Watering Can")
    time.sleep(0.2)

    for i, (x, y) in enumerate(ordered):
        cur, mx = api.player_stamina()
        if cur < 8:
            api.log(f"Stamina empty at {i}/{len(ordered)}")
            break

        check_water()

        api.move_to(x, y - 1, timeout=8)
        time.sleep(0.1)
        direction = face_toward(x, y)
        api.face(direction)
        time.sleep(0.1)
        api.use_tool("Watering Can")
        time.sleep(TOOL_DELAY)

        if (i + 1) % 20 == 0:
            api.log(f"  {i+1}/{len(ordered)}")

    s = api.state()
    api.log(f"Done! Stamina: {s['player']['stamina']:.0f}/{s['player']['maxStamina']}")
    api.log(f"Time: {s['time']['timeOfDay']}")


if __name__ == "__main__":
    run()
