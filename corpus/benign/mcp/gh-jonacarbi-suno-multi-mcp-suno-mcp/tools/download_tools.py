"""Download tools for Suno MCP — CDN-based direct download."""

import logging
import shutil
import subprocess
import sys
from pathlib import Path

from ..browser.manager import BrowserManager
from ..exceptions import SunoError

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr)

# Suno's CDN/stream audio is signed or encrypted; the supported path is the song page's
# Download dialog (Free plan: each song "unlocks" once from the monthly download quota).
SONG_URL = "https://suno.com/song/{}"


class DownloadTools:
    """Tools for downloading tracks from Suno AI."""

    def __init__(self, manager: BrowserManager) -> None:
        self.manager = manager

    async def download_track(
        self,
        track_id: str,
        download_path: str = "downloads/",
        include_stems: bool = False,
    ) -> str:
        """Download a track via Suno's Download dialog; saves `{track_id}.mp3`
        (converted with ffmpeg) or the raw m4a if ffmpeg is missing."""
        try:
            page = (await self.manager.ensure_browser())["page"]
            await page.goto(SONG_URL.format(track_id))
            await page.locator('button[aria-label="More options"]:visible').first.click()
            await page.get_by_text("Download", exact=True).last.click()
            unlock = page.get_by_role("button", name="Unlock & Download")
            download_btn = page.get_by_role("button", name="Download", exact=True)
            await unlock.or_(download_btn).first.wait_for()
            async with page.expect_download(timeout=120_000) as dl:
                await (unlock if await unlock.count() else download_btn).click()
            download = await dl.value

            download_dir = Path(download_path).expanduser()
            download_dir.mkdir(parents=True, exist_ok=True)
            raw = download_dir / f"{track_id}{Path(download.suggested_filename).suffix or '.m4a'}"
            await download.save_as(raw)
            filepath = raw
            if raw.suffix != ".mp3" and shutil.which("ffmpeg"):
                filepath = raw.with_suffix(".mp3")
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-q:a", "2", str(filepath)],
                    check=True, timeout=120,
                )
                raw.unlink()
            if filepath.stat().st_size < 1024:
                raise SunoError(f"Downloaded file too small: {filepath}", "DOWNLOAD_INVALID")

            size = filepath.stat().st_size
            return (
                f"Download completed!\n"
                f"Track ID: {track_id}\n"
                f"Path: {filepath}\n"
                f"Size: {size:,} bytes ({size // 1024} KB)"
            )

        except SunoError:
            raise
        except Exception as e:
            logger.error("Download failed: %s", e)
            raise SunoError(f"Download failed: {e}", "DOWNLOAD_ERROR")
