"""One-shot song pipeline: generate -> wait for the new clips -> download -> optional trim."""

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from ..exceptions import SunoError
from .download_tools import DownloadTools
from .generate_tools import GenerateTools
from .library_tools import LibraryTools

POLL_SECONDS = 20
POLL_ROUNDS = 24  # ~8 min for clips to show up in the library
DOWNLOAD_RETRIES = 18  # audio can lag behind the clip record


def _clips(library_text: str) -> list[dict]:
    """Full songs from library_list output; Suno's 60s "preview" teasers can't be downloaded."""
    m = re.search(r"```json\n(.*?)\n```", library_text, re.S)
    return [c for c in json.loads(m.group(1)) if c.get("type") != "preview"] if m else []


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "suno-song"


class SongTools:
    def __init__(self, generate: GenerateTools, library: LibraryTools, download: DownloadTools) -> None:
        self.generate, self.library, self.download = generate, library, download

    async def create_song(
        self,
        prompt: str,
        style: str,
        title: str,
        lyrics: Optional[str] = None,
        download_path: str = "~/Music/Suno",
        max_seconds: Optional[int] = None,
        both_versions: bool = False,
    ) -> str:
        lib = _clips(await self.library.library_list(20))
        # Credit guard: a title that already exists (e.g. an earlier run that timed out) is reused, never regenerated.
        new = [c["id"] for c in lib if c.get("title") == title]
        if not new:
            before = {c["id"] for c in lib}
            await self.generate.generate_track(prompt, style, lyrics, "auto", title)
            for _ in range(POLL_ROUNDS):
                await asyncio.sleep(POLL_SECONDS)
                new = [c["id"] for c in _clips(await self.library.library_list(20)) if c["id"] not in before]
                if len(new) >= (2 if both_versions else 1):
                    break
        if not new:
            raise SunoError("No new clip appeared (Cloudflare check not ticked?)", "CREATE_TIMEOUT")

        out = Path(download_path).expanduser()
        paths = [await self._fetch(clip, out, f"{_slug(title)}{'-' + str(n + 1) if n else ''}", max_seconds)
                 for n, clip in enumerate(new[: 2 if both_versions else 1])]
        return "Song ready!\n" + "\n".join(f"{p}  (https://suno.com/song/{c})" for p, c in zip(paths, new))

    async def _fetch(self, clip: str, out: Path, stem: str, max_seconds: Optional[int]) -> Path:
        for attempt in range(DOWNLOAD_RETRIES):
            try:
                await self.download.download_track(clip, str(out))
                break
            except SunoError:
                if attempt == DOWNLOAD_RETRIES - 1:
                    raise
                await asyncio.sleep(POLL_SECONDS)
        src = next(out.glob(f"{clip}.*"))
        dst = out / f"{stem}{src.suffix}"
        if dst.exists():  # never overwrite an earlier song with the same title
            dst = out / f"{stem}-{clip[:8]}{src.suffix}"
        if max_seconds and shutil.which("ffmpeg"):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-t", str(max_seconds),
                            "-c", "copy", str(dst)], check=True, timeout=60)
            src.unlink()
        else:
            src.replace(dst)
        return dst
