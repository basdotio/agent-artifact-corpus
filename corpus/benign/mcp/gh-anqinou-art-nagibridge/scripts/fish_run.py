"""
自动钓鱼脚本：传送到钓鱼点 → 启动Fishbot → 每5条鱼检测体力/背包/时间 → 安全退出

用法:
    PYTHONIOENCODING=utf-8 python3 fish_run.py [--port 7842] [--location Beach] [--max-fish 30]

参数:
    --port          NagiBridge端口（默认 7842）
    --location      钓鱼地点（默认 Beach）
    --max-fish      最多钓几条就停（默认 30）
    --stamina-pct   体力低于此百分比停止（默认 15）
"""

import sys
import time
import argparse
import json
import urllib.request

FISHING_SPOTS = {
    "Beach": {"x": 42, "y": 36, "face": 2},
    "Mountain": {"x": 69, "y": 14, "face": 2},
    "Forest": {"x": 69, "y": 28, "face": 2},
}

CHECK_INTERVAL = 5


def log(msg):
    try:
        print(f"[fish] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[fish] {msg.encode('utf-8', errors='replace').decode('utf-8')}", flush=True)


class FishBot:
    def __init__(self, port):
        self.base = f"http://localhost:{port}"

    def _get(self, ep):
        return json.load(urllib.request.urlopen(f"{self.base}{ep}", timeout=10))

    def _post(self, ep, data=None):
        req = urllib.request.Request(
            f"{self.base}{ep}",
            json.dumps(data or {}).encode(),
            {"Content-Type": "application/json"},
        )
        return json.load(urllib.request.urlopen(req, timeout=10))

    def state(self):
        return self._get("/state")

    def warp(self, location):
        return self._post("/warp", {"location": location})

    def move_to(self, x, y):
        self._post("/move", {"x": x, "y": y})
        deadline = time.time() + 8
        while time.time() < deadline:
            s = self.state()
            if not s["player"]["isMoving"]:
                return True
            time.sleep(0.3)
        self._post("/stop")
        return False

    def face(self, direction):
        self._post("/face", {"direction": direction})

    def select(self, name):
        return self._post("/select", {"name": name})

    def sell(self):
        return self._post("/sell", {})

    def fishbot(self, action):
        return self._post("/fishbot", {"action": action})

    def stamina_pct(self):
        s = self.state()
        p = s["player"]
        return (p["stamina"] / p["maxStamina"] * 100) if p["maxStamina"] > 0 else 0

    def game_time(self):
        s = self.state()
        return s.get("time", {}).get("timeOfDay", 600)

    def inventory_space(self):
        s = self.state()
        p = s["player"]
        inv = p.get("inventory", [])
        if not inv:
            return -1
        total = len(inv)
        used = sum(1 for i in inv if i)
        return total - used

    def count_fish(self):
        s = self.state()
        p = s["player"]
        fishing = p.get("fishing", {})
        return fishing

    def is_fishing(self):
        s = self.state()
        f = s["player"].get("fishing", {})
        return f.get("isFishing", False) or f.get("isCasting", False) or f.get("isReeling", False)


def run(port, location, max_fish, stamina_threshold):
    bot = FishBot(port)

    st = bot._get("/status")
    if not st.get("worldReady"):
        log("world not ready")
        return

    spot = FISHING_SPOTS.get(location)
    if not spot:
        log(f"unknown fishing spot: {location}, known: {list(FISHING_SPOTS.keys())}")
        return

    log(f"=== fish run: {location} ({spot['x']},{spot['y']}), max {max_fish} fish ===")

    # select rod
    rod_names = ["Iridium Rod", "Fiberglass Rod", "Training Rod", "Bamboo Pole"]
    rod_found = False
    for name in rod_names:
        r = bot.select(name)
        if r.get("ok"):
            log(f"selected: {name}")
            rod_found = True
            break
    if not rod_found:
        log("no fishing rod found!")
        return

    # warp to fishing spot
    bot.warp("Farm")
    time.sleep(1)
    bot.warp(location)
    time.sleep(2)

    # move to position
    bot.move_to(spot["x"], spot["y"])
    time.sleep(0.5)
    bot.face(spot["face"])
    time.sleep(0.3)

    # re-select rod (warp might reset)
    for name in rod_names:
        r = bot.select(name)
        if r.get("ok"):
            break

    s = bot.state()
    p = s["player"]
    log(f"pos: ({p['x']},{p['y']}) tool: {p['currentTool']} stamina: {p['stamina']}")
    initial_stamina = p["stamina"]

    # start fishbot
    r = bot.fishbot("on")
    log(f"fishbot: {r}")

    # monitor loop
    fish_count = 0
    last_stamina = initial_stamina
    check_counter = 0

    while fish_count < max_fish:
        time.sleep(6)

        s = bot.state()
        p = s["player"]
        current_stamina = p["stamina"]

        # detect fish caught by stamina drop (each cast costs 8)
        if current_stamina < last_stamina:
            casts = int((last_stamina - current_stamina) / 8)
            if casts > 0:
                fish_count += casts
                log(f"  ~{fish_count} fish caught (stamina {current_stamina}/{p['maxStamina']})")
            last_stamina = current_stamina

        check_counter += 1
        if check_counter >= CHECK_INTERVAL:
            check_counter = 0

            # check stamina
            sta_pct = current_stamina / p["maxStamina"] * 100
            if sta_pct < stamina_threshold:
                log(f"  stamina low ({sta_pct:.0f}%), stopping")
                break

            # check time
            game_time = s.get("time", {}).get("timeOfDay", 600)
            if game_time >= 2300:
                log(f"  too late ({game_time}), stopping")
                break

            log(f"  check: stamina {sta_pct:.0f}%, time {game_time}, ~{fish_count} fish")

    # stop fishbot
    bot.fishbot("off")
    log(f"fishbot off, caught ~{fish_count} fish")

    # go home and sleep
    bot.warp("FarmHouse")
    time.sleep(1.5)
    try:
        bot._post("/sleep", {})
        log("went to bed")
    except Exception:
        log("warped home (sleep failed)")
    log("=== fish run complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7842)
    parser.add_argument("--location", default="Beach")
    parser.add_argument("--max-fish", type=int, default=30)
    parser.add_argument("--stamina-pct", type=int, default=15)
    args = parser.parse_args()

    run(args.port, args.location, args.max_fish, args.stamina_pct)
