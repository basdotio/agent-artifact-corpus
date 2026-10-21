import os
import subprocess
import psutil
from fastmcp import FastMCP
import base64, os, requests
import io
import mss
from PIL import Image

from instructions import SERVER_INSTRUCTIONS
from research_topic import research_topic
from analyze_data import analyze_data
from script_writer import write_script, run_script

from dotenv import load_dotenv
load_dotenv()


mcp = FastMCP("laptop-assistant", instructions=SERVER_INSTRUCTIONS)

mcp.tool()(research_topic)
mcp.tool()(analyze_data)

mcp.tool()(write_script)
mcp.tool()(run_script)

def _grab_screen_png(max_side: int = 1600) -> bytes:
    """Capture the primary monitor and shrink it (cheaper and faster for the model)."""
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _ask_vision_model(png: bytes, question: str) -> str:
    b64 = base64.b64encode(png).decode()
    model = "gemini-2.5-flash"  # or any vision-capable Gemini model in your AI Studio
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": os.environ["GOOGLE_API_KEY"]},
        json={
            "contents": [{"parts": [
                {"text": question},
                {"inline_data": {"mime_type": "image/png", "data": b64}},
            ]}],
            "generationConfig": {"maxOutputTokens": 2000},
        },
        timeout=60,
    )
    if not r.ok:
        raise RuntimeError(f"{r.status_code}: {r.text}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


@mcp.tool()
def ask_about_screen(question: str) -> str:
    """Look at the user's laptop screen right now and answer a question about it.
    Use when the user asks about something visible on screen, such as an error
    message, a chart, a page they are reading, or what app is open."""
    png = _grab_screen_png()
    return _ask_vision_model(png, question)


@mcp.tool
def run_git_status(repo_path: str = ".") -> str:
    """Runs 'git status' in the specified directory to check for uncommitted work."""
    try:
        result = subprocess.run(
            ["git", "status"], 
            cwd=repo_path, 
            capture_output=True, 
            text=True,
            check=True
        )
        return result.stdout
    except Exception as e:
        return f"Failed to run git status: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")  # serves at http://127.0.0.1:8000/mcp