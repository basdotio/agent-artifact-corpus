"""Bounded PNG capture without tab activation, resizing or implicit scrolling."""
import base64
from dataclasses import dataclass
import math
import os
from pathlib import Path
import struct
import tempfile

from ..errors import OmniError

MAX_PIXELS = 6000000
MAX_SIDE = 8192
MAX_BYTES = 4 * 1024 * 1024


@dataclass
class ScreenshotResult:
    metadata: dict
    png: bytes


def destination(output, mkdir=False, overwrite=False):
    if output is None:
        return None
    path = Path(output).absolute()
    if path.is_symlink() or path.exists() and (not overwrite or not path.is_file()):
        raise OmniError('OUTPUT_EXISTS', 'Screenshot output exists or is a symlink; use --overwrite for a regular file.', 2)
    if not path.parent.is_dir() and not mkdir:
        raise OmniError('INVALID_ARGUMENT', 'Screenshot parent must exist; use --mkdir explicitly.', 2)
    return path


def publish(path, data, mkdir, overwrite):
    temporary = None
    try:
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.omni-png-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
            temporary.unlink()
    except OSError:
        raise OmniError('SCREENSHOT_WRITE', 'Cannot publish screenshot; existing output was not silently overwritten.', 6) from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def screenshot(page, tab_id, output=None, full_page=False, mkdir=False, overwrite=False, timeout=10000):
    from playwright.sync_api import Error
    path = destination(output, mkdir, overwrite)
    session = page.context.new_cdp_session(page)
    try:
        layout = session.send('Page.getLayoutMetrics')
        view = layout['cssVisualViewport']
        bounds = layout['cssContentSize'] if full_page else {
            'x': view['pageX'], 'y': view['pageY'], 'width': view['clientWidth'], 'height': view['clientHeight'],
        }
        width, height = math.ceil(bounds['width']), math.ceil(bounds['height'])
        if width <= 0 or height <= 0 or max(width, height) > MAX_SIDE or width * height > MAX_PIXELS:
            raise OmniError('SCREENSHOT_LIMIT', 'Capture exceeds 8192px per side or 6000000 pixels; use viewport capture.', 2)
        dpr = page.evaluate('() => window.devicePixelRatio || 1')
        response = session.send('Page.captureScreenshot', {
            'format': 'png', 'fromSurface': True, 'captureBeyondViewport': full_page,
            'clip': {**bounds, 'scale': 1 / dpr},
        })
        # Limit encoded size before decoding as well as verifying actual PNG dimensions.
        if len(response['data']) > (MAX_BYTES + 2) // 3 * 4:
            raise OmniError('SCREENSHOT_LIMIT', 'PNG exceeds the 4 MiB image payload limit.', 2)
        png = base64.b64decode(response['data'], validate=True)
        if png[:8] != b'\x89PNG\r\n\x1a\n' or len(png) < 24:
            raise OmniError('SCREENSHOT', 'Browser did not return a valid PNG header.', 4)
        width, height = struct.unpack('>II', png[16:24])
        if len(png) > MAX_BYTES or width * height > MAX_PIXELS or max(width, height) > MAX_SIDE:
            raise OmniError('SCREENSHOT_LIMIT', 'Actual PNG exceeds the image size limits.', 2)
        if path is not None:
            publish(path, png, mkdir, overwrite)
        return ScreenshotResult({'ok': True, 'tab_id': tab_id, 'url': page.url,
                                 'path': str(path) if path else None, 'format': 'png',
                                 'width': width, 'height': height, 'bytes': len(png), 'full_page': full_page}, png)
    except Error:
        raise OmniError('SCREENSHOT', 'Capture failed; inspect the selected tab.', 4) from None
    finally:
        try:
            session.detach()
        except Error:
            pass
