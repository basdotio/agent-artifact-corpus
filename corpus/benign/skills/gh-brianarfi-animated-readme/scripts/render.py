#!/usr/bin/env python3
"""Render every scene in readme-scenes.json to a GIF (and an optional still PNG), in one command.

Usage:
    python scripts/render.py                          # uses ./readme-scenes.json
    python scripts/render.py --config path/to/readme-scenes.json
    python scripts/render.py --only hero              # one scene by name
    python scripts/render.py --check                  # validate the config, render nothing
    python scripts/render.py --list-styles            # the 17 visual styles you can set as "style"

What it does, per scene:
    1. Fills the template (templates/<template>.html) with the scene's "data" block.
    2. Records it frame by frame to the GIF path, deterministically (scripts/record_html.py).
    3. Writes a still PNG if the scene asks for one, for places that do not play GIFs.
    4. Warns when a GIF is over the size budget, because a heavy README loads slowly on GitHub.
    5. Writes readme-snippets.md next to the config: the markdown image line for each scene,
       with its alt text, ready to paste into the README.

Styles: an optional top-level "style" key (and a per-scene "style" override) restyles the scenes
with one of 17 named looks from templates/skins.css. Layout, copy and timing do not change. Leave
"style" out and the built-in look and your "theme" colours are used exactly as before. When both
"style" and "theme" are given, the style sets the palette and your theme colours are applied on top.
Use "style": "none" on one scene to opt it out of a project-wide style.

Paths in the config are relative to the config file.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import record_html  # noqa: E402

TEMPLATES = HERE.parent / 'templates'
SIZES = {  # template: (width, height, default seconds)
    'hero': (1600, 800, 9),
    'before-after': (1200, 680, 12),
    'how-it-works': (1200, 660, 12),
}
BUDGET_MB = 4.0
SKINS = TEMPLATES / 'skins.css'
STYLES = {  # key: display name. Same keys as the shared style gallery.
    'math': 'Math / 3Blue1Brown',
    'typographic': 'Typographic (Swiss mono)',
    'cutpaper': 'Cut paper',
    'sketchbook': 'Sketchbook / crosshatch',
    'riso': 'Risograph',
    'terminal': 'Dark terminal',
    'isometric': 'Isometric blocks',
    'blueprint': 'Blueprint',
    'brutalist': 'Neo brutalism',
    'whiteboard': 'Whiteboard marker',
    'liquid': 'Liquid morph',
    'holo': 'Holographic neon',
    'glass': 'Glass morphism',
    'clay': 'Clay 3D',
    'ascii': 'ASCII art',
    'pixel': 'Pixel art',
    'artdeco': 'Art deco',
}
NO_STYLE = ('none', 'default')  # explicit "keep the built-in look" for one scene

# Runs before the template script. The templates animate some parts with the Web Animations API and
# a fixed easing; this lets a skin's --ease reach those too. No timers, no randomness.
SKIN_JS = ('(function(){var A=Element.prototype.animate;Element.prototype.animate=function(k,o){'
           "if(o&&o.easing==='cubic-bezier(.2,.8,.2,1)'){var e=getComputedStyle(document.documentElement)"
           ".getPropertyValue('--ease').trim();if(e)o.easing=e;}return A.call(this,k,o);};})();")


def bad_style(value):
    """Return an error message when `value` is not a usable style key, else None."""
    if value is None or value in NO_STYLE or value in STYLES:
        return None
    return (f'"style" must be one of {", ".join(sorted(STYLES))} (or "none"), got {value!r}. '
            'Run render.py --list-styles to see them.')


def pick_style(cfg, scene):
    """The style for one scene: the scene's own, else the project's. None means the built-in look."""
    value = scene['style'] if 'style' in scene else cfg.get('style')
    return None if value in (None, *NO_STYLE) else value


def problems(cfg):
    out = []
    names = set()
    msg = bad_style(cfg.get('style'))
    if msg:
        out.append(f'top level: {msg}')
    for i, s in enumerate(cfg.get('scenes', [])):
        where = f'scenes[{i}]'
        name = s.get('name')
        if not name:
            out.append(f'{where}: missing "name"')
        elif name in names:
            out.append(f'{where}: duplicate name "{name}"')
        names.add(name)
        msg = bad_style(s.get('style'))
        if msg:
            out.append(f'{where}: {msg}')
        t = s.get('template')
        if t not in SIZES and not s.get('html'):
            out.append(f'{where}: "template" must be one of {sorted(SIZES)}, or give your own "html" page')
        if not s.get('gif'):
            out.append(f'{where}: missing "gif" output path')
        alt = (s.get('alt') or '').strip()
        if len(alt) < 40:
            out.append(f'{where}: "alt" is missing or too short. Describe what the GIF shows, '
                       'in order, for someone who cannot see it.')
        d = s.get('data') or {}
        if t == 'before-after' and not (d.get('before') and d.get('after')):
            out.append(f'{where}: before-after needs "before" cards and "after" outcomes')
        if t == 'how-it-works' and not d.get('steps'):
            out.append(f'{where}: how-it-works needs "steps"')
        if t == 'hero' and not d.get('title'):
            out.append(f'{where}: hero needs a "title"')
        text = json.dumps(d, ensure_ascii=False)
        dash = chr(0x2014)
        if dash in text or dash in alt:
            out.append(f'{where}: contains an em-dash. Use a comma, a colon or a full stop.')
    if not cfg.get('scenes'):
        out.append('no "scenes" in the config')
    return out


def fill(template, data, dur, style=None):
    html = (TEMPLATES / f'{template}.html').read_text(encoding='utf-8')
    payload = dict(data)
    payload['_dur'] = dur
    js = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
    assert '/*DATA*/null' in html, f'{template}.html has no /*DATA*/ slot'
    html = html.replace('/*DATA*/null', js)
    if style:
        assert style in STYLES, f'unknown style {style!r}'
        # Skin first, theme after: the theme colours are set inline by the template script,
        # which beats the skin's variables, so a project's own colours still win.
        css = SKINS.read_text(encoding='utf-8')
        head = f'<style id="skin">\n{css}\n</style>\n<script id="skin-js">{SKIN_JS}</script>\n</head>'
        assert '</head>' in html and '<html' in html
        html = html.replace('</head>', head, 1)
        html = html.replace('<html', f'<html data-style="{style}"', 1)
    return html


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', default='readme-scenes.json')
    ap.add_argument('--only', action='append', help='render only this scene (repeatable)')
    ap.add_argument('--check', action='store_true', help='validate the config and stop')
    ap.add_argument('--list-styles', action='store_true', help='print the style keys and names, then stop')
    a = ap.parse_args()

    if a.list_styles:
        for key, name in STYLES.items():
            print(f'{key:<12} {name}')
        return

    cfg_path = Path(a.config).resolve()
    if not cfg_path.exists():
        sys.exit(f'No config at {cfg_path}. Copy examples/readme-scenes.json to start.')
    cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
    base = cfg_path.parent
    issues = problems(cfg)
    if issues:
        print('Fix these first:')
        for p in issues:
            print('  -', p)
        sys.exit(1)
    if a.check:
        print(f'OK: {len(cfg["scenes"])} scene(s) ready to render.')
        return

    theme = cfg.get('theme') or {}
    snippets = []
    work = Path(tempfile.mkdtemp(prefix='scenes-'))
    for s in cfg['scenes']:
        if a.only and s['name'] not in a.only:
            continue
        t = s.get('template')
        w, h, d = SIZES.get(t, (s.get('w', 1200), s.get('h', 600), 8))
        w, h = s.get('w', w), s.get('h', h)
        dur = float(s.get('seconds', d))
        if t in SIZES:
            data = dict(s.get('data') or {})
            if theme and 'theme' not in data:
                data['theme'] = theme
            page = work / f'{s["name"]}.html'
            page.write_text(fill(t, data, dur, pick_style(cfg, s)), encoding='utf-8')
            # Keep the filled page next to the template source, so it can be opened and tweaked.
        else:
            page = (base / s['html']).resolve()
        gif = (base / s['gif']).resolve()
        gif.parent.mkdir(parents=True, exist_ok=True)
        how, n = record_html.record(page, gif, w, h, dur, fps=s.get('fps', 12),
                                    scale=s.get('scale', 1.0), colors=s.get('colors', 128))
        mb = gif.stat().st_size / 1e6
        flag = '' if mb <= BUDGET_MB else f'  OVER BUDGET ({BUDGET_MB} MB): lower "fps", "colors" or "seconds"'
        print(f'{s["name"]:>14}: {gif.relative_to(base)}  {mb:.2f} MB, {n} frames, via {how}{flag}')
        if s.get('still'):
            png = (base / s['still']).resolve()
            record_html.still(page, png, w, h, float(s.get('still_at', dur * 0.75)))
            print(f'{"":>14}  still: {png.relative_to(base)}')
        alt = ' '.join(s['alt'].split()).replace(']', ')')
        snippets.append(f'<!-- {s["name"]} -->\n![{alt}]({s["gif"]})\n')
    (base / 'readme-snippets.md').write_text(
        '# Paste these into your README\n\nEach line carries its alt text. Keep it when you move the line.\n\n'
        + '\n'.join(snippets), encoding='utf-8')
    print(f'\nWrote {base / "readme-snippets.md"}')


if __name__ == '__main__':
    main()
