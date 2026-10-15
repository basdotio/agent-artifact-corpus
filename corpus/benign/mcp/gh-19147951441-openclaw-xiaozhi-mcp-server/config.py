import os
from dotenv import load_dotenv

load_dotenv()

OPENCLAW_WS_URL = "wss://api.xiaozhi.me/mcp/"
OPENCLAW_TOKEN = os.getenv("OPENCLAW_TOKEN", "")

if not OPENCLAW_TOKEN:
    raise ValueError("请设置 OPENCLAW_TOKEN 环境变量")
