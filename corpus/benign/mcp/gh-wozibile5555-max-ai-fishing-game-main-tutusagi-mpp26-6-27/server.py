"""
钓鱼游戏 MCP Server + 管理面板后端
统一端口 11125，HTTP 协议
- /          前端管理面板
- /mcp       MCP endpoint：兼容 SSE(GET) 和 Streamable HTTP(POST/GET/DELETE)
- /mcp-http  MCP Streamable HTTP endpoint（Kelivo/新版客户端可连这个）
- /api/...   管理 API
- /ws/logs   WebSocket 实时日志
"""

import asyncio
import base64
from contextlib import asynccontextmanager
import copy
import gzip
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# MCP imports
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import Tool, TextContent

# 把当前目录加入 path 以便 import engine
sys.path.insert(0, str(Path(__file__).parent))
import engine

# ============================================================
# Logging & 实时日志广播
# ============================================================

log_subscribers: list[WebSocket] = []
game_logs: list[dict] = []

MAX_LOG_HISTORY = 200


async def broadcast_log(entry: dict):
    """广播日志给所有 WebSocket 连接"""
    game_logs.append(entry)
    if len(game_logs) > MAX_LOG_HISTORY:
        game_logs.pop(0)
    dead = []
    for ws in log_subscribers:
        try:
            await ws.send_json(entry)
        except Exception:
            dead.append(ws)
    for ws in dead:
        log_subscribers.remove(ws)


def log_game_action(command: str, result: str):
    """同步记录日志，后台异步广播"""
    entry = {
        "time": time.strftime("%H:%M:%S"),
        "command": command,
        "result": result[:500],  # 截断避免太长
        "full_result": result,
    }
    game_logs.append(entry)
    if len(game_logs) > MAX_LOG_HISTORY:
        game_logs.pop(0)
    # 尝试异步广播
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(broadcast_log(entry))
    except RuntimeError:
        pass


# ============================================================
# 自定义配置管理（前端可调度）
# ============================================================

DEFAULT_CUSTOM_CONFIG = {
    "bait_limits": {},  # {"basic_worm": 20, "glow_bait": 5} — 每次购买上限
    "disabled_baits": [],  # 禁用的鱼饵 ID
    "custom_baits": {},
    "custom_locations": {},
    "custom_fish": {},
    "deleted_baits": [],
    "deleted_locations": [],
    "deleted_fish": [],
    "tool_descriptions": {
        "play_fishing": "文字钓鱼游戏。传入指令如: help, status, cast, cast 10, buy basic_worm 5; cast 10, goto, sell all, dive 5, encyclopedia 等。支持用 ; 串联多条指令一次执行（最多8条）。\n\n常用指令：\n- help 看规则\n- status 看状态\n- shop 看商店\n- buy <饵id> [数量] 买饵\n- cast [饵id] [次数] [stop=new,rare,event] 抛竿\n- cast 10 stop=rare 连钓10竿遇稀有就停\n- goto 列出地点 / goto <地点id> 前往\n- sell all 卖掉所有鱼\n- inventory 看背包\n- encyclopedia 看图鉴\n- dive [氧气瓶数] 潜水远征\n- buy basic_worm 10; cast 10 买饵再钓一条龙",
        "new_fishing_game": "重开一局钓鱼游戏。可选传入 seed 整数作为随机种子，相同种子+相同指令序列=完全相同结果。不传则用默认种子。"
    },
}

custom_config = copy.deepcopy(DEFAULT_CUSTOM_CONFIG)


def get_custom_config_path():
    return Path(__file__).parent / "custom_config.json"


def normalize_custom_config(data):
    cfg = copy.deepcopy(DEFAULT_CUSTOM_CONFIG)
    if not isinstance(data, dict):
        return cfg
    for key, value in data.items():
        if key == "tool_descriptions" and isinstance(value, dict):
            cfg[key].update(value)
        elif key in cfg:
            cfg[key] = value
    for key in ["bait_limits", "custom_baits", "custom_locations", "custom_fish", "tool_descriptions"]:
        if not isinstance(cfg.get(key), dict):
            cfg[key] = copy.deepcopy(DEFAULT_CUSTOM_CONFIG[key])
    for key in ["disabled_baits", "deleted_baits", "deleted_locations", "deleted_fish"]:
        if not isinstance(cfg.get(key), list):
            cfg[key] = []
    return cfg


def apply_custom_content():
    for bait_id in custom_config.get("deleted_baits", []):
        engine.BAITS.pop(bait_id, None)
    for loc_id in custom_config.get("deleted_locations", []):
        engine.LOCATIONS.pop(loc_id, None)
    for fish_id in custom_config.get("deleted_fish", []):
        engine.FISH.pop(fish_id, None)

    for bait_id, bait in custom_config.get("custom_baits", {}).items():
        bait = dict(bait)
        bait["id"] = bait_id
        bait.setdefault("effects", {})
        engine.BAITS[bait_id] = bait
    for loc_id, loc in custom_config.get("custom_locations", {}).items():
        loc = dict(loc)
        loc["id"] = loc_id
        loc.setdefault("junk_chance_base", 0.1)
        loc.setdefault("tag_weight_mult", {})
        loc.setdefault("available_seasons", ["spring", "summer", "autumn", "winter"])
        loc.setdefault("ambience", [])
        loc.setdefault("character", "")
        loc.setdefault("dive_enabled", True)
        loc.setdefault("dive_description", "")
        loc.setdefault("dive_available_seasons", loc.get("available_seasons", ["spring", "summer", "autumn", "winter"]))
        loc.setdefault("dive_ambience", {})
        loc.setdefault("dive_notes", "")
        engine.LOCATIONS[loc_id] = loc
    for fish_id, fish in custom_config.get("custom_fish", {}).items():
        fish = dict(fish)
        fish["id"] = fish_id
        fish.setdefault("size_unit", "cm")
        fish.setdefault("locations", [])
        fish.setdefault("seasons", ["all"])
        fish.setdefault("tags", [])
        fish.setdefault("dive", False)
        engine.FISH[fish_id] = fish


def remember_content(kind: str, item_id: str, item: dict):
    key = f"custom_{kind}"
    custom_config.setdefault(key, {})[item_id] = copy.deepcopy(item)
    deleted_key = f"deleted_{kind}"
    if item_id in custom_config.setdefault(deleted_key, []):
        custom_config[deleted_key].remove(item_id)


def forget_content(kind: str, item_id: str):
    custom_config.setdefault(f"custom_{kind}", {}).pop(item_id, None)
    deleted_key = f"deleted_{kind}"
    if item_id not in custom_config.setdefault(deleted_key, []):
        custom_config[deleted_key].append(item_id)


def clean_save_after_bait_delete(bait_id: str):
    state = engine._load()
    state.get("bait_inventory", {}).pop(bait_id, None)
    engine._save()


def clean_save_after_fish_delete(fish_id: str):
    state = engine._load()
    state["catch_inventory"] = [c for c in state.get("catch_inventory", []) if c.get("fish_id") != fish_id]
    state.get("encyclopedia", {}).pop(fish_id, None)
    engine._save()


def clean_save_after_location_delete(location_id: str):
    state = engine._load()
    for key in ["unlocked_locations", "dive_unlocked"]:
        if location_id in state.get(key, []):
            state[key].remove(location_id)
    state.get("map_fragments", {}).pop(location_id, None)
    if state.get("location_id") == location_id:
        fallback = "moonlit_pond" if "moonlit_pond" in engine.LOCATIONS else next(iter(engine.LOCATIONS), None)
        if fallback:
            state["location_id"] = fallback
            if fallback not in state.setdefault("unlocked_locations", []):
                state["unlocked_locations"].append(fallback)
    engine._save()


def validate_fish_locations(locations):
    if not locations:
        return "鱼种至少需要一个出没地点"
    invalid = [loc for loc in locations if loc != "all" and loc not in engine.LOCATIONS]
    if invalid:
        return "地点不存在：" + ", ".join(invalid)
    return None


def fish_referencing_location(location_id: str):
    return [fish for fish in engine.FISH.values() if location_id in fish.get("locations", [])]


def normalize_dive_ambience(value):
    """把前端传来的深水氛围统一成 {season: [line, ...]}。"""
    if not isinstance(value, dict):
        return {}
    out = {}
    for season in ["spring", "summer", "autumn", "winter"]:
        raw = value.get(season, [])
        if isinstance(raw, str):
            lines = raw.splitlines()
        elif isinstance(raw, list):
            lines = raw
        else:
            lines = []
        cleaned = [str(x).strip() for x in lines if str(x).strip()]
        if cleaned:
            out[season] = cleaned
    return out


def public_fish_payload(fid: str, fish: dict, location_id: Optional[str] = None):
    locs = fish.get("locations", [])
    payload = {
        "id": fid,
        "name": fish.get("name", fid),
        "rarity": fish.get("rarity", "common"),
        "base_value": fish.get("base_value", 0),
        "locations": locs,
        "seasons": fish.get("seasons", []),
        "tags": fish.get("tags", []),
        "dive": fish.get("dive", False),
        "capture_feel": fish.get("capture_feel", ""),
        "description": fish.get("description", "")[:100],
    }
    if location_id is not None:
        payload["global"] = "all" in locs
        payload["explicit"] = location_id in locs
    return payload


def removable_bait_error(bait_id: str):
    if bait_id == "basic_worm":
        return "普通蚯蚓是默认鱼饵和潜水权重基准，不能删除；可以改价格或禁用其他鱼饵。"
    if len(engine.BAITS) <= 1:
        return "至少要保留一种鱼饵，否则 MCP 无法正常 cast。"
    state = engine._load()
    if state.get("bait_inventory", {}).get(bait_id, 0) > 0:
        return "存档里还有这个鱼饵库存，请先用掉或重开后再删除。"
    return None


def load_custom_config():
    global custom_config
    p = get_custom_config_path()
    if p.exists():
        try:
            custom_config = normalize_custom_config(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            custom_config = copy.deepcopy(DEFAULT_CUSTOM_CONFIG)
    apply_custom_content()


def save_custom_config():
    p = get_custom_config_path()
    p.write_text(json.dumps(custom_config, ensure_ascii=False, indent=2), encoding="utf-8")


load_custom_config()


# ============================================================
# MCP Server 定义
# ============================================================

mcp_server = Server("fishing-game")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    # 动态读取自定义工具描述
    descs = custom_config.get("tool_descriptions", {})
    play_desc = descs.get("play_fishing", "文字钓鱼游戏。传入指令如: help, status, cast, cast 10, buy basic_worm 5; cast 10, goto, sell all, dive 5, encyclopedia 等。")
    new_game_desc = descs.get("new_fishing_game", "重开一局钓鱼游戏。")

    return [
        Tool(
            name="play_fishing",
            description=play_desc,
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "游戏指令，如 cast 10 stop=rare, buy basic_worm 5; cast 10, goto reed_river 等"
                    }
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="new_fishing_game",
            description=new_game_desc,
            inputSchema={
                "type": "object",
                "properties": {
                    "seed": {
                        "type": "integer",
                        "description": "随机种子，不填则使用默认种子"
                    }
                }
            }
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "play_fishing":
        command = arguments.get("command", "help")
        # 应用自定义限制
        result = engine.cmd(command)
        log_game_action(command, result)
        print(f"[MCP] play_fishing: {command[:60]}")
        return [TextContent(type="text", text=result)]
    elif name == "new_fishing_game":
        seed = arguments.get("seed", None)
        if seed is not None:
            result = engine.new_game(seed)
        else:
            result = engine.new_game()
        log_game_action(f"new_game({seed})", result)
        print(f"[MCP] new_game: seed={seed}")
        return [TextContent(type="text", text=result)]
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


# ============================================================
# FastAPI 应用
# ============================================================

# Streamable HTTP Transport（MCP 2025+）
# 关闭 DNS rebinding host 校验，方便局域网设备/Kelivo 通过 192.168.x.x 访问。
streamable_http_manager = StreamableHTTPSessionManager(
    app=mcp_server,
    json_response=False,
    stateless=False,
    security_settings=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with streamable_http_manager.run():
        yield


app = FastAPI(title="Fishing Game MCP Server", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
web_dir = Path(__file__).parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

# MCP SSE Transport
sse_transport = SseServerTransport("/mcp/messages/")


@app.get("/mcp")
async def mcp_sse(request: Request):
    # 新版 Streamable HTTP 客户端初始化后，会带 MCP-Session-Id 对同一个 URL 发 GET
    # 来建立服务端通知流；旧版 SSE 客户端不会带该 header。
    if "mcp-session-id" in request.headers:
        await streamable_http_manager.handle_request(request.scope, request.receive, request._send)
        return
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


@app.post("/mcp")
async def mcp_streamable_http(request: Request):
    """MCP Streamable HTTP endpoint：Kelivo/新版 MCP 客户端可直接连接此地址。"""
    await streamable_http_manager.handle_request(request.scope, request.receive, request._send)


@app.delete("/mcp")
async def mcp_streamable_http_delete(request: Request):
    """MCP Streamable HTTP session terminate endpoint。"""
    await streamable_http_manager.handle_request(request.scope, request.receive, request._send)


@app.api_route("/mcp-http", methods=["GET", "POST", "DELETE"])
async def mcp_streamable_http_alias(request: Request):
    """显式 Streamable HTTP 地址，避免和旧 SSE 客户端混用。"""
    await streamable_http_manager.handle_request(request.scope, request.receive, request._send)


@app.post("/mcp/messages/")
async def mcp_messages(request: Request):
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)


# ============================================================
# 前端页面
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = web_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Web directory not found</h1>")


# ============================================================
# WebSocket 实时日志
# ============================================================

@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    log_subscribers.append(websocket)
    # 发送历史日志
    try:
        for entry in game_logs[-50:]:
            await websocket.send_json(entry)
        while True:
            # 保持连接
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in log_subscribers:
            log_subscribers.remove(websocket)


# ============================================================
# 管理 API
# ============================================================

@app.get("/api/status")
async def api_status():
    """获取游戏当前状态"""
    result = engine.cmd("status")
    return JSONResponse({"status": "ok", "game_status": result})


@app.post("/api/command")
async def api_command(request: Request):
    """直接执行游戏指令"""
    body = await request.json()
    command = body.get("command", "status")
    result = engine.cmd(command)
    log_game_action(f"[Panel] {command}", result)
    return JSONResponse({"result": result})


@app.post("/api/new_game")
async def api_new_game(request: Request):
    """重开一局"""
    body = await request.json()
    seed = body.get("seed", None)
    if seed is not None:
        result = engine.new_game(int(seed))
    else:
        result = engine.new_game()
    log_game_action(f"[Panel] new_game({seed})", result)
    return JSONResponse({"result": result})


# --- 鱼饵管理 ---

@app.get("/api/baits")
async def api_get_baits():
    """获取所有鱼饵配置"""
    baits = []
    for bid, bait in engine.BAITS.items():
        baits.append({
            "id": bid,
            "name": bait["name"],
            "cost": bait["cost"],
            "description": bait["description"],
            "limit": custom_config.get("bait_limits", {}).get(bid, None),
            "disabled": bid in custom_config.get("disabled_baits", []),
        })
    return JSONResponse({"baits": baits})


@app.post("/api/baits/add")
async def api_add_bait(request: Request):
    """新增自定义鱼饵"""
    body = await request.json()
    bait_id = body.get("id")
    if not bait_id:
        bait_id = "custom_bait_" + str(len(engine.BAITS) + 1)
    if bait_id in engine.BAITS:
        return JSONResponse({"error": "鱼饵 ID 已存在"}, status_code=400)

    new_bait = {
        "id": bait_id,
        "name": body.get("name", "自定义鱼饵"),
        "cost": int(body.get("cost", 20)),
        "description": body.get("description", "自定义鱼饵"),
        "effects": body.get("effects", {}),
    }
    engine.BAITS[bait_id] = new_bait
    remember_content("baits", bait_id, new_bait)
    save_custom_config()
    return JSONResponse({"ok": True, "bait": new_bait})


@app.post("/api/baits/delete")
async def api_delete_bait(request: Request):
    """删除鱼饵"""
    body = await request.json()
    bait_id = body.get("id")
    if bait_id not in engine.BAITS:
        return JSONResponse({"error": "鱼饵不存在"}, status_code=404)
    remove_error = removable_bait_error(bait_id)
    if remove_error:
        return JSONResponse({"error": remove_error}, status_code=400)
    del engine.BAITS[bait_id]
    forget_content("baits", bait_id)
    custom_config.get("bait_limits", {}).pop(bait_id, None)
    if bait_id in custom_config.get("disabled_baits", []):
        custom_config["disabled_baits"].remove(bait_id)
    clean_save_after_bait_delete(bait_id)
    save_custom_config()
    return JSONResponse({"ok": True})


@app.get("/api/baits/effects/{bait_id}")
async def api_get_bait_effects(bait_id: str):
    """获取单个鱼饵的 effects"""
    if bait_id not in engine.BAITS:
        return JSONResponse({"error": "鱼饵不存在"}, status_code=404)
    return JSONResponse({"id": bait_id, "effects": engine.BAITS[bait_id].get("effects", {})})


@app.post("/api/baits/update")
async def api_update_bait(request: Request):
    """更新鱼饵配置"""
    body = await request.json()
    bait_id = body.get("id")
    if bait_id not in engine.BAITS:
        return JSONResponse({"error": "鱼饵不存在"}, status_code=400)

    if "cost" in body:
        engine.BAITS[bait_id]["cost"] = int(body["cost"])
    if "name" in body:
        engine.BAITS[bait_id]["name"] = body["name"]
    if "description" in body:
        engine.BAITS[bait_id]["description"] = body["description"]
    if "effects" in body:
        engine.BAITS[bait_id]["effects"] = body["effects"] or {}
    if "limit" in body:
        if body["limit"] is None:
            custom_config.get("bait_limits", {}).pop(bait_id, None)
        else:
            custom_config.setdefault("bait_limits", {})[bait_id] = int(body["limit"])
    if "disabled" in body:
        if body["disabled"]:
            if bait_id not in custom_config.setdefault("disabled_baits", []):
                custom_config["disabled_baits"].append(bait_id)
        else:
            if bait_id in custom_config.get("disabled_baits", []):
                custom_config["disabled_baits"].remove(bait_id)

    remember_content("baits", bait_id, engine.BAITS[bait_id])
    save_custom_config()
    return JSONResponse({"ok": True})


# --- 地点 & 渔获管理 ---

@app.get("/api/locations")
async def api_get_locations():
    """获取所有地点"""
    locs = []
    for lid, loc in engine.LOCATIONS.items():
        locs.append({
            "id": lid,
            "name": loc["name"],
            "description": loc.get("description", ""),
            "character": loc.get("character", ""),
            "unlock_cost": loc.get("unlock_cost", 0),
            "available_seasons": loc.get("available_seasons", []),
            "dive_enabled": loc.get("dive_enabled", True),
            "dive_description": loc.get("dive_description", ""),
            "dive_available_seasons": loc.get("dive_available_seasons", loc.get("available_seasons", [])),
            "dive_ambience": loc.get("dive_ambience", {}),
            "dive_notes": loc.get("dive_notes", ""),
        })
    return JSONResponse({"locations": locs})


@app.post("/api/locations/add")
async def api_add_location(request: Request):
    """新增地点"""
    body = await request.json()
    loc_id = body.get("id")
    if not loc_id:
        return JSONResponse({"error": "需要 id"}, status_code=400)
    if loc_id in engine.LOCATIONS:
        return JSONResponse({"error": "地点 ID 已存在"}, status_code=400)

    new_loc = {
        "id": loc_id,
        "name": body.get("name", loc_id),
        "description": body.get("description", ""),
        "junk_chance_base": 0.1,
        "tag_weight_mult": {},
        "unlock_cost": body.get("unlock_cost", 0),
        "available_seasons": body.get("available_seasons", ["spring", "summer", "autumn", "winter"]),
        "ambience": [],
        "character": "",
        "dive_enabled": bool(body.get("dive_enabled", True)),
        "dive_description": body.get("dive_description", ""),
        "dive_available_seasons": body.get("dive_available_seasons", body.get("available_seasons", ["spring", "summer", "autumn", "winter"])),
        "dive_ambience": normalize_dive_ambience(body.get("dive_ambience", {})),
        "dive_notes": body.get("dive_notes", ""),
    }
    engine.LOCATIONS[loc_id] = new_loc
    remember_content("locations", loc_id, new_loc)
    save_custom_config()
    return JSONResponse({"ok": True, "location": new_loc})


@app.post("/api/locations/update")
async def api_update_location(request: Request):
    """编辑地点"""
    body = await request.json()
    loc_id = body.get("id")
    if loc_id not in engine.LOCATIONS:
        return JSONResponse({"error": "地点不存在"}, status_code=404)

    loc = engine.LOCATIONS[loc_id]
    if "name" in body:
        loc["name"] = body["name"]
    if "description" in body:
        loc["description"] = body["description"]
    if "unlock_cost" in body:
        loc["unlock_cost"] = int(body["unlock_cost"])
    if "available_seasons" in body:
        loc["available_seasons"] = body["available_seasons"]
    if "dive_enabled" in body:
        loc["dive_enabled"] = bool(body["dive_enabled"])
    if "dive_description" in body:
        loc["dive_description"] = body["dive_description"]
    if "dive_available_seasons" in body:
        loc["dive_available_seasons"] = body["dive_available_seasons"]
    if "dive_ambience" in body:
        loc["dive_ambience"] = normalize_dive_ambience(body["dive_ambience"])
    if "dive_notes" in body:
        loc["dive_notes"] = body["dive_notes"]
    remember_content("locations", loc_id, loc)
    save_custom_config()
    return JSONResponse({"ok": True, "location": loc})


@app.post("/api/locations/delete")
async def api_delete_location(request: Request):
    """删除地点"""
    body = await request.json()
    loc_id = body.get("id")
    if loc_id not in engine.LOCATIONS:
        return JSONResponse({"error": "地点不存在"}, status_code=404)
    blockers = fish_referencing_location(loc_id)
    if blockers:
        return JSONResponse({
            "error": "还有鱼种引用这个地点，先编辑这些鱼的出没地点再删除",
            "fish": [{"id": fish["id"], "name": fish.get("name", fish["id"])} for fish in blockers[:20]],
        }, status_code=400)
    del engine.LOCATIONS[loc_id]
    forget_content("locations", loc_id)
    clean_save_after_location_delete(loc_id)
    save_custom_config()
    return JSONResponse({"ok": True})


@app.get("/api/locations/{location_id}/fish")
async def api_get_location_fish(location_id: str):
    """获取某地点可钓到的鱼"""
    if location_id not in engine.LOCATIONS:
        return JSONResponse({"error": "地点不存在"}, status_code=404)

    fish_list = []
    for fid, fish in engine.FISH.items():
        locs = fish.get("locations", [])
        if location_id in locs or "all" in locs:
            fish_list.append(public_fish_payload(fid, fish, location_id))
    return JSONResponse({"location_id": location_id, "fish": fish_list})


@app.post("/api/fish/add")
async def api_add_fish(request: Request):
    """添加自定义鱼种"""
    body = await request.json()
    fish_id = body.get("id")
    if not fish_id:
        return JSONResponse({"error": "需要 id"}, status_code=400)
    if fish_id in engine.FISH:
        return JSONResponse({"error": "鱼种 ID 已存在"}, status_code=400)

    new_fish = {
        "id": fish_id,
        "name": body.get("name", fish_id),
        "rarity": body.get("rarity", "common"),
        "description": body.get("description", "自定义鱼种"),
        "size_min": int(body.get("size_min", 5)),
        "size_max": int(body.get("size_max", 30)),
        "size_unit": "cm",
        "base_value": int(body.get("base_value", 10)),
        "locations": body.get("locations", []),
        "seasons": body.get("seasons", ["all"]),
        "tags": body.get("tags", []),
        "latin": body.get("latin", "Custom species"),
        "dive": bool(body.get("dive", False)),
        "capture_feel": body.get("capture_feel", ""),
    }
    if new_fish["dive"] and "underwater" not in new_fish["tags"]:
        new_fish["tags"].append("underwater")
    location_error = validate_fish_locations(new_fish["locations"])
    if location_error:
        return JSONResponse({"error": location_error}, status_code=400)
    engine.FISH[fish_id] = new_fish
    remember_content("fish", fish_id, new_fish)
    save_custom_config()
    return JSONResponse({"ok": True, "fish": new_fish})


@app.post("/api/fish/update")
async def api_update_fish(request: Request):
    """编辑已有鱼种"""
    body = await request.json()
    fish_id = body.get("id")
    if fish_id not in engine.FISH:
        return JSONResponse({"error": "鱼种不存在"}, status_code=404)

    fish = copy.deepcopy(engine.FISH[fish_id])
    for key in ["name", "rarity", "description", "base_value", "size_min", "size_max", "locations", "seasons", "tags", "dive", "capture_feel"]:
        if key in body:
            fish[key] = body[key]
    fish["dive"] = bool(fish.get("dive", False))
    fish.setdefault("tags", [])
    if fish["dive"] and "underwater" not in fish["tags"]:
        fish["tags"].append("underwater")
    for key in ["base_value", "size_min", "size_max"]:
        if key in fish:
            fish[key] = int(fish[key])
    location_error = validate_fish_locations(fish.get("locations", []))
    if location_error:
        return JSONResponse({"error": location_error}, status_code=400)
    engine.FISH[fish_id] = fish
    remember_content("fish", fish_id, fish)
    save_custom_config()
    return JSONResponse({"ok": True, "fish": fish})


@app.post("/api/fish/delete")
async def api_delete_fish(request: Request):
    """删除鱼种"""
    body = await request.json()
    fish_id = body.get("id")
    if fish_id not in engine.FISH:
        return JSONResponse({"error": "鱼种不存在"}, status_code=404)
    del engine.FISH[fish_id]
    forget_content("fish", fish_id)
    clean_save_after_fish_delete(fish_id)
    save_custom_config()
    return JSONResponse({"ok": True})


@app.post("/api/fish/remove_from_location")
async def api_remove_fish_from_location(request: Request):
    """从某地点移除一种鱼"""
    body = await request.json()
    fish_id = body.get("fish_id")
    location_id = body.get("location_id")
    if fish_id not in engine.FISH:
        return JSONResponse({"error": "鱼种不存在"}, status_code=404)
    locs = engine.FISH[fish_id].get("locations", [])
    if location_id in locs:
        if len(locs) <= 1:
            return JSONResponse({"error": "不能移除最后一个出没地点，否则会产生孤儿鱼种"}, status_code=400)
        locs.remove(location_id)
        remember_content("fish", fish_id, engine.FISH[fish_id])
        save_custom_config()
    return JSONResponse({"ok": True})


@app.post("/api/fish/add_to_location")
async def api_add_fish_to_location(request: Request):
    """给某地点添加一种鱼"""
    body = await request.json()
    fish_id = body.get("fish_id")
    location_id = body.get("location_id")
    if fish_id not in engine.FISH:
        return JSONResponse({"error": "鱼种不存在"}, status_code=404)
    if location_id not in engine.LOCATIONS:
        return JSONResponse({"error": "地点不存在"}, status_code=404)
    locs = engine.FISH[fish_id].get("locations", [])
    if location_id not in locs:
        locs.append(location_id)
        engine.FISH[fish_id]["locations"] = locs
    if "dive" in body:
        engine.FISH[fish_id]["dive"] = bool(body.get("dive"))
        engine.FISH[fish_id].setdefault("tags", [])
        if engine.FISH[fish_id]["dive"] and "underwater" not in engine.FISH[fish_id]["tags"]:
            engine.FISH[fish_id]["tags"].append("underwater")
    remember_content("fish", fish_id, engine.FISH[fish_id])
    save_custom_config()
    return JSONResponse({"ok": True})


# --- 概率计算 ---

@app.get("/api/probability/{location_id}")
async def api_probability(location_id: str, season: str = "spring", mode: str = "cast"):
    """计算某地点+季节的鱼种概率"""
    if location_id not in engine.LOCATIONS:
        return JSONResponse({"error": "地点不存在"}, status_code=404)

    loc = engine.LOCATIONS[location_id]
    season_data = engine.SEASONS.get(season, {})
    dive_mode = mode == "dive"
    results = []

    for fid, fish in engine.FISH.items():
        fish_locs = fish.get("locations", [])
        fish_seasons = fish.get("seasons", [])
        if location_id not in fish_locs and "all" not in fish_locs:
            continue
        if season not in fish_seasons and "all" not in fish_seasons:
            continue
        if bool(fish.get("dive", False)) != dive_mode:
            continue
        if dive_mode and fish.get("branch_only"):
            continue

        rarity = fish.get("rarity", "common")
        base_weight = engine.RARITY.get(rarity, {}).get("weight", 100)

        # 应用地点 tag 权重
        weight = base_weight
        for tag in fish.get("tags", []):
            mult = loc.get("tag_weight_mult", {}).get(tag, 1.0)
            weight *= mult
            # 季节 tag 加成
            s_mult = season_data.get("tag_weight_mult", {}).get(tag, 1.0)
            weight *= s_mult

        # 个体权重
        ind_w = fish.get("individual_weight", None)
        if ind_w is not None:
            weight *= ind_w

        results.append({
            "id": fid,
            "name": fish["name"],
            "rarity": rarity,
            "weight": round(weight, 2),
        })

    # 计算概率百分比
    total = sum(r["weight"] for r in results) or 1
    for r in results:
        r["probability"] = round(r["weight"] / total * 100, 2)

    results.sort(key=lambda x: -x["weight"])
    return JSONResponse({"location_id": location_id, "season": season, "mode": mode, "fish": results})


# --- 所有鱼种列表 ---

@app.get("/api/fish")
async def api_all_fish():
    """获取所有鱼种"""
    fish_list = []
    for fid, fish in engine.FISH.items():
        fish_list.append(public_fish_payload(fid, fish))
    return JSONResponse({"fish": fish_list})


# --- 工具描述管理 ---

@app.get("/api/tool_descriptions")
async def api_get_tool_descriptions():
    """获取自定义工具描述"""
    descs = custom_config.get("tool_descriptions", {})
    return JSONResponse({"tool_descriptions": descs})


@app.post("/api/tool_descriptions/update")
async def api_update_tool_descriptions(request: Request):
    """保存自定义工具描述"""
    body = await request.json()
    custom_config.setdefault("tool_descriptions", {})
    if "play_fishing" in body:
        custom_config["tool_descriptions"]["play_fishing"] = body["play_fishing"]
    if "new_fishing_game" in body:
        custom_config["tool_descriptions"]["new_fishing_game"] = body["new_fishing_game"]
    save_custom_config()
    return JSONResponse({"ok": True})


# --- 导入导出 ---

@app.get("/api/export")
async def api_export():
    """导出所有配置和存档"""
    config_data = copy.deepcopy(custom_config)
    save_path = Path(__file__).parent / "fishing_save.json"
    save_data = {}
    if save_path.exists():
        try:
            save_data = json.loads(save_path.read_text(encoding="utf-8"))
        except Exception:
            save_data = {}

    export_payload = {
        "version": 1,
        "custom_config": config_data,
        "save_data": save_data,
    }

    json_bytes = json.dumps(export_payload, ensure_ascii=False).encode("utf-8")
    compressed = gzip.compress(json_bytes, compresslevel=9)
    b64 = base64.b64encode(compressed).decode("ascii")

    return JSONResponse({"ok": True, "data": b64, "size_original": len(json_bytes), "size_compressed": len(compressed)})


@app.post("/api/import")
async def api_import(request: Request):
    """导入配置和存档"""
    body = await request.json()
    b64_data = body.get("data", "")
    if not b64_data:
        return JSONResponse({"error": "没有数据"}, status_code=400)

    try:
        compressed = base64.b64decode(b64_data)
        json_bytes = gzip.decompress(compressed)
        payload = json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        return JSONResponse({"error": f"解压/解析失败：{str(e)}"}, status_code=400)

    if payload.get("version") != 1:
        return JSONResponse({"error": "不支持的导出版本"}, status_code=400)

    # 恢复 custom_config
    global custom_config
    custom_config = normalize_custom_config(payload.get("custom_config", {}))
    save_custom_config()

    # 恢复存档
    save_data = payload.get("save_data", {})
    save_path = Path(__file__).parent / "fishing_save.json"
    save_path.write_text(json.dumps(save_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 重载引擎
    import importlib
    importlib.reload(engine)
    apply_custom_content()
    engine._load()

    return JSONResponse({"ok": True, "message": "导入成功，配置和存档已恢复"})


# --- 日志 ---

@app.get("/api/logs")
async def api_logs():
    """获取历史日志"""
    return JSONResponse({"logs": game_logs[-100:]})


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  🎣 钓鱼游戏 MCP Server")
    print(f"  管理面板: http://localhost:11125")
    print(f"  MCP SSE:  http://localhost:11125/mcp")
    print(f"  MCP HTTP: http://localhost:11125/mcp-http")
    print(f"  WebSocket: ws://localhost:11125/ws/logs")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=11125, log_level="info")
