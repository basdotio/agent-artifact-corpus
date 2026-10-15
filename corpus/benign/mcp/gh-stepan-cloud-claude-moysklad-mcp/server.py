"""
МойСклад MCP-сервер для Claude Code.

Даёт Claude инструменты для работы с МойСклад через JSON API 1.2:
товары и модификации (ассортимент), остатки, контрагенты, заказы покупателей
и любые документы — чтение, создание, изменение, плюс «сырой» запрос к API.

Авторизация — Bearer-токен. Он берётся из переменной окружения MOYSKLAD_TOKEN
или из файла moysklad_token.txt рядом с этим файлом (файл в .gitignore).
Токен читается при каждом вызове, поэтому после того как его положили,
перезапуск Claude Code не нужен.

ВАЖНО: все денежные суммы в API МойСклад — в КОПЕЙКАХ (×100).
"""

from __future__ import annotations

import functools
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.moysklad.ru/api/remap/1.2/"
UI_URL = "https://online.moysklad.ru/app/#"
REPO_URL = "https://github.com/stepan-cloud/claude-moysklad-mcp"
USER_AGENT = f"claude-moysklad-mcp/1.0 (+{REPO_URL})"
TOKEN_FILE = Path(__file__).resolve().parent / "moysklad_token.txt"

PAGE_LIMIT = 1000  # максимум записей на страницу в API
PAGE_LIMIT_EXPAND = 100  # при использовании expand API отдаёт не больше 100
MAX_ROWS_CAP = 10000  # защита от гигантских ответов в контекст Claude
MAX_RETRIES = 5

logging.getLogger("httpx").setLevel(logging.WARNING)  # без построчного лога запросов

mcp = FastMCP(
    "moysklad",
    instructions=(
        "Инструменты для работы с МойСклад (JSON API 1.2): товары и модификации, "
        "остатки, контрагенты, заказы покупателей и другие документы. "
        "ВСЕ ДЕНЕЖНЫЕ СУММЫ В API — В КОПЕЙКАХ (цена 150 ₽ = 15000). Исключение — "
        "параметр price в create_customer_order / add_positions: там рубли. "
        "Чтобы перенести данные в Google Таблицу, передавай параметр columns "
        "(например ['name','code','stock','salePrices.0.value:rub']) — ответ придёт "
        "как header + rows (2D-массив), готовый для write_range / append_rows; "
        "суффикс ':rub' переводит копейки в рубли. Ссылки на объекты в "
        "create_entity / update_entity можно писать коротко: {'meta': 'counterparty/<id>'}. "
        "Сначала вызови get_context, чтобы узнать ID юрлиц, складов и типов цен. "
        "ПЕРЕД ЛЮБЫМ СОЗДАНИЕМ, ИЗМЕНЕНИЕМ, ПРОВЕДЕНИЕМ ИЛИ УДАЛЕНИЕМ покажи "
        "пользователю, что именно будет сделано, и дождись его явного подтверждения."
    ),
)


# --- Ошибки -----------------------------------------------------------------


class AuthError(Exception):
    """Нет токена или он не принят сервером."""


class ApiError(Exception):
    """Ошибка, которую вернул API МойСклад."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


# --- Токен и HTTP-клиент ----------------------------------------------------


def _read_token_file(path: Path = TOKEN_FILE) -> str:
    """Первая непустая строка файла, не начинающаяся с '#' (там подсказки)."""
    if not path.exists():
        return ""
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            return s
    return ""


_ASSIGN_RE = re.compile(r"^(?:export\s+|set\s+)?[A-Za-z_][A-Za-z0-9_]*\s*[=:]\s*")


def _clean_token(token: str) -> str:
    """Убирает то, что часто прилипает при копировании: 'MOYSKLAD_TOKEN=',
    'Authorization: Bearer ', кавычки."""
    token = token.strip()
    if _ASSIGN_RE.match(token):
        token = _ASSIGN_RE.sub("", token, count=1)
    token = token.strip().strip("\"'").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def _token() -> str:
    token = _clean_token(os.environ.get("MOYSKLAD_TOKEN", "") or _read_token_file())
    if not token:
        raise AuthError(
            "Токен МойСклад не найден. Запусти authorize.bat (или "
            "`python authorize.py`) в папке коннектора и вставь токен, либо положи "
            f"его в файл {TOKEN_FILE.name} рядом с server.py. Токен создаётся в "
            "МойСклад: Настройки → Токены. НЕ вставляй токен в чат."
        )
    return token


_client: httpx.Client | None = None


def _http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(90.0, connect=15.0),
            headers={
                "Accept": "application/json;charset=utf-8",
                "Accept-Encoding": "gzip",
                "User-Agent": USER_AGENT,
            },
        )
    return _client


def _url(path: str) -> str:
    """Относительный путь ('entity/product') или полная ссылка на API -> URL.

    Полные ссылки принимаются только на api.moysklad.ru — токен никогда не
    уходит на другие адреса.
    """
    path = path.strip()
    if path.startswith(("http://", "https://")):
        if not path.startswith(BASE_URL):
            raise ValueError(f"Разрешены только ссылки вида {BASE_URL}...")
        return path
    path = path.lstrip("/")
    if path.startswith("api/remap/1.2/"):
        path = path[len("api/remap/1.2/") :]
    return BASE_URL + path


def _retry_delay(resp: httpx.Response, attempt: int) -> float:
    ms = resp.headers.get("X-Lognex-Retry-After")
    if ms and ms.strip().isdigit():
        return max(0.2, int(ms) / 1000)
    sec = resp.headers.get("Retry-After")
    if sec:
        try:
            return max(0.2, float(sec))
        except ValueError:
            pass
    return 1.0 * (attempt + 1)


def _error_text(resp: httpx.Response) -> str:
    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        return resp.text[:500] or resp.reason_phrase
    errors = data.get("errors") if isinstance(data, dict) else None
    if isinstance(data, list):  # массовые операции: список ответов
        errors = [e for item in data if isinstance(item, dict) for e in item.get("errors", [])]
    if not errors:
        return json.dumps(data, ensure_ascii=False)[:500]
    parts = []
    for e in errors:
        msg = e.get("error", "")
        if e.get("code"):
            msg = f"{msg} (код {e['code']})"
        if e.get("parameter"):
            msg += f", параметр: {e['parameter']}"
        if e.get("moreInfo"):
            msg += f", подробнее: {e['moreInfo']}"
        parts.append(msg)
    return "; ".join(parts)


def _request(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    body: Any = None,
) -> Any:
    """Запрос к API с повтором при 429 (лимиты) и сбоях сервера."""
    method = method.upper()
    url = _url(path)
    headers = {"Authorization": f"Bearer {_token()}"}
    content = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        content = json.dumps(body, ensure_ascii=False).encode("utf-8")
    params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    idempotent = method in ("GET", "HEAD")

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = _http().request(
                method, url, params=params, content=content, headers=headers
            )
        except httpx.TransportError as exc:
            if idempotent and attempt < MAX_RETRIES:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise ApiError(0, f"Сетевая ошибка: {type(exc).__name__}: {exc}") from exc

        if resp.status_code == 429 and attempt < MAX_RETRIES:
            # Превышен лимит запросов — запрос не выполнен, повтор безопасен.
            time.sleep(_retry_delay(resp, attempt))
            continue
        if resp.status_code in (500, 502, 503, 504) and idempotent and attempt < MAX_RETRIES:
            time.sleep(1.0 * (attempt + 1))
            continue
        break

    if resp.status_code == 401:
        raise AuthError(
            f"Токен не принят (401): {_error_text(resp)}. Проверь токен — "
            "перезапусти authorize.bat и вставь действующий."
        )
    if resp.status_code >= 400:
        hint = ""
        if resp.status_code == 403:
            hint = " (недостаточно прав у пользователя, которому выдан токен)"
        elif resp.status_code == 429:
            hint = " (лимит запросов — повтори чуть позже)"
        raise ApiError(resp.status_code, f"[{resp.status_code}]{hint} {_error_text(resp)}")
    if not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError:
        return {"content": resp.text}


# --- Ссылки (meta) ----------------------------------------------------------

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
# Нестандартные пути и типы некоторых объектов
_SPECIAL_PATHS = {"pricetype": "context/companysettings/pricetype"}
_TYPE_BY_SEGMENT = {"states": "state", "attributes": "attributemetadata"}


def _is_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value.strip()))


def _id_from_href(href: str) -> str:
    return href.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]


def _meta(ref: str) -> dict:
    """'counterparty/<id>' / 'entity/store/<id>' / полная ссылка -> полный meta."""
    ref = ref.strip()
    if ref.startswith(("http://", "https://")):
        href = _url(ref)
    else:
        rel = ref.lstrip("/")
        first = rel.split("/", 1)[0]
        if first in _SPECIAL_PATHS:
            rel = _SPECIAL_PATHS[first] + rel[len(first) :]
        elif first not in ("entity", "context", "report"):
            rel = "entity/" + rel
        href = BASE_URL + rel
    parts = href[len(BASE_URL) :].split("?", 1)[0].strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Не понимаю ссылку '{ref}'. Ожидается вид 'тип/<id>'.")
    seg = parts[-2]
    return {
        "href": href,
        "type": _TYPE_BY_SEGMENT.get(seg, seg),
        "mediaType": "application/json",
    }


def _expand_refs(data: Any) -> Any:
    """Разворачивает короткие ссылки {'meta': 'тип/<id>'} в полный meta."""
    if isinstance(data, list):
        return [_expand_refs(x) for x in data]
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            if k == "meta" and isinstance(v, str):
                out[k] = _meta(v)
            else:
                out[k] = _expand_refs(v)
        return out
    return data


# --- Компактный вывод и таблицы ---------------------------------------------


def _compact(obj: Any) -> Any:
    """Убирает громоздкие meta/accountId, сворачивает ссылки до {type, id}."""
    if isinstance(obj, list):
        return [_compact(x) for x in obj]
    if not isinstance(obj, dict):
        return obj
    meta = obj.get("meta")
    if isinstance(meta, dict) and set(obj) == {"meta"}:
        if "size" in meta and "limit" in meta:  # вложенная коллекция (позиции и т.п.)
            return {"size": meta["size"]}
        if meta.get("href"):
            return {"type": meta.get("type"), "id": _id_from_href(meta["href"])}
    out: dict[str, Any] = {}
    if isinstance(meta, dict) and meta.get("href"):
        if "type" not in obj and meta.get("type"):
            out["type"] = meta["type"]
        ref_id = _id_from_href(meta["href"])
        if "id" not in obj and _is_uuid(ref_id):
            out["id"] = ref_id
    for k, v in obj.items():
        if k in ("meta", "accountId"):
            continue
        out[k] = _compact(v)
    return out


def _pick(obj: Any, path: str) -> Any:
    """Значение по пути 'a.b.0.c'. В списках можно выбирать элемент по name
    (например 'salePrices.Цена продажи.value'). 'attr:Имя' — доп. поле по имени."""
    if path.startswith("attr:"):
        name = path[5:]
        for a in obj.get("attributes", []) if isinstance(obj, dict) else []:
            if a.get("name") == name:
                return a.get("value")
        return None
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            if part.lstrip("-").isdigit():
                i = int(part)
                cur = cur[i] if -len(cur) <= i < len(cur) else None
            else:
                cur = next(
                    (
                        x
                        for x in cur
                        if isinstance(x, dict)
                        and (
                            x.get("name") == part
                            or (x.get("priceType") or {}).get("name") == part
                        )
                    ),
                    None,
                )
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
        if cur is None:
            return None
    return cur


def _cell(value: Any, rub: bool) -> Any:
    if rub and isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(value / 100, 2)
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("name", "value", "id"):
            if key in value:
                return value[key]
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return value


def _to_table(rows: list[dict], columns: list[str]) -> dict:
    specs = []
    for col in columns:
        rub = col.endswith(":rub")
        specs.append((col[:-4] if rub else col, rub))
    return {
        "header": list(columns),
        "rows": [[_cell(_pick(r, p), rub) for p, rub in specs] for r in rows],
    }


def _format_rows(
    rows: list[dict],
    total: int | None,
    offset: int,
    columns: list[str] | None,
    raw: bool,
    extra: dict | None = None,
) -> dict:
    result: dict[str, Any] = {"total": total, "returned": len(rows), "offset": offset}
    if total is not None and offset + len(rows) < total:
        result["next_offset"] = offset + len(rows)
    if extra:
        result.update(extra)
    data = rows if raw else _compact(rows)
    if columns:
        result.update(_to_table(data, columns))
    else:
        result["rows"] = data
    return result


# --- Пагинация --------------------------------------------------------------


def _fetch_rows(
    path: str,
    params: dict[str, Any] | None = None,
    max_rows: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int | None]:
    """Докачивает страницы (limit/offset), пока не наберёт max_rows."""
    params = dict(params or {})
    max_rows = max(1, min(int(max_rows), MAX_ROWS_CAP))
    page = PAGE_LIMIT_EXPAND if params.get("expand") else PAGE_LIMIT
    rows: list[dict] = []
    total: int | None = None
    cur = max(0, int(offset))
    while len(rows) < max_rows:
        lim = min(page, max_rows - len(rows))
        data = _request("GET", path, {**params, "limit": lim, "offset": cur})
        if isinstance(data, list):  # некоторые эндпоинты отдают просто массив
            rows.extend(data[: max_rows - len(rows)])
            total = len(data)
            break
        chunk = data.get("rows", [])
        size = (data.get("meta") or {}).get("size")
        if size is not None:
            total = size
        rows.extend(chunk)
        cur += len(chunk)
        if len(chunk) < lim or (total is not None and cur >= total):
            break
    return rows, total


def _join_filter(*parts: str) -> str:
    return ";".join(p.strip().strip(";") for p in parts if p and p.strip())


# --- Поиск объектов по имени / коду / ID ------------------------------------


def _candidates(rows: list[dict]) -> str:
    return "; ".join(
        f"{r.get('name')} (id {r.get('id')}"
        + (f", код {r['code']}" if r.get("code") else "")
        + (f", артикул {r['article']}" if r.get("article") else "")
        + ")"
        for r in rows[:10]
    )


def _try_rows(path: str, params: dict) -> list[dict]:
    try:
        return _request("GET", path, {**params, "limit": 11}).get("rows", [])
    except ApiError as exc:
        if exc.status == 400:  # фильтр не поддерживается этой сущностью
            return []
        raise


def _resolve(entity: str, value: str) -> dict:
    """Находит объект по ID, ссылке, точному имени (или ИНН у контрагента)."""
    value = str(value).strip()
    if value.startswith("http") or _is_uuid(value):
        path = value if value.startswith("http") else f"entity/{entity}/{value}"
        return _request("GET", path)
    attempts = [{"filter": f"name={value}"}]
    if entity in ("counterparty", "organization") and value.isdigit():
        attempts.insert(0, {"filter": f"inn={value}"})
    if entity in ("store", "counterparty"):
        attempts.append({"filter": f"code={value}"})
    attempts.append({"search": value})
    for params in attempts:
        rows = _try_rows(f"entity/{entity}", params)
        if len(rows) == 1:
            return rows[0]
        if len(rows) > 1:
            raise ValueError(
                f"'{value}' ({entity}) неоднозначно — нашлось несколько: "
                f"{_candidates(rows)}. Укажи ID."
            )
    raise ValueError(f"Не найден объект {entity} '{value}'.")


def _resolve_assortment(value: str) -> dict:
    """Товар/модификация/услуга/комплект по ID, коду, артикулу, штрихкоду или имени."""
    value = str(value).strip()
    if _is_uuid(value):
        for t in ("product", "variant", "service", "bundle"):
            try:
                return _request("GET", f"entity/{t}/{value}")
            except ApiError as exc:
                if exc.status != 404:
                    raise
        raise ValueError(f"Товар с ID {value} не найден.")
    if value.startswith("http"):
        return _request("GET", value)
    for field in ("code", "article", "barcode", "name"):
        rows = _try_rows("entity/assortment", {"filter": f"{field}={value}"})
        if len(rows) == 1:
            return rows[0]
        if len(rows) > 1:
            raise ValueError(
                f"'{value}' неоднозначно (совпадение по {field}): "
                f"{_candidates(rows)}. Укажи ID."
            )
    rows = _try_rows("entity/assortment", {"filter": f"search={value}"})
    if len(rows) == 1:
        return rows[0]
    if rows:
        raise ValueError(
            f"По '{value}' нашлось несколько товаров: {_candidates(rows)}. Укажи ID или код."
        )
    raise ValueError(f"Товар '{value}' не найден.")


def _ref(obj: dict) -> dict:
    return {"meta": obj["meta"]}


_BUY_DOCS = {"supply", "purchaseorder", "invoicein", "purchasereturn"}


def _build_positions(positions: list[dict], doc_type: str) -> list[dict]:
    """Упрощённые позиции -> формат API. Цена в рублях -> копейки."""
    if not positions:
        raise ValueError("Нужна хотя бы одна позиция.")
    out = []
    for i, p in enumerate(positions, 1):
        ident = p.get("product") or p.get("assortment") or p.get("id") or p.get("code")
        if not ident:
            raise ValueError(f"Позиция {i}: укажи 'product' (код, артикул, имя или ID).")
        item = _resolve_assortment(str(ident))
        qty = p.get("quantity", 1)
        if p.get("price") is not None:
            price = round(float(p["price"]) * 100)
        elif doc_type in _BUY_DOCS:
            price = (item.get("buyPrice") or {}).get("value", 0)
        else:
            prices = item.get("salePrices") or []
            price = prices[0].get("value", 0) if prices else 0
        pos: dict[str, Any] = {
            "quantity": float(qty),
            "price": price,
            "assortment": _ref(item),
        }
        for key in ("discount", "vat", "reserve"):
            if p.get(key) is not None:
                pos[key] = p[key]
        out.append(pos)
    return out


def _doc_summary(doc: dict, entity: str) -> dict:
    return {
        "id": doc.get("id"),
        "name": doc.get("name"),
        "moment": doc.get("moment"),
        "sum_rub": round((doc.get("sum") or 0) / 100, 2),
        "applicable": doc.get("applicable"),
        "url": f"{UI_URL}{entity}/edit?id={doc.get('id')}",
    }


def _entity_path(entity: str) -> str:
    entity = entity.strip().strip("/")
    if entity.startswith("entity/"):
        entity = entity[len("entity/") :]
    if not entity:
        raise ValueError("Не указан тип сущности (например 'product', 'counterparty').")
    return f"entity/{entity}"


# --- Обёртка инструментов ---------------------------------------------------


def _safe(fn):
    """Понятные ошибки вместо стектрейсов; результат — JSON-строка."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False)
        except AuthError as exc:
            return f"ОШИБКА АВТОРИЗАЦИИ: {exc}"
        except ApiError as exc:
            return f"ОШИБКА API МойСклад: {exc}"
        except ValueError as exc:
            return f"ОШИБКА: {exc}"
        except Exception as exc:  # noqa: BLE001
            return f"ОШИБКА: {type(exc).__name__}: {exc}"

    return wrapper


# --- Инструменты: чтение ----------------------------------------------------


@mcp.tool()
@_safe
def ping() -> str:
    """Проверка связи и токена: кто я в МойСклад. Безопасное чтение."""
    emp = _request("GET", "context/employee")
    return (
        f"Связь с МойСклад есть. Пользователь токена: {emp.get('name') or emp.get('fullName')}"
        + (f" ({emp['email']})" if emp.get("email") else "")
    )


@mcp.tool()
@_safe
def get_context() -> dict:
    """Справка по аккаунту: текущий сотрудник, юрлица (organization), склады (store)
    и типы цен. Вызови перед созданием документов, чтобы знать их ID и имена."""
    emp = _request("GET", "context/employee")
    orgs, _ = _fetch_rows("entity/organization", max_rows=100)
    stores, _ = _fetch_rows("entity/store", max_rows=200)
    price_types = _request("GET", "context/companysettings/pricetype")
    return {
        "employee": {"id": emp.get("id"), "name": emp.get("name"), "email": emp.get("email")},
        "organizations": [
            {"id": o.get("id"), "name": o.get("name"), "inn": o.get("inn"), "archived": o.get("archived")}
            for o in orgs
        ],
        "stores": [
            {"id": s.get("id"), "name": s.get("name"), "archived": s.get("archived")}
            for s in stores
        ],
        "price_types": [
            {"id": p.get("id"), "name": p.get("name")}
            for p in (price_types if isinstance(price_types, list) else [])
        ],
    }


@mcp.tool()
@_safe
def search_assortment(
    search: str = "",
    filter: str = "",
    store: str = "",
    stock_mode: str = "",
    max_rows: int = 20,
    offset: int = 0,
    columns: list[str] | None = None,
    raw: bool = False,
) -> dict:
    """Поиск по ассортименту: товары, модификации, услуги, комплекты (с остатками).

    search      — строка поиска (имя, код, артикул, штрихкод). Пусто = всё.
    filter      — фильтр API, напр. 'archived=false;type=product' или 'code=123'.
    store       — склад (имя или ID): остатки только по нему.
    stock_mode  — all | positiveOnly | negativeOnly | empty | nonEmpty | underMinimum.
    max_rows    — сколько вернуть (по умолчанию 20, страницы по 1000 качаются сами).
    offset      — смещение для следующей порции (next_offset из прошлого ответа).
    columns     — вернуть таблицей: напр. ['type','name','code','article','stock',
                  'salePrices.0.value:rub']. ':rub' — копейки в рубли.
    raw         — вернуть ответ API без упрощения.
    Поле 'type' в результате: product / variant / service / bundle.
    Цены (salePrices[].value, buyPrice.value) — в копейках.
    """
    # У entity/assortment поиск работает только внутри filter (search=...)
    parts = [filter, f"search={search}" if search else ""]
    if store:
        parts.append(f"stockStore={_resolve('store', store)['meta']['href']}")
    if stock_mode:
        parts.append(f"stockMode={stock_mode}")
    params = {"filter": _join_filter(*parts)}
    rows, total = _fetch_rows("entity/assortment", params, max_rows, offset)
    return _format_rows(rows, total, offset, columns, raw)


@mcp.tool()
@_safe
def get_stock(
    store: str = "",
    search: str = "",
    stock_mode: str = "",
    per_store: bool = False,
    group_by: str = "",
    filter: str = "",
    max_rows: int = 100,
    offset: int = 0,
    columns: list[str] | None = None,
    raw: bool = False,
) -> dict:
    """Остатки товаров (отчёт report/stock/all или report/stock/bystore).

    store       — склад (имя или ID). Пусто = по всем складам суммарно.
    search      — поиск по имени / коду / артикулу. Ищет по НАЧАЛУ слова:
                  'бензогенератора' найдёт, 'генератор' внутри слова — нет.
    stock_mode  — all | positiveOnly | negativeOnly | empty | nonEmpty | underMinimum
                  (по умолчанию API: nonEmpty).
    per_store   — true = разбивка по каждому складу (поле stockByStore).
    group_by    — product | variant | consignment (только для общего отчёта).
    filter      — доп. фильтр API, напр. 'productFolder=<href>'.
    columns     — таблицей, напр. ['name','code','article','stock','reserve',
                  'quantity','salePrice:rub']. stock — остаток, reserve — резерв,
                  quantity — доступно. price/salePrice — в копейках (':rub' -> рубли).
    """
    parts = [filter]
    if store:
        parts.append(f"store={_resolve('store', store)['meta']['href']}")
    if search:
        parts.append(f"search={search}")
    if stock_mode:
        parts.append(f"stockMode={stock_mode}")
    path = "report/stock/bystore" if per_store else "report/stock/all"
    params: dict[str, Any] = {"filter": _join_filter(*parts)}
    if group_by and not per_store:
        params["groupBy"] = group_by
    rows, total = _fetch_rows(path, params, max_rows, offset)
    if per_store:
        _add_names(rows)
    return _format_rows(rows, total, offset, columns, raw)


def _add_names(rows: list[dict]) -> None:
    """В отчёте по складам нет имён товаров — подтягиваем имя/код/артикул
    из ассортимента пачками по 100 ID."""
    ids = [_id_from_href(r["meta"]["href"]) for r in rows if (r.get("meta") or {}).get("href")]
    info: dict[str, dict] = {}
    for i in range(0, len(ids), 100):
        batch = ids[i : i + 100]
        data = _request(
            "GET",
            "entity/assortment",
            {"filter": ";".join(f"id={x}" for x in batch), "limit": 100},
        )
        for a in data.get("rows", []):
            info[a.get("id")] = a
    for r in rows:
        a = info.get(_id_from_href((r.get("meta") or {}).get("href", "")))
        if a:
            for key in ("name", "code", "article"):
                if a.get(key) is not None:
                    r.setdefault(key, a[key])


@mcp.tool()
@_safe
def list_entities(
    entity: str,
    search: str = "",
    filter: str = "",
    order: str = "",
    expand: str = "",
    max_rows: int = 50,
    offset: int = 0,
    columns: list[str] | None = None,
    raw: bool = False,
) -> dict:
    """Список объектов любого типа.

    entity  — product, variant, service, bundle, productfolder, counterparty,
              customerorder, demand, supply, purchaseorder, invoiceout, invoicein,
              paymentin, paymentout, cashin, cashout, move, enter, loss, inventory,
              salesreturn, purchasereturn, retaildemand, store, organization,
              employee, currency, uom, … (как в URL API: entity/<entity>).
    search  — контекстный поиск.
    filter  — фильтр API: 'name=Иван;archived=false', 'moment>=2026-09-01 00:00:00',
              ссылки — полным href: 'agent=https://api.moysklad.ru/api/remap/1.2/entity/counterparty/<id>'.
    order   — сортировка, напр. 'moment,desc' или 'name'.
    expand  — раскрыть связанные объекты, напр. 'agent,state' (тогда страницы по 100).
    columns — вернуть таблицей, напр. ['name','moment','agent.name','sum:rub','state.name'].
    Суммы (sum, price, value) — в копейках.
    """
    params = {"search": search, "filter": filter, "order": order, "expand": expand}
    rows, total = _fetch_rows(_entity_path(entity), params, max_rows, offset)
    return _format_rows(rows, total, offset, columns, raw)


@mcp.tool()
@_safe
def get_entity(entity: str, id: str, expand: str = "", raw: bool = False) -> dict:
    """Один объект по ID. entity — тип (product, counterparty, customerorder, …).
    expand — раскрыть связанные объекты, напр. 'agent,organization,state,positions.assortment'.
    """
    data = _request("GET", f"{_entity_path(entity)}/{id.strip()}", {"expand": expand})
    return data if raw else _compact(data)


@mcp.tool()
@_safe
def get_positions(
    entity: str,
    id: str,
    max_rows: int = 1000,
    columns: list[str] | None = None,
    raw: bool = False,
) -> dict:
    """Строки (позиции) документа с раскрытым товаром.

    entity  — тип документа (customerorder, demand, supply, move, …).
    columns — таблицей, напр. ['assortment.name','assortment.code','quantity',
              'price:rub','discount','reserve','shipped'].
    price — в копейках, discount — в процентах.
    """
    path = f"{_entity_path(entity)}/{id.strip()}/positions"
    rows, total = _fetch_rows(path, {"expand": "assortment"}, max_rows, 0)
    return _format_rows(rows, total, 0, columns, raw)


# --- Инструменты: запись ----------------------------------------------------


@mcp.tool()
@_safe
def create_customer_order(
    agent: str,
    positions: list[dict[str, Any]],
    organization: str = "",
    store: str = "",
    description: str = "",
    moment: str = "",
    name: str = "",
    applicable: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> dict:
    """Создать заказ покупателя. ПЕРЕД ВЫЗОВОМ ПОДТВЕРДИ С ПОЛЬЗОВАТЕЛЕМ.

    agent        — контрагент: имя, ИНН или ID.
    positions    — [{"product": "<код/артикул/штрихкод/имя/ID>", "quantity": 2,
                    "price": 150.50, "discount": 5}]. price — В РУБЛЯХ, если не
                    указан — берётся первая цена продажи товара. discount — %.
    organization — юрлицо (имя/ИНН/ID). Пусто = единственное юрлицо аккаунта.
    store        — склад (имя/ID), необязательно.
    moment       — дата 'YYYY-MM-DD HH:MM:SS', пусто = сейчас.
    applicable   — провести (true) / черновик (false); пусто = по умолчанию API.
    extra        — любые доп. поля API (короткие ссылки {'meta':'тип/<id>'} можно).
    """
    body: dict[str, Any] = {"agent": _ref(_resolve("counterparty", agent))}
    if organization:
        body["organization"] = _ref(_resolve("organization", organization))
    else:
        orgs = _request("GET", "entity/organization", {"filter": "archived=false", "limit": 10}).get("rows", [])
        if len(orgs) != 1:
            raise ValueError(
                "В аккаунте несколько юрлиц — укажи organization: " + _candidates(orgs)
            )
        body["organization"] = _ref(orgs[0])
    if store:
        body["store"] = _ref(_resolve("store", store))
    for key, val in (("description", description), ("moment", moment), ("name", name)):
        if val:
            body[key] = val
    if applicable is not None:
        body["applicable"] = applicable
    if extra:
        body.update(_expand_refs(extra))
    body["positions"] = _build_positions(positions, "customerorder")
    doc = _request("POST", "entity/customerorder", body=body)
    return {"created": _doc_summary(doc, "customerorder")}


@mcp.tool()
@_safe
def add_positions(entity: str, id: str, positions: list[dict[str, Any]]) -> dict:
    """Добавить строки в документ. ПЕРЕД ВЫЗОВОМ ПОДТВЕРДИ С ПОЛЬЗОВАТЕЛЕМ.

    entity    — тип документа (customerorder, demand, supply, move, …).
    positions — [{"product": "<код/артикул/имя/ID>", "quantity": 1, "price": 99.90,
                 "discount": 0}]. price — В РУБЛЯХ; не указан — цена продажи
                 (для закупочных документов — закупочная цена).
    Позиции в «сыром» формате API можно отправить через api_request.
    """
    doc_type = _entity_path(entity).split("/", 1)[1]
    body = _build_positions(positions, doc_type)
    res = _request("POST", f"{_entity_path(entity)}/{id.strip()}/positions", body=body)
    doc = _request("GET", f"{_entity_path(entity)}/{id.strip()}")
    return {"added": len(res) if isinstance(res, list) else 1, "document": _doc_summary(doc, doc_type)}


@mcp.tool()
@_safe
def create_entity(entity: str, data: dict[str, Any] | list[dict[str, Any]], raw: bool = False) -> dict:
    """Создать объект/документ (POST). ПЕРЕД ВЫЗОВОМ ПОДТВЕРДИ С ПОЛЬЗОВАТЕЛЕМ.

    entity — тип: counterparty, product, demand, supply, paymentin, move, …
    data   — тело в формате API; список — массовое создание (до 1000 шт.).
             Ссылки можно коротко: {"agent": {"meta": "counterparty/<id>"}},
             {"assortment": {"meta": "product/<id>"}}, {"meta": "pricetype/<id>"}.
             Суммы и цены — В КОПЕЙКАХ.
    Совет: для отгрузки по заказу сначала получи шаблон через
    api_request PUT 'entity/demand/new' с телом {"customerOrder": {"meta": "customerorder/<id>"}}.
    """
    res = _request("POST", _entity_path(entity), body=_expand_refs(data))
    return res if raw else _compact(res)


@mcp.tool()
@_safe
def update_entity(entity: str, id: str, data: dict[str, Any], raw: bool = False) -> dict:
    """Изменить объект/документ (PUT, передаются только меняемые поля).
    ПЕРЕД ВЫЗОВОМ ПОДТВЕРДИ С ПОЛЬЗОВАТЕЛЕМ.

    Примеры data: {"description": "..."}, {"applicable": true} (провести),
    {"state": {"meta": "customerorder/metadata/states/<id>"}}.
    Короткие ссылки {'meta': 'тип/<id>'} разворачиваются сами. Суммы — в копейках.
    """
    res = _request("PUT", f"{_entity_path(entity)}/{id.strip()}", body=_expand_refs(data))
    return res if raw else _compact(res)


@mcp.tool()
@_safe
def api_request(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | list[Any] | None = None,
    raw: bool = False,
) -> Any:
    """«Сырой» запрос к любому методу JSON API 1.2 (escape-hatch).

    method — GET | POST | PUT | DELETE. Для POST/PUT/DELETE ОБЯЗАТЕЛЬНО сначала
             подтверди действие с пользователем (DELETE удаляет безвозвратно).
    path   — путь от https://api.moysklad.ru/api/remap/1.2/, напр.
             'entity/customerorder/metadata' (статусы, доп. поля),
             'report/profit/byproduct', 'report/dashboard/day',
             'entity/demand/new' (PUT — шаблон документа на основании).
    params — query-параметры: {"limit": 100, "offset": 0, "filter": "...", "expand": "..."}.
             Здесь пагинации нет: максимум limit=1000 (с expand — 100).
    body   — тело JSON; короткие ссылки {'meta': 'тип/<id>'} разворачиваются.
    """
    method = method.upper().strip()
    if method not in ("GET", "POST", "PUT", "DELETE"):
        raise ValueError("method должен быть GET, POST, PUT или DELETE.")
    res = _request(method, path, params, _expand_refs(body) if body is not None else None)
    if method == "DELETE" and res == {}:
        return "Удалено."
    return res if raw else _compact(res)


if __name__ == "__main__":
    mcp.run()
