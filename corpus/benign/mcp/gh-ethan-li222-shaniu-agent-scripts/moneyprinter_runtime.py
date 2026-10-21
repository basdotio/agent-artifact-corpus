"""Private configuration and local fonts for the bundled video engine."""
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BUNDLED = ROOT / 'vendor/moneyprinter'


def configure_project(project):
    """Keep external checkout behavior; only the bundled engine uses private data."""
    project = Path(project).resolve()
    if project != BUNDLED.resolve():
        return project / 'config.toml'
    configured = Path(os.getenv('SHANIU_MPT_CONFIG') or 'data/moneyprinter/config.toml').expanduser()
    path = (configured if configured.is_absolute() else ROOT / configured).resolve()
    if path.is_relative_to((ROOT / 'vendor').resolve()):
        raise ValueError('Private MoneyPrinter config must stay outside vendor/')
    if path.exists() and not path.is_file():
        raise ValueError('MoneyPrinter config path must be a file')
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation preserves user settings during concurrent startup.
        try:
            with path.open('xb') as target, (project / 'config.example.toml').open('rb') as source:
                shutil.copyfileobj(source, target)
        except FileExistsError:
            pass
    os.environ['SHANIU_MPT_CONFIG'] = str(path)
    return path


def subtitle_font(requested, font_dir):
    """Respect existing fonts, otherwise use an installed CJK font, never bundle it."""
    override = os.getenv('SHANIU_MPT_FONT_FILE', '').strip()
    if override:
        path = Path(override).expanduser()
        path = (path if path.is_absolute() else ROOT / path).resolve()
        if not path.is_file():
            raise ValueError('SHANIU_MPT_FONT_FILE must reference an installed font')
        return str(path)
    original = Path(font_dir) / (requested or 'STHeitiMedium.ttc')
    if original.is_file():
        return str(original.resolve())
    fonts = Path(os.getenv('WINDIR', 'C:/Windows')) / 'Fonts'
    candidates = [fonts/'msyh.ttc', fonts/'simhei.ttf', fonts/'simsun.ttc',
                  Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
                  Path('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'),
                  Path('/System/Library/Fonts/PingFang.ttc')]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    raise ValueError('No CJK subtitle font found; install one and set SHANIU_MPT_FONT_FILE, or disable subtitles')
