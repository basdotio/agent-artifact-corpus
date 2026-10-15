#!/usr/bin/env python3
"""The kit's own check: the example config validates, styles are validated and injected, and one
scene renders to a looping GIF, plain and with a style.

Usage: python tests/test_render.py
Needs Playwright with Chromium. Uses ffmpeg when it is on PATH, otherwise Pillow.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    cfg = json.loads((ROOT / 'readme-scenes.json').read_text(encoding='utf-8'))
    sys.path.insert(0, str(ROOT / 'scripts'))
    import render
    assert render.problems(cfg) == [], render.problems(cfg)

    bad = {'scenes': [{'name': 'x', 'template': 'hero', 'gif': 'x.gif', 'alt': 'short', 'data': {}}]}
    found = render.problems(bad)
    assert any('alt' in p for p in found) and any('title' in p for p in found), found

    # Styles: unknown keys are caught, with the valid keys listed, at the top level and per scene.
    scene0 = cfg['scenes'][0]
    found = render.problems({**cfg, 'style': 'neon-unicorn'})
    assert any('neon-unicorn' in p and 'pixel' in p for p in found), found
    found = render.problems({'scenes': [dict(scene0, style='nope')]})
    assert any('scenes[0]' in p and 'nope' in p for p in found), found
    for ok in ('pixel', 'none', None):
        assert render.problems({**cfg, 'style': ok}) == [], ok
    assert len(render.STYLES) == 17
    css = (ROOT / 'templates' / 'skins.css').read_text(encoding='utf-8')
    blocks = set(re.findall(r'html\[data-style="([a-z]+)"\]\s*\{', css))
    assert blocks == set(render.STYLES), (blocks ^ set(render.STYLES))

    # No style: the filled page is exactly what the templates produced before skins existed.
    for s in cfg['scenes']:
        t, data = s['template'], dict(s['data'])
        dur = float(s.get('seconds', render.SIZES[t][2]))
        raw = (ROOT / 'templates' / f'{t}.html').read_text(encoding='utf-8')
        payload = dict(data)
        payload['_dur'] = dur
        js = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
        reference = raw.replace('/*DATA*/null', js)
        assert render.fill(t, data, dur) == reference, f'{t}: default output changed'
        assert render.fill(t, data, dur, None) == reference
        assert 'data-style' not in reference and 'id="skin"' not in reference
        # With a style: skin CSS goes last in <head>, data-style is set, the page body is untouched.
        styled = render.fill(t, data, dur, 'terminal')
        assert '<html data-style="terminal"' in styled and styled.count('<style id="skin">') == 1
        assert styled.index('<style id="skin">') > styled.index('</style>') and styled.index('</head>') > styled.index('id="skin-js"')
        assert styled.split('</head>', 1)[1] == reference.split('</head>', 1)[1]

    # A style applied from the config, and per-scene override and opt-out.
    two = {'style': 'pixel', 'scenes': [dict(scene0), dict(scene0, name='b', style='none'), dict(scene0, name='c', style='clay')]}
    assert [render.pick_style(two, x) for x in two['scenes']] == ['pixel', None, 'clay']

    with tempfile.TemporaryDirectory() as d:
        scene = dict(cfg['scenes'][2])
        scene['gif'] = 'out.gif'
        scene['seconds'] = 3
        scene['fps'] = 6
        scene.pop('still', None)
        test_cfg = Path(d) / 'readme-scenes.json'
        test_cfg.write_text(json.dumps({'scenes': [scene]}), encoding='utf-8')
        subprocess.run([sys.executable, str(ROOT / 'scripts' / 'render.py'), '--config', str(test_cfg)], check=True)
        gif = Path(d) / 'out.gif'
        head = gif.read_bytes()[:6]
        assert head in (b'GIF89a', b'GIF87a'), head
        assert gif.stat().st_size > 10_000, gif.stat().st_size
        assert (Path(d) / 'readme-snippets.md').exists()

        # The same scene with a style (pixel: stepped motion, dark) renders to a valid GIF too.
        styled_scene = dict(scene, gif='styled.gif', name='styled', style='pixel')
        styled_cfg = Path(d) / 'styled-scenes.json'
        styled_cfg.write_text(json.dumps({'scenes': [styled_scene]}), encoding='utf-8')
        subprocess.run([sys.executable, str(ROOT / 'scripts' / 'render.py'), '--config', str(styled_cfg)], check=True)
        sgif = Path(d) / 'styled.gif'
        assert sgif.read_bytes()[:6] in (b'GIF89a', b'GIF87a')
        assert sgif.stat().st_size > 10_000, sgif.stat().st_size
        assert sgif.read_bytes() != gif.read_bytes(), 'style changed nothing'

    listing = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'render.py'), '--list-styles'],
                             check=True, capture_output=True, text=True).stdout
    assert all(k in listing for k in render.STYLES), listing
    print('OK: config valid, bad config and bad style caught, default output unchanged, one scene rendered plain and styled.')


if __name__ == '__main__':
    main()
