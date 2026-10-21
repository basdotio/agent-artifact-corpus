"""Chop trees — warp precision, chop trunk + stump in one go."""

import argparse
import os
import time

parser = argparse.ArgumentParser()
parser.add_argument("--count", type=int, default=10, help="Max trees to chop")
parser.add_argument("--port", type=int, default=7842)
args = parser.parse_args()

os.environ["NAGI_URL"] = f"http://localhost:{args.port}"
import stardew_api as api

TRUNK_HITS = 12
STUMP_HITS = 6
HIT_DELAY = 0.65
STAMINA_RESERVE = 10


def find_trees(radius=20):
    data = api.surroundings(radius)
    px, py = data["center"]["x"], data["center"]["y"]
    trees = []
    for t in data.get("tiles", []):
        terrain = t.get("terrain", "")
        if terrain.startswith("Tree:"):
            d = abs(t["x"] - px) + abs(t["y"] - py)
            trees.append((t["x"], t["y"], terrain, d))
    trees.sort(key=lambda t: t[3])
    return trees


def tile_has(tx, ty, check):
    data = api.surroundings(3)
    for t in data.get("tiles", []):
        if t["x"] == tx and t["y"] == ty:
            terrain = t.get("terrain", "")
            obj = t.get("object", "")
            if check == "tree" and terrain.startswith("Tree:"):
                return True
            if check == "stump" and (obj == "Twig" or terrain.startswith("Tree:")):
                return True
    return False


def chop_at(tx, ty, hits):
    """Warp next to target, face it, swing axe."""
    api.warp("Farm", tx, ty - 1)
    time.sleep(0.8)
    api.face(2)
    time.sleep(0.15)
    api.select("Axe")
    time.sleep(0.15)

    for hit in range(hits):
        cur, _ = api.player_stamina()
        if cur < STAMINA_RESERVE:
            api.log(f"  Stamina low ({cur:.0f})")
            return "stamina"
        api.use_tool("Axe")
        time.sleep(HIT_DELAY)

    return "done"


def chop_tree(tx, ty):
    api.log(f"  Chopping trunk...")
    result = chop_at(tx, ty, TRUNK_HITS)
    if result == "stamina":
        return "stamina"

    # walk over to pick up wood drops
    api.warp("Farm", tx, ty)
    time.sleep(0.5)

    # check for stump and chop it too
    if tile_has(tx, ty, "stump") or tile_has(tx, ty, "tree"):
        api.log(f"  Stump remaining, chopping...")
        result = chop_at(tx, ty, STUMP_HITS)
        if result == "stamina":
            return "stamina"
        # pick up stump drops
        api.warp("Farm", tx, ty)
        time.sleep(0.5)

    if tile_has(tx, ty, "tree"):
        return "failed"
    return "chopped"


def run():
    api.log(f"=== Chop Trees (max {args.count}, warp mode) ===")

    s = api.state()
    inv = s.get("inventory", [])
    wood_before = sum(i["stack"] for i in inv if i and i["name"] == "Wood")
    api.log(f"Wood before: {wood_before}")

    chopped = 0
    for attempt in range(args.count):
        trees = find_trees()
        if not trees:
            api.log("No more trees nearby")
            break

        tx, ty, ttype, dist = trees[0]
        api.log(f"Tree #{chopped+1}: ({tx},{ty}) {ttype}")

        result = chop_tree(tx, ty)
        api.log(f"  Result: {result}")

        if result == "chopped":
            chopped += 1
        elif result == "stamina":
            break

    s = api.state()
    inv = s.get("inventory", [])
    wood_after = sum(i["stack"] for i in inv if i and i["name"] == "Wood")
    api.log(f"Chopped {chopped} trees. Wood: {wood_before} -> {wood_after} (+{wood_after - wood_before})")
    api.log(f"Stamina: {s['player']['stamina']:.0f}/{s['player']['maxStamina']}")
    api.log(f"Time: {s['time']['timeOfDay']}")


if __name__ == "__main__":
    run()
