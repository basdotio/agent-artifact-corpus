"""
Módulo de Automatización Pasiva por WebSocket CDP para LinkedIn.
Permite interactuar de forma 100% silenciosa y sin robo de foco con la sesión activa
de LinkedIn en Brave Browser (puerto 9222), evitando la revocación concurrente de li_at
y los cuelgues por exceso de targets de connect_over_cdp.
"""

import asyncio
import json
import logging
import os
import sys
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mcp_linkedin_cdp")

CDP_BASE_URL = "http://127.0.0.1:9222"

def is_brave_cdp_available() -> bool:
    """Verifica si Brave está ejecutándose con el puerto de depuración 9222 abierto."""
    try:
        req = urllib.request.Request(f"{CDP_BASE_URL}/json/version")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def get_active_linkedin_tab() -> Optional[Dict[str, Any]]:
    """Obtiene la pestaña activa de LinkedIn en Brave CDP."""
    try:
        req = urllib.request.Request(f"{CDP_BASE_URL}/json")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            tabs = json.loads(resp.read().decode("utf-8"))
        # Priorizar páginas del feed o perfil
        pages = [t for t in tabs if t.get("type") == "page" and "linkedin.com" in t.get("url", "")]
        for p in pages:
            url = p.get("url", "")
            if "login" not in url and "checkpoint" not in url:
                return p
        return pages[0] if pages else None
    except Exception as e:
        logger.debug(f"Error consultando pestañas de Brave CDP: {e}")
        return None

class BraveLinkedInCDP:
    """Cliente WebSocket CDP directo para la pestaña de LinkedIn en Brave."""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._msg_id = 0

    @classmethod
    async def connect_active(cls) -> Optional["BraveLinkedInCDP"]:
        """Intenta conectarse a la pestaña activa de LinkedIn en Brave."""
        if not is_brave_cdp_available():
            return None
        tab = get_active_linkedin_tab()
        if not tab or "webSocketDebuggerUrl" not in tab:
            return None
        return cls(tab["webSocketDebuggerUrl"])

    async def _send(self, ws, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._msg_id += 1
        current_id = self._msg_id
        payload = {"id": current_id, "method": method}
        if params:
            payload["params"] = params
        await ws.send(json.dumps(payload))
        while True:
            res = await ws.recv()
            data = json.loads(res)
            if data.get("id") == current_id:
                return data

    async def evaluate(self, expression: str, return_by_value: bool = True) -> Any:
        """Evalúa una expresión JavaScript en el contexto de la página."""
        import websockets
        async with websockets.connect(self.ws_url) as ws:
            res = await self._send(ws, "Runtime.evaluate", {
                "expression": expression,
                "returnByValue": return_by_value
            })
            val = res.get("result", {}).get("result", {}).get("value")
            return val

    async def insert_text(self, text: str) -> bool:
        """Inyecta texto multilínea nativo mediante Input.insertText."""
        import websockets
        async with websockets.connect(self.ws_url) as ws:
            await self._send(ws, "Input.insertText", {"text": text})
            return True

    async def set_file_input(self, file_path: str, selector: str = "input[type='file']") -> bool:
        """Asigna archivos a un input de tipo file mediante DOM.setFileInputFiles."""
        import websockets
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Archivo no encontrado: {abs_path}")

        async with websockets.connect(self.ws_url) as ws:
            doc = await self._send(ws, "DOM.getDocument")
            root_id = doc.get("result", {}).get("root", {}).get("nodeId", 1)
            query_res = await self._send(ws, "DOM.querySelectorAll", {
                "nodeId": root_id,
                "selector": selector
            })
            node_ids = query_res.get("result", {}).get("nodeIds", [])
            if not node_ids:
                return False
            for nid in node_ids:
                await self._send(ws, "DOM.setFileInputFiles", {
                    "files": [abs_path],
                    "nodeId": nid
                })
            return True

    async def navigate(self, url: str) -> bool:
        """Navega a una URL dentro de la misma pestaña."""
        import websockets
        async with websockets.connect(self.ws_url) as ws:
            await self._send(ws, "Page.navigate", {"url": url})
            return True

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """Obtiene las cookies de la sesión activa de LinkedIn."""
        import websockets
        async with websockets.connect(self.ws_url) as ws:
            res = await self._send(ws, "Network.getCookies", {"urls": ["https://www.linkedin.com"]})
            return res.get("result", {}).get("cookies", [])
