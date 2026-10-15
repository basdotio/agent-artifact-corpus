"""
TradingView MCP Server
======================
Servidor FastMCP que recibe alertas de TradingView via webhook HTTP
y las expone como herramientas MCP para Claude.

Arquitectura:
  TradingView Alert → POST /webhook → FastAPI receiver
                                        ↓
                                  SQLite storage
                                        ↓
                                  MCP Tools ← Claude

Autor: Daynier (adaptado por Claude)
"""

import json
import sqlite3
import hashlib
import hmac
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional, List, Any
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict

# ──────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────
DEFAULT_SECRET = "changeme_secret_2024"
WEBHOOK_SECRET = os.getenv("TV_WEBHOOK_SECRET", DEFAULT_SECRET)
# Solo para desarrollo local: permite arrancar sin secreto configurado.
ALLOW_INSECURE = os.getenv("TV_ALLOW_INSECURE", "0") == "1"
DB_PATH = Path(os.getenv("TV_DB_PATH", "./data/alerts/alerts.db"))
SERVER_HOST = os.getenv("TV_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("TV_PORT", "8000"))
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))

# IPs oficiales de TradingView (allowlist)
TRADINGVIEW_IPS = {
    "52.89.214.238",
    "34.212.75.30",
    "54.218.53.128",
    "52.32.178.7",
}

# ──────────────────────────────────────────────────────────────
# BASE DE DATOS SQLite
# ──────────────────────────────────────────────────────────────

def init_db():
    """Inicializa la base de datos SQLite con el esquema necesario."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at TEXT NOT NULL,
            ticker      TEXT,
            action      TEXT,
            price       REAL,
            close       REAL,
            high        REAL,
            low         REAL,
            volume      REAL,
            timeframe   TEXT,
            strategy    TEXT,
            message     TEXT,
            raw_payload TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ticker    ON alerts(ticker);
        """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_received  ON alerts(received_at);
        """)
    conn.commit()
    conn.close()


def insert_alert(payload: dict) -> int:
    """Guarda una alerta recibida en SQLite y retorna su ID."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("""
        INSERT INTO alerts
            (received_at, ticker, action, price, close, high, low, volume,
             timeframe, strategy, message, raw_payload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        payload.get("ticker"),
        payload.get("action"),
        payload.get("price"),
        payload.get("close"),
        payload.get("high"),
        payload.get("low"),
        payload.get("volume"),
        payload.get("timeframe"),
        payload.get("strategy"),
        payload.get("message"),
        json.dumps(payload),
    ))
    conn.commit()
    alert_id = cur.lastrowid
    conn.close()
    return alert_id


def query_alerts(
    ticker: str = None,
    action: str = None,
    strategy: str = None,
    limit: int = 50,
    offset: int = 0,
) -> List[dict]:
    """Consulta alertas con filtros opcionales."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conditions, params = [], []
    if ticker:
        conditions.append("UPPER(ticker) = UPPER(?)")
        params.append(ticker)
    if action:
        conditions.append("UPPER(action) = UPPER(?)")
        params.append(action)
    if strategy:
        conditions.append("strategy LIKE ?")
        params.append(f"%{strategy}%")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params += [limit, offset]

    rows = conn.execute(
        f"SELECT * FROM alerts {where} ORDER BY received_at DESC LIMIT ? OFFSET ?",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary_stats(ticker: str = None) -> dict:
    """Calcula estadísticas de alertas: total, buy/sell, última señal."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    filter_sql ="WHERE UPPER(ticker) = UPPER(?)" if ticker else ""
    params = [ticker] if ticker else []

    total = conn.execute(
        f"SELECT COUNT(*) FROM alerts {filter_sql}", params
    ).fetchone()[0]
    by_action = conn.execute(
        f"SELECT action, COUNT(*) as cnt FROM alerts {filter_sql} GROUP BY action", params
    ).fetchall()
    last = conn.execute(
        f"SELECT * FROM alerts {filter_sql} ORDER BY received_at DESC LIMIT 1", params
    ).fetchone()
    conn.close()

    return {
        "total_alerts": total,
        "by_action": {r[0]: r[1] for r in by_action},
        "last_alert": dict(last) if last else None,
    }


# ──────────────────────────────────────────────────────────────
# FASTAPI: WEBHOOK RECEIVER
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"✅ DB inicializada en {DB_PATH}")
    yield

webhook_app = FastAPI(
    title="TradingView Webhook Receiver",
    version="1.0.0",
    lifespan=lifespan,
)


def verify_secret(payload_bytes: bytes, secret_header: str) -> bool:
    """Verifica HMAC-SHA256 del payload contra el header x-tv-secret."""
    expected = hmac.new(
        WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, secret_header or "")


def is_authorized(raw: bytes, payload: dict, secret_header: Optional[str]) -> bool:
    """
    Autoriza la alerta por una de dos vías:
      1. Header x-tv-secret con HMAC-SHA256 del body (clientes propios).
      2. Campo "secret" dentro del JSON: TradingView no permite cabeceras
         personalizadas, así que el secreto viaja en el mensaje de la alerta.
    Falla en cerrado: sin secreto configurado se rechaza todo, salvo que
    TV_ALLOW_INSECURE=1 (solo desarrollo local).
    """
    if WEBHOOK_SECRET == DEFAULT_SECRET:
        return ALLOW_INSECURE
    if secret_header:
        return verify_secret(raw, secret_header)
    body_secret = payload.get("secret")
    if isinstance(body_secret, str):
        return hmac.compare_digest(body_secret.encode(), WEBHOOK_SECRET.encode())
    return False


@webhook_app.post("/webhook")
async def receive_alert(
    request: Request,
    x_tv_secret: Optional[str] = Header(default=None),
):
    """
    Endpoint que TradingView llama con cada alerta.
    Acepta JSON con los campos del Pine Script alert_message.
    """
    # ── Validar IP de origen (opcional, recomendado en producción)
    client_ip = request.client.host
    # Descomenta para producción:
    # if client_ip not in TRADINGVIEW_IPS:
    #     raise HTTPException(403, f"IP no autorizada: {client_ip}")

    raw = await request.body()

    # ── Parsear JSON
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            payload = {"message": str(payload)}
    except json.JSONDecodeError:
        # Si viene como texto plano, envuélvelo
        payload = {"message": raw.decode("utf-8", errors="replace")}

    # ── Autenticar (falla en cerrado)
    if not is_authorized(raw, payload, x_tv_secret):
        raise HTTPException(401, "Secreto inválido")

    # El secreto nunca se persiste en la base de datos
    payload.pop("secret", None)

    # ── Guardar en DB
    alert_id = insert_alert(payload)

    print(f"[{datetime.now().isoformat()}] ✅ Alerta #{alert_id} recibida "
          f"| ticker={payload.get('ticker')} action={payload.get('action')} "
          f"price={payload.get('price')} desde {client_ip}")

    return JSONResponse({"status": "ok", "alert_id": alert_id})


@webhook_app.get("/health")
async def health():
    return {"status": "ok", "db": str(DB_PATH), "alerts": query_alerts(limit=1)}


# ──────────────────────────────────────────────────────────────
# FASTMCP: HERRAMIENTAS MCP PARA CLAUDE
# ──────────────────────────────────────────────────────────────

mcp = FastMCP("tradingview_mcp")


# ── Modelos de input ──────────────────────────────────────────

class GetAlertsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: Optional[str] = Field(
        default=None,
        description="Filtrar por ticker. Ej: 'QQQ', 'SPY', 'AAPL'",
    )
    action: Optional[str] = Field(
        default=None,
        description="Filtrar por acción: 'buy', 'sell', 'close_long', 'close_short'",
    )
    strategy: Optional[str] = Field(
        default=None,
        description="Filtrar por nombre de estrategia (búsqueda parcial)",
    )
    limit: int = Field(
        default=20,
        description="Número máximo de alertas a retornar (1–200)",
        ge=1,
        le=200,
    )
    offset: int = Field(
        default=0,
        description="Desplazamiento para paginación",
        ge=0,
    )


class GetStatsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: Optional[str] = Field(
        default=None,
        description="Ticker para calcular estadísticas. Si es None, calcula sobre todos.",
    )


class AnalyzeSignalsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str = Field(
        description="Ticker a analizar. Ej: 'QQQ'",
        min_length=1,
        max_length=10,
    )
    last_n: int = Field(
        default=50,
        description="Cuántas alertas recientes analizar",
        ge=5,
        le=500,
    )


# ── Herramientas MCP ──────────────────────────────────────────

@mcp.tool(
    name="tv_get_alerts",
    annotations={
        "title": "Obtener Alertas de TradingView",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tv_get_alerts(params: GetAlertsInput) -> str:
    """
    Retorna las alertas de TradingView almacenadas, con filtros opcionales.

    Úsala para revisar señales recientes de una estrategia Pine Script,
    ver qué acciones (buy/sell) se han generado, o depurar alertas.

    Args:
        params (GetAlertsInput):
            - ticker: Filtrar por instrumento (QQQ, SPY, etc.)
            - action: buy | sell | close_long | close_short
            - strategy: Nombre parcial de la estrategia
            - limit: Máximo de resultados (default 20)
            - offset: Para paginación

    Returns:
        str: JSON con lista de alertas y metadata de paginación.
    """
    alerts = query_alerts(
        ticker=params.ticker,
        action=params.action,
        strategy=params.strategy,
        limit=params.limit,
        offset=params.offset,
    )
    return json.dumps({
        "count": len(alerts),
        "limit": params.limit,
        "offset": params.offset,
        "filters": {
            "ticker": params.ticker,
            "action": params.action,
            "strategy": params.strategy,
        },
        "alerts": alerts,
    }, indent=2, ensure_ascii=False)


@mcp.tool(
    name="tv_get_stats",
    annotations={
        "title": "Estadísticas de Alertas",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tv_get_stats(params: GetStatsInput) -> str:
    """
    Retorna estadísticas resumidas de las alertas recibidas.

    Útil para revisar rápidamente cuántas señales buy/sell ha generado
    una estrategia, cuál fue la última señal, y el balance general.

    Args:
        params (GetStatsInput):
            - ticker: Filtrar estadísticas por ticker. None = todos.

    Returns:
        str: JSON con total, desglose por acción, y última alerta.
    """
    stats = get_summary_stats(params.ticker)
    return json.dumps(stats, indent=2, ensure_ascii=False)


@mcp.tool(
    name="tv_analyze_signals",
    annotations={
        "title": "Analizar Calidad de Señales",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tv_analyze_signals(params: AnalyzeSignalsInput) -> str:
    """
    Analiza las últimas N alertas de un ticker y reporta métricas de calidad:
    frecuencia de señales, ratio buy/sell, precios promedio, gaps entre señales.

    Ideal para evaluar si una estrategia Pine Script está sobre-señalizando,
    tiene señales balanceadas, o presenta anomalías en los precios.

    Args:
        params (AnalyzeSignalsInput):
            - ticker: Instrumento a analizar (QQQ, SPY, etc.)
            - last_n: Cuántas alertas recientes analizar (default 50)

    Returns:
        str: JSON con métricas de calidad de señales.
    """
    alerts = query_alerts(ticker=params.ticker, limit=params.last_n)

    if not alerts:
        return json.dumps({
            "error": f"No hay alertas para ticker={params.ticker}",
            "suggestion": "Verifica que TradingView esté enviando alertas al webhook.",
        })

    buys  = [a for a in alerts if (a.get("action") or "").lower() == "buy"]
    sells = [a for a in alerts if (a.get("action") or "").lower() == "sell"]
    prices = [a["price"] for a in alerts if a.get("price") is not None]

    # Gap promedio entre señales (en segundos)
    timestamps = []
    for a in alerts:
        try:
            timestamps.append(datetime.fromisoformat(a["received_at"]))
        except Exception:
            pass

    gaps = []
    for i in range(len(timestamps) - 1):
        diff = abs((timestamps[i] - timestamps[i + 1]).total_seconds())
        gaps.append(diff)

    analysis = {
        "ticker": params.ticker.upper(),
        "alerts_analyzed": len(alerts),
        "period": {
            "first": alerts[-1]["received_at"] if alerts else None,
            "last":  alerts[0]["received_at"] if alerts else None,
        },
        "signal_counts": {
            "buy":   len(buys),
            "sell":  len(sells),
            "other": len(alerts) - len(buys) - len(sells),
        },
        "buy_sell_ratio": round(len(buys) / len(sells), 2) if sells else None,
        "price_stats": {
            "min":  round(min(prices), 4) if prices else None,
            "max":  round(max(prices), 4) if prices else None,
            "avg":  round(sum(prices) / len(prices), 4) if prices else None,
        },
        "avg_gap_between_signals_seconds": round(sum(gaps) / len(gaps), 1) if gaps else None,
        "strategies_seen": list({a.get("strategy") for a in alerts if a.get("strategy")}),
        "timeframes_seen": list({a.get("timeframe") for a in alerts if a.get("timeframe")}),
        "diagnosis": [],
    }

    # Diagnóstico automático
    if len(alerts) > 40:
        analysis["diagnosis"].append(
            "⚠️ Alta frecuencia de señales – posible sobre-optimización o ruido."
        )
    if analysis["buy_sell_ratio"] and (analysis["buy_sell_ratio"] > 3 or analysis["buy_sell_ratio"] < 0.33):
        analysis["diagnosis"].append(
            "⚠️ Ratio buy/sell muy desbalanceado – revisa la lógica de entrada/salida."
        )
    if not analysis["diagnosis"]:
        analysis["diagnosis"].append("✅ Señales dentro de rangos normales.")

    return json.dumps(analysis, indent=2, ensure_ascii=False)


# ──────────────────────────────────────────────────────────────
# ENTRYPOINTS
# ──────────────────────────────────────────────────────────────

def run_webhook():
    """Arranca el servidor webhook FastAPI."""
    if WEBHOOK_SECRET == DEFAULT_SECRET and not ALLOW_INSECURE:
        raise SystemExit(
            "TV_WEBHOOK_SECRET no configurado. Define un secreto en .env "
            "o usa TV_ALLOW_INSECURE=1 solo para pruebas locales."
        )
    uvicorn.run(webhook_app, host=SERVER_HOST, port=SERVER_PORT)


def run_mcp():
    """Arranca el servidor MCP (stdio o SSE según entorno)."""
    mcp.run()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        run_mcp()
    else:
        run_webhook()
