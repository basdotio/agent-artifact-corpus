"""
挖矿脚本：warp传送进矿洞 → 逐层扫描敲石头 → 传送下一层 → 低血量自动撤退

用法:
    PYTHONIOENCODING=utf-8 python3 mine_run.py [--start-level 1] [--max-levels 5] [--hp-threshold 30] [--port 7842]

参数:
    --start-level   从第几层开始（默认 1）
    --max-levels    最多挖几层（默认 5）
    --hp-threshold  血量百分比低于此值时撤退（默认 30）
    --port          NagiBridge端口（默认 7842）
"""

import sys
import os
import time
import argparse
import requests

TOOL_DELAY = 0.8
SCAN_RADIUS = 12

MINEABLE_OBJECTS = {"Stone", "Copper Node", "Iron Node", "Gold Node", "Iridium Node",
                    "Mystic Stone", "Gem Node", "Diamond Node", "Amethyst Node",
                    "Topaz Node", "Emerald Node", "Aquamarine Node", "Jade Node",
                    "Ruby Node", "Geode Node", "Frozen Geode Node",
                    "Magma Geode Node", "Omni Geode Node"}


def log(msg):
    try:
        print(f"[mine] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[mine] {msg.encode('utf-8', errors='replace').decode('utf-8')}", flush=True)


class MineBot:
    def __init__(self, port):
        self.base = f"http://localhost:{port}"

    def _get(self, ep, params=None):
        return requests.get(f"{self.base}{ep}", params=params, timeout=10).json()

    def _post(self, ep, data=None):
        return requests.post(f"{self.base}{ep}", json=data or {}, timeout=10).json()

    def status(self):
        return self._get("/status")

    def state(self):
        return self._get("/state")

    def warp(self, location, x=-1, y=-1):
        d = {"location": location}
        if x >= 0: d["x"] = x
        if y >= 0: d["y"] = y
        return self._post("/warp", d)

    def move_to(self, x, y):
        self._post("/move", {"x": x, "y": y})
        deadline = time.time() + 10
        while time.time() < deadline:
            s = self.state()
            if not s.get("player", {}).get("isMoving", False):
                return True
            time.sleep(0.25)
        self._post("/stop")
        return False

    def face(self, direction):
        self._post("/face", {"direction": direction})

    def use_tool(self, name):
        self._post("/tool", {"name": name})

    def select(self, name):
        return self._post("/select", {"name": name})

    def surroundings(self, radius=12):
        return self._get("/surroundings", {"radius": radius})

    def player_hp(self):
        s = self.state()
        p = s["player"]
        return p["health"], p["maxHealth"]

    def player_stamina(self):
        s = self.state()
        p = s["player"]
        return p["stamina"], p["maxStamina"]

    def location(self):
        return self.state()["location"]["name"]

    def find_mineable(self):
        data = self.surroundings(SCAN_RADIUS)
        px = data["center"]["x"]
        py = data["center"]["y"]
        targets = []
        for t in data.get("tiles", []):
            obj = t.get("object")
            if obj and obj in MINEABLE_OBJECTS:
                dist = abs(t["x"] - px) + abs(t["y"] - py)
                targets.append((t["x"], t["y"], obj, dist))
        targets.sort(key=lambda t: t[3])
        return [(x, y, name) for x, y, name, _ in targets]

    def find_passable_neighbor(self, tx, ty):
        data = self.surroundings(SCAN_RADIUS)
        blocked = set()
        for t in data.get("tiles", []):
            if not t.get("passable", True):
                blocked.add((t["x"], t["y"]))
        for dx, dy, face_dir in [(0, 1, 0), (0, -1, 2), (-1, 0, 1), (1, 0, 3)]:
            nx, ny = tx + dx, ty + dy
            if (nx, ny) not in blocked:
                return nx, ny, face_dir
        return None

    def hp_pct(self):
        hp, max_hp = self.player_hp()
        return (hp / max_hp * 100) if max_hp > 0 else 0

    def stamina_pct(self):
        sta, max_sta = self.player_stamina()
        return (sta / max_sta * 100) if max_sta > 0 else 0

    def game_time(self):
        s = self.state()
        return s.get("time", {}).get("timeOfDay", 600)

    def is_safe(self, hp_threshold):
        hp_ok = self.hp_pct() >= hp_threshold
        sta_ok = self.stamina_pct() >= 15
        time_ok = self.game_time() < 2300
        if not hp_ok:
            log(f"  hp too low ({self.hp_pct():.0f}%)")
        if not sta_ok:
            log(f"  stamina too low ({self.stamina_pct():.0f}%)")
        if not time_ok:
            log(f"  too late ({self.game_time()}), time to go home")
        return hp_ok and sta_ok and time_ok

    def emergency_retreat(self):
        log("  !!! RETREAT → warp to Farm !!!")
        self.warp("Farm")

    def mine_tile(self, tx, ty, name, hp_threshold=30):
        neighbor = self.find_passable_neighbor(tx, ty)
        if neighbor is None:
            log(f"  cannot reach ({tx},{ty}) {name}, skip")
            return "skip"
        nx, ny, face_dir = neighbor
        self.move_to(nx, ny)
        self.face(face_dir)
        time.sleep(0.15)
        for _ in range(3):
            if not self.is_safe(hp_threshold):
                self.emergency_retreat()
                return "retreat"
            self.use_tool("Pickaxe")
            time.sleep(TOOL_DELAY)
        return "ok"


def run(port, start_level, max_levels, hp_threshold):
    bot = MineBot(port)

    st = bot.status()
    if not st.get("worldReady"):
        log("world not ready")
        return

    bot.select("Pickaxe")
    log(f"=== mine run: levels {start_level}-{start_level + max_levels - 1}, hp threshold {hp_threshold}% ===")

    for i in range(max_levels):
        level = start_level + i
        loc_name = f"UndergroundMine{level}"

        log(f"--- warp to level {level} ---")
        result = bot.warp(loc_name)
        if not result.get("ok"):
            log(f"  warp failed: {result.get('error', '?')}")
            log("  trying 'Mine' entrance instead...")
            result = bot.warp("Mine")
            if not result.get("ok"):
                log(f"  cannot reach mine, abort")
                return
            break

        time.sleep(1.5)

        if not bot.is_safe(hp_threshold):
            bot.emergency_retreat()
            return

        attempts = 0
        max_attempts = 20
        while attempts < max_attempts:
            attempts += 1

            if not bot.is_safe(hp_threshold):
                bot.emergency_retreat()
                return

            targets = bot.find_mineable()
            if not targets:
                log("  no more rocks, next level")
                break

            for tx, ty, name in targets[:5]:
                if not bot.is_safe(hp_threshold):
                    bot.emergency_retreat()
                    return

                log(f"  mining {name} ({tx},{ty})")
                result = bot.mine_tile(tx, ty, name, hp_threshold)
                if result == "retreat":
                    return

        log(f"=== level {level} done ({i+1}/{max_levels}) ===")

    log(f"=== mine run complete ===")
    bot.warp("Farm")
    log("warped home")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7842)
    parser.add_argument("--start-level", type=int, default=1)
    parser.add_argument("--max-levels", type=int, default=5)
    parser.add_argument("--hp-threshold", type=int, default=30)
    args = parser.parse_args()

    run(args.port, args.start_level, args.max_levels, args.hp_threshold)
