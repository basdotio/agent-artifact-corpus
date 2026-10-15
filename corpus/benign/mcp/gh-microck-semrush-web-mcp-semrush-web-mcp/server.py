"""Read Semrush reports through a signed-in Chromium context."""

import asyncio
import json
import re
import uuid
from contextlib import asynccontextmanager
from html.parser import HTMLParser
from importlib.metadata import version

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from patchright.async_api import Error as BrowserError
from patchright.async_api import async_playwright
from pydantic import ValidationError

from .reports import REPORTS, report_parameters


class SemrushError(Exception):
    """A report cannot be read without changing account or authentication state."""


class UserBootstrap(HTMLParser):
    """Read the web app's JSON assignment without evaluating its JavaScript."""

    def __init__(self):
        super().__init__()
        self.in_script = False
        self.auth = {}

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, text):
        if self.in_script and (match := re.search(r"window\.sm2\.user\s*=\s*", text)):
            user, _ = json.JSONDecoder().raw_decode(text, match.end())
            if isinstance(user, dict) and user.get("api_key") and user.get("id"):
                self.auth = {"apiKey": user["api_key"], "userId": user["id"]}


FETCH_BOOTSTRAP = """async () => {
    const response = await fetch('/analytics/overview/?db=us', {
        credentials: 'include', signal: AbortSignal.timeout(45000)
    });
    return {status: response.status, text: response.ok ? await response.text() : ''};
}"""

# Only fixed report methods above are exposed. Callers cannot supply a URL,
# JavaScript, RPC method, auth fields or account-changing operation.
FETCH_REPORT = """async ({path, payload, get, headers}) => {
    const query = new URLSearchParams();
    if (get) for (const [key, value] of Object.entries(payload)) {
        for (const item of Array.isArray(value) ? value : [value]) query.append(key, item);
    }
    const response = await fetch(get ? path + '?' + query : path, {
        method: get ? 'GET' : 'POST', credentials: 'include',
        headers: {...headers, ...(get ? {} : {'Content-Type': 'application/json'})},
        ...(get ? {} : {body: JSON.stringify(payload)}),
        signal: AbortSignal.timeout(45000)
    });
    if (!response.ok) return {status: response.status};
    return {status: response.status, text: await response.text()};
}"""
CHECK_AUTH = """async () => {
    const response = await fetch('/home/', {
        method: 'HEAD', credentials: 'include', cache: 'no-store',
        signal: AbortSignal.timeout(15000)
    });
    return response.ok && new URL(response.url).pathname === '/home/';
}"""


class BrowserSession:
    def __init__(
        self, cdp_url="http://127.0.0.1:9234", *, context=None, origin="https://www.semrush.com"
    ):
        self.cdp_url = cdp_url
        self.origin = origin
        self.context = context
        self.page = None
        self.playwright = None
        self.auth = {}
        self.spectrum_headers = {}
        self.lock = asyncio.Lock()

    async def connect(self):
        if self.page is not None and not self.page.is_closed():
            return
        if self.context is None:
            self.playwright = await async_playwright().start()
            try:
                browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
            except BrowserError:
                await self.close()
                raise SemrushError(
                    "Semrush browser unavailable. Run semrush-web-mcp setup."
                ) from None
            self.context = browser.contexts[0]
        self.page = await self.context.new_page()
        try:
            # Establish the origin, then read authentication without loading charts,
            # app bundles or dashboard polling in every MCP process.
            await self.page.goto(
                self.origin + "/robots.txt", wait_until="domcontentloaded", timeout=45000
            )
            response = await self.page.evaluate(FETCH_BOOTSTRAP, isolated_context=False)
            bootstrap = UserBootstrap()
            bootstrap.feed(response["text"])
            if response["status"] != 200 or not bootstrap.auth:
                await self.close()
                raise SemrushError(
                    "Semrush authentication metadata unavailable. Sign in with semrush-web-mcp login; if already signed in, the web app may have changed."
                )
            self.auth = bootstrap.auth
        except (BrowserError, TimeoutError, ValueError):
            await self.close()
            raise SemrushError(
                "Semrush authentication bootstrap failed. Check the browser service and sign in."
            ) from None

    async def connect_spectrum(self):
        if self.spectrum_headers:
            return
        ready = asyncio.Event()

        def observe(request):
            if request.url.startswith(self.origin + "/spectrum/") and request.headers.get(
                "authorization"
            ):
                self.spectrum_headers = {
                    key: request.headers[key]
                    for key in ("authorization",)
                    if key in request.headers
                }
                ready.set()

        self.page.on("request", observe)
        try:
            await self.page.goto(
                self.origin + "/analytics/keywordgap/?db=us",
                wait_until="domcontentloaded",
                timeout=45000,
            )
            await asyncio.wait_for(ready.wait(), timeout=15)
        except (BrowserError, TimeoutError):
            raise SemrushError(
                "Semrush keyword gap authentication unavailable. Reconnect MCP after signing in."
            ) from None
        finally:
            self.page.remove_listener("request", observe)
            await self.page.goto(self.origin + "/robots.txt", wait_until="domcontentloaded")

    async def check_auth(self):
        if not await self.page.evaluate(CHECK_AUTH, isolated_context=False):
            await self.close()
            raise SemrushError(
                "Semrush session expired. Run semrush-web-mcp login, then reconnect MCP."
            )

    def redact(self, value):
        # Provider errors and REST responses can echo page-owned authentication.
        if isinstance(value, dict):
            return {
                key: self.redact(item)
                for key, item in value.items()
                if key.lower() not in {"apikey", "key", "userid", "access_token", "authorization"}
            }
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, str):
            for secret in (
                self.auth.get("apiKey", ""),
                self.spectrum_headers.get("authorization", ""),
                self.spectrum_headers.get("authorization", "").removeprefix("Bearer "),
            ):
                # Do not replace numeric user identifiers inside URLs or business text.
                if secret:
                    value = value.replace(str(secret), "[redacted]")
        return value

    async def request(self, path, payload, *, get=False, headers=None):
        response = await self.page.evaluate(
            FETCH_REPORT,
            {"path": path, "payload": payload, "get": get, "headers": headers or {}},
            isolated_context=False,
        )
        if response["status"] != 200:
            raise SemrushError(f"Semrush report: HTTP {response['status']}")
        try:
            # Parse outside JavaScript so 64-bit report identifiers stay exact.
            body = json.loads(response["text"])
        except ValueError:
            raise SemrushError(
                "Semrush report: expected JSON, received a page or challenge"
            ) from None
        if isinstance(body, dict):
            if "error" in body:
                error = body["error"]
                if isinstance(error, dict):
                    message = f"{error.get('code')} {error.get('message', 'Report failed')}"
                else:
                    message = str(error)
                raise SemrushError(f"Semrush report: {self.redact(message)[:500]}")
            if body.get("status") not in (None, "SUCCESS", "success"):
                raise SemrushError(f"Semrush report: {self.redact(str(body.get('status')))[:500]}")
        return body

    async def rpc(self, method, params, *, transport="keyword", web_report="domain.overview"):
        path = {
            "domain": "/dpa/rpc",
            "direct": "/dpa/rpc",
            "magic": "/kmtgw/v2/webapi",
            "keyword": "/kwogw/v2/webapi",
        }[transport]
        if transport == "domain":
            params = {
                "request_id": str(uuid.uuid4()),
                "report": web_report,
                "args": params,
                **self.auth,
            }
        elif transport == "direct":
            params = {**params, **self.auth}
        body = await self.request(
            path, {"id": 1, "jsonrpc": "2.0", "method": method, "params": params}
        )
        if "result" not in body:
            raise SemrushError(f"Semrush {method}: missing report result")
        return body["result"]

    async def report(self, name, arguments):
        if name not in REPORTS:
            raise SemrushError(f"Unknown report: {name}")
        definition = REPORTS[name]
        query = definition.query.model_validate(arguments).model_dump()
        async with self.lock:
            await self.connect()
            await self.check_auth()
            params = report_parameters(definition, query)
            family = definition.transport
            if family in ("keyword", "domain", "direct", "magic"):
                result = await self.rpc(
                    definition.method,
                    params,
                    transport=family,
                    web_report=definition.web_report,
                )
            else:
                headers = {}
                if family == "gap":
                    await self.connect_spectrum()
                    headers = {
                        **self.spectrum_headers,
                        "x-report": "gap.keywords",
                        "x-request-id": str(uuid.uuid4()),
                    }
                if family.startswith("backlink"):
                    path = "/analytics/backlinks/webapi2/"
                    if family == "backlink_overview":
                        path += "overview/" + definition.method
                    params["key"] = self.auth["apiKey"]
                    if family == "backlink_overview":
                        headers["x-request-id"] = str(uuid.uuid4())
                        await self.request(
                            "/analytics/backlinks/webapi2/overview/init",
                            params,
                            get=True,
                            headers=headers,
                        )
                else:
                    path = definition.method
                    if path.startswith("/siteaudit/"):
                        params["key"] = self.auth["apiKey"]
                result = await self.request(
                    path, params, get=family not in ("post", "gap", "projects"), headers=headers
                )
            if definition.total_method:
                total = await self.rpc(
                    definition.total_method,
                    {key: value for key, value in params.items() if key != "display"}
                    if name == "domain_position_changes"
                    else params,
                    transport="domain",
                    web_report=definition.web_report,
                )
                result = {
                    "rows": result,
                    "total": total,
                    "page": query["page"],
                    "page_size": query["page_size"],
                }
            if name == "keyword_overview":
                matches = [
                    item for item in result["keywords"] if item["database"] == query["database"]
                ]
                if not matches:
                    raise SemrushError("No keyword data for the selected database")
                result = matches[0]
            elif name == "domain_overview":
                metrics = [item for item in result if item["database"] == query["database"]]
                if not metrics:
                    raise SemrushError("No domain data for the selected database")
                backlinks = await self.rpc(
                    "backlinks.Summary",
                    {
                        "searchItem": query["domain"],
                        "searchType": "domain",
                    },
                    transport="domain",
                )
                result = {"search": metrics[0], "backlinks": backlinks}
            if "limit" in query and isinstance(result, list):
                result = result[: query["limit"]]
            return {"authenticated": True, "report": name, "data": self.redact(result)}

    async def close(self):
        if self.page is not None and not self.page.is_closed():
            await self.page.close()
        if self.playwright is not None:
            await self.playwright.stop()
            self.playwright = None
            self.context = None
        self.page = None
        self.auth.clear()
        self.spectrum_headers.clear()


def create_server(session):
    tools = [
        types.Tool(
            name=name,
            description=f"Authenticated Semrush web report. {report.description}",
            inputSchema=report.query.model_json_schema(),
            annotations=types.ToolAnnotations(readOnlyHint=True, openWorldHint=True),
        )
        for name, report in REPORTS.items()
    ]

    async def list_tools(ctx, params):
        return types.ListToolsResult(tools=tools)

    async def call_tool(ctx, params):
        try:
            result = await session.report(params.name, params.arguments or {})
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(result))]
            )
        except (SemrushError, ValidationError) as error:
            message = str(error)
        except Exception:  # noqa: BLE001 - the MCP boundary must not leak browser details
            # Browser exceptions can include request details. Do not print them.
            message = "Semrush browser request failed. Check the browser service and reconnect MCP."
        return types.CallToolResult(
            isError=True, content=[types.TextContent(type="text", text=message)]
        )

    @asynccontextmanager
    async def lifespan(server):
        try:
            yield {}
        finally:
            await session.close()

    return Server(
        "semrush-web-mcp",
        version=version("semrush-web-mcp"),
        lifespan=lifespan,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


async def serve(cdp_url):
    server = create_server(BrowserSession(cdp_url))
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())
