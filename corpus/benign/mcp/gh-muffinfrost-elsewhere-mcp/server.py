import os
import math
import base64
import asyncio
import time
import datetime as dt

import httpx
from mcp.server.fastmcp import FastMCP, Image

API_KEY = os.environ["WINDY_API_KEY"]
BASE = "https://api.windy.com/webcams/api/v3"
INCLUDE = "location,images,player,urls,categories"
GH_TOKEN = os.getenv("GH_TOKEN")
GH_REPO = os.getenv("GH_REPO")  # 公开仓库，如 yourname/your-snaps，show 工具用

mcp = FastMCP(
    "webcam",
    host=os.getenv("HOST", "127.0.0.1"),
    port=int(os.getenv("PORT", "8787")),
)


async def _get(path, params=None):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{BASE}{path}", params=params,
                        headers={"x-windy-api-key": API_KEY})
        r.raise_for_status()
        return r.json()


def _slim(w):
    loc = w.get("location") or {}
    img = (w.get("images") or {}).get("current") or {}
    player = w.get("player") or {}
    return {
        "id": w.get("webcamId"),
        "title": w.get("title"),
        "status": w.get("status"),
        "city": loc.get("city"),
        "region": loc.get("region"),
        "country": loc.get("country"),
        "lat": loc.get("latitude"),
        "lon": loc.get("longitude"),
        "snapshot": img.get("preview") or img.get("thumbnail"),
        "live_player": player.get("live"),
        "day_timelapse": player.get("day"),
        "page": (w.get("urls") or {}).get("detail"),
        "last_updated": w.get("lastUpdatedOn"),
    }


async def _snapshot_bytes(webcam_id):
    info = await get_webcam(webcam_id)
    url = info.get("snapshot")
    if not url:
        raise ValueError("这个摄像头现在没有可用截图")
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
    return info, r.content


@mcp.tool()
async def search_nearby(lat: float, lon: float, radius_km: int = 50,
                        category: str | None = None, limit: int = 10) -> list[dict]:
    """按经纬度搜索附近的实时摄像头。radius_km 最大 250。
    category 可选，如 beach, mountain, city, harbor, lake, landscape, sunset 等（用 list_categories 查全部）。"""
    params = {"nearby": f"{lat},{lon},{min(radius_km, 250)}",
              "include": INCLUDE, "limit": min(limit, 50)}
    if category:
        params["categories"] = category
    data = await _get("/webcams", params)
    return [_slim(w) for w in data.get("webcams", [])]


@mcp.tool()
async def search_by_country(country: str, category: str | None = None,
                            limit: int = 10, offset: int = 0) -> list[dict]:
    """按国家搜索摄像头。country 用两位国家代码，如 CN, JP, IS（冰岛）, NO, AU, NZ。"""
    params = {"countries": country.upper(), "include": INCLUDE,
              "limit": min(limit, 50), "offset": offset}
    if category:
        params["categories"] = category
    data = await _get("/webcams", params)
    return [_slim(w) for w in data.get("webcams", [])]


@mcp.tool()
async def list_categories() -> list[dict]:
    """列出所有摄像头类别。"""
    data = await _get("/categories")
    return data if isinstance(data, list) else data.get("categories", data)


@mcp.tool()
async def get_webcam(webcam_id: str) -> dict:
    """查看某个摄像头的详细信息、最新截图和直播播放器链接。"""
    data = await _get(f"/webcams/{webcam_id}", {"include": INCLUDE})
    return _slim(data)


@mcp.tool()
async def look(webcam_id: str) -> Image:
    """直接看一眼某个摄像头此刻的画面（返回图片本身，只有 Claude 自己能看见）。"""
    _, data = await _snapshot_bytes(webcam_id)
    return Image(data=data, format="jpeg")


@mcp.tool()
async def show(webcam_id: str) -> dict:
    """把某个摄像头此刻的画面给用户看。返回 image_url（cdn.jsdelivr.net 链接）和一段 html，
    能渲染 html 的客户端直接放进去就能显示图片。想让用户看到画面时用这个，不要用 look。"""
    if not GH_TOKEN or not GH_REPO:
        raise ValueError("服务器上没配置 GH_TOKEN / GH_REPO")
    info, data = await _snapshot_bytes(webcam_id)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = f"snaps/{stamp}-{webcam_id}.jpg"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.put(
            f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
            headers={"Authorization": f"Bearer {GH_TOKEN}",
                     "Accept": "application/vnd.github+json"},
            json={"message": f"snap {webcam_id}",
                  "content": base64.b64encode(data).decode()},
        )
        r.raise_for_status()
        sha = r.json()["commit"]["sha"]
    url = f"https://cdn.jsdelivr.net/gh/{GH_REPO}@{sha}/{path}"
    place = " · ".join(x for x in (info.get("title"), info.get("country")) if x)
    return {
        "image_url": url,
        "place": place,
        "html": f'<img src="{url}" alt="{place}" style="width:100%;border-radius:12px;display:block">',
    }


def _sun_points(event, now):
    doy = now.timetuple().tm_yday
    decl = math.radians(23.44) * math.sin(math.radians(360 / 365 * (doy - 81)))
    utc_h = now.hour + now.minute / 60
    pts = []
    for lat in range(-45, 66, 10):
        x = -math.tan(math.radians(lat)) * math.tan(decl)
        if abs(x) > 1:
            continue
        h0 = math.degrees(math.acos(x)) / 15
        local = 12 - h0 if event == "sunrise" else 12 + h0
        lon = ((local - utc_h) * 15 + 540) % 360 - 180
        pts.append((lat, lon))
    return pts


@mcp.tool()
async def where_sun_is(event: str = "sunrise", limit: int = 5) -> list[dict]:
    """找世界上此刻正在日出（sunrise）或日落（sunset）的地方的摄像头。"""
    now = dt.datetime.now(dt.timezone.utc)
    pts = _sun_points(event, now)
    results = await asyncio.gather(
        *(search_nearby(lat, lon, radius_km=250, limit=3) for lat, lon in pts),
        return_exceptions=True,
    )
    found = []
    for cams in results:
        if isinstance(cams, Exception):
            continue
        found += [c for c in cams if c.get("status") == "active"]
    return found[:limit]


# ---------------- Movebank 动物追踪（官方 REST API，用你自己的 Movebank 账号） ----------------
# 文档：github.com/movebank/movebank-api-doc
# 账号从环境变量 MOVEBANK_USER_B64 / MOVEBANK_PASS_B64 读（base64，避开引号问题）。
# 需要接受条款的研究，不在代码里替用户接受，请用户去网页上用自己账号接受。

import csv
import io
import re

MB_BASE = "https://www.movebank.org/movebank/service/direct-read"
MB_SOURCE = "Movebank (movebank.org)，数据归各研究所有，使用遵守该研究的条款"


def _b64env(k):
    v = os.getenv(k)
    return base64.b64decode(v).decode() if v else None


MB_USER = _b64env("MOVEBANK_USER_B64")
MB_PASS = _b64env("MOVEBANK_PASS_B64")
_mb_cache: dict = {}
_mb_lock = asyncio.Lock()
_mb_last = 0.0


def _looks_like_csv(text):
    """正常返回的第一行是列名（全是小写字母下划线）；条款页、错误页不是。"""
    lines = text.lstrip().splitlines()
    return bool(lines) and re.fullmatch(r'"?[a-z_]+"?(,"?[a-z_]+"?)*', lines[0].strip()) is not None


async def _mb_get(params, ttl=1800):
    """带缓存和限速的请求，返回 CSV 行。出错时有旧缓存就用旧的。"""
    global _mb_last
    if not MB_USER or not MB_PASS:
        raise ValueError("服务器上没配置 Movebank 账号")
    key = tuple(sorted(params.items()))
    hit = _mb_cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    async with _mb_lock:
        hit = _mb_cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
        wait = 1.0 - (time.time() - _mb_last)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
                r = await c.get(MB_BASE, params=params, auth=(MB_USER, MB_PASS))
            _mb_last = time.time()
            if r.status_code == 401:
                raise ValueError("Movebank 账号或密码不对")
            r.raise_for_status()
            text = r.text
            if not _looks_like_csv(text):
                sid = params.get("study_id", "")
                raise ValueError(
                    f"研究 {sid} 需要先在 movebank.org 网页上用你的账号"
                    "接受数据使用条款，接受后再试")
            rows = list(csv.DictReader(io.StringIO(text)))
        except Exception:
            if hit:
                return hit[1]
            raise
        _mb_cache[key] = (time.time(), rows)
        return rows


def _mbts(s):
    if not s:
        return None
    s = s.strip().replace("T", " ").rstrip("Z")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            pass
    return None


def _mbiso(s):
    t = _mbts(s)
    return t.isoformat().replace("+00:00", "Z") if t else None


def _iso(t):
    return t.isoformat(timespec="minutes") if t else None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


async def _mb_points(study_id, individual_id, days):
    start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days))
    rows = await _mb_get({
        "entity_type": "event",
        "study_id": str(study_id),
        "individual_id": str(individual_id),
        "attributes": "timestamp,location_lat,location_long",
        "timestamp_start": start.strftime("%Y%m%d%H%M%S") + "000",
    }, ttl=1800)
    pts = []
    for r in rows:
        lat, lon = _num(r.get("location_lat")), _num(r.get("location_long"))
        t = _mbts(r.get("timestamp"))
        if lat is None or lon is None or t is None:
            continue
        pts.append({"time": t, "lat": lat, "lon": lon})
    pts.sort(key=lambda p: p["time"])
    return pts


@mcp.tool()
async def list_studies(days: int = 30, taxon: str | None = None,
                       limit: int = 30) -> list[dict]:
    """Movebank：列出你的账号能下载、且最近 N 天还有新定位的动物追踪研究。
    taxon 按物种名筛，比如 Ciconia（鹳）、Chelonia（海龟）、Carcharodon（大白鲨）。"""
    rows = await _mb_get({"entity_type": "study",
                          "i_have_download_access": "true"}, ttl=21600)
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    out = []
    for r in rows:
        if r.get("i_have_download_access", "true").lower() != "true":
            continue
        last = _mbts(r.get("timestamp_last_deployed_location"))
        if not last or last < since:
            continue
        tx = r.get("taxon_ids") or ""
        if taxon and taxon.lower() not in tx.lower():
            continue
        out.append({
            "study_id": r.get("id"),
            "name": r.get("name"),
            "taxon": tx,
            "last_location": last,
            "individuals": r.get("number_of_individuals"),
            "license": r.get("license_type"),
        })
    out.sort(key=lambda s: s["last_location"], reverse=True)
    for s in out:
        s["last_location"] = s["last_location"].isoformat().replace("+00:00", "Z")
    return out[:limit]


@mcp.tool()
async def list_animals(study_id: str, limit: int = 50) -> list[dict]:
    """Movebank：某个研究里的动物个体（名字、物种、性别、最后记录时间）。"""
    rows = await _mb_get({"entity_type": "individual",
                          "study_id": str(study_id)}, ttl=21600)
    out = [{
        "individual_id": r.get("id"),
        "name": r.get("nick_name") or r.get("local_identifier"),
        "local_identifier": r.get("local_identifier"),
        "taxon": r.get("taxon_canonical_name"),
        "sex": r.get("sex"),
        "last_seen": _mbiso(r.get("timestamp_end")),
    } for r in rows]
    out.sort(key=lambda a: a["last_seen"] or "", reverse=True)
    return out[:limit]


async def _animal_info(study_id, individual_id):
    try:
        for a in await list_animals(study_id, limit=100000):
            if str(a["individual_id"]) == str(individual_id):
                return {k: a[k] for k in ("name", "taxon", "sex")}
    except Exception:
        pass
    return {}


@mcp.tool()
async def animal_track(study_id: str, individual_id: str,
                       days: int = 30) -> dict:
    """Movebank：某只动物最近 N 天的定位点（按时间排序，最多 500 个，多了均匀抽样）。"""
    pts = await _mb_points(study_id, individual_id, days)
    if len(pts) > 500:
        step = len(pts) / 500
        pts = [pts[int(i * step)] for i in range(499)] + [pts[-1]]
    return {
        "study_id": study_id,
        "individual_id": individual_id,
        **await _animal_info(study_id, individual_id),
        "days": days,
        "count": len(pts),
        "points": [{"time": _iso(p["time"]), "lat": p["lat"], "lon": p["lon"]}
                   for p in pts],
        "source": MB_SOURCE,
    }


@mcp.tool()
async def animal_latest(study_id: str, individual_id: str) -> dict:
    """Movebank：某只动物最新一次定位（最近 60 天内）。"""
    pts = await _mb_points(study_id, individual_id, 60)
    last = pts[-1] if pts else None
    return {
        "study_id": study_id,
        "individual_id": individual_id,
        **await _animal_info(study_id, individual_id),
        "time": _iso(last["time"]) if last else None,
        "lat": last["lat"] if last else None,
        "lon": last["lon"] if last else None,
        "note": None if last else "最近 60 天没有定位",
        "source": MB_SOURCE,
    }


# ---------------- 天气（Open-Meteo 免费接口，不用钥匙） ----------------

OM_URL = "https://api.open-meteo.com/v1/forecast"
OM_CURRENT = ("temperature_2m,apparent_temperature,wind_speed_10m,"
              "wind_direction_10m,cloud_cover,precipitation,weather_code,is_day")
_DIRS = ["北", "东北偏北", "东北", "东北偏东", "东", "东南偏东", "东南", "东南偏南",
         "南", "西南偏南", "西南", "西南偏西", "西", "西北偏西", "西北", "西北偏北"]
_WMO = {
    0: "晴", 1: "大致晴", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨", 56: "冻毛毛雨", 57: "强冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "阵雨", 82: "强阵雨", 85: "阵雪", 86: "强阵雪",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
}
_om_cache: dict = {}


def _wind_dir(deg):
    if deg is None:
        return None
    return _DIRS[int((deg % 360) / 22.5 + 0.5) % 16]


@mcp.tool()
async def weather_at(lat: float, lon: float) -> dict:
    """某个经纬度此刻的天气：温度、体感、风速风向、云量、降水，和当地时间。
    数据来自 Open-Meteo，10 分钟内同一地点不重复请求。"""
    key = (round(lat, 2), round(lon, 2))
    hit = _om_cache.get(key)
    if hit and time.time() - hit[0] < 600:
        data = hit[1]
    else:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(OM_URL, params={
                "latitude": lat, "longitude": lon, "current": OM_CURRENT,
                "timezone": "auto", "wind_speed_unit": "kmh",
            })
            r.raise_for_status()
            data = r.json()
        _om_cache[key] = (time.time(), data)
    cur = data.get("current") or {}
    off = data.get("utc_offset_seconds") or 0
    now_local = (dt.datetime.now(dt.timezone.utc)
                 + dt.timedelta(seconds=off)).replace(tzinfo=None)
    wd = cur.get("wind_direction_10m")
    code = cur.get("weather_code")
    return {
        "lat": data.get("latitude", lat),
        "lon": data.get("longitude", lon),
        "local_time": now_local.isoformat(timespec="minutes"),
        "timezone": data.get("timezone"),
        "utc_offset_hours": off / 3600,
        "observed_at": cur.get("time"),
        "is_day": bool(cur.get("is_day")) if cur.get("is_day") is not None else None,
        "weather": _WMO.get(code, f"代码 {code}") if code is not None else None,
        "temperature_c": cur.get("temperature_2m"),
        "feels_like_c": cur.get("apparent_temperature"),
        "wind_speed_kmh": cur.get("wind_speed_10m"),
        "wind_direction_deg": wd,
        "wind_from": _wind_dir(wd),
        "cloud_cover_pct": cur.get("cloud_cover"),
        "precipitation_mm": cur.get("precipitation"),
        "source": "Open-Meteo (open-meteo.com)",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
