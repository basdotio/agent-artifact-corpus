#!/usr/bin/env python3
"""timeline-video: check, price, render and review a timeline-scripted AI video.

  check  <script.md>                      parse the six blocks, check the clock, print the beats
  models [--model ID]                     OpenRouter video models: durations, resolutions, aspects, audio, price
  render <script.md> -o DIR [options]     price, submit to OpenRouter, poll, download MP4 + JSON sidecar
  sheet  <video.mp4> <script.md>          one frame per beat in a grid (needs ffmpeg)

Python 3.8+ standard library. The OpenRouter key comes from --key-file or OPENROUTER_API_KEY and is never printed
or written anywhere. Exit: 0 done, 1 OpenRouter refused / the job failed, 2 bad script or parameter, 4 no key.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = 'https://openrouter.ai/api/v1'
BLOCKS = ['CHARACTER', 'STYLE', 'AUDIO', 'TIMELINE', 'CAMERA RULES', 'NEGATIVE']
DEFAULTS = {'model': 'bytedance/seedance-2.5', 'duration': 30, 'aspect': '16:9', 'resolution': '720p'}
UA = 'timeline-video/1.0 (+https://github.com/askdestava/claude-skills)'
DASH = r'\s*[–—-]\s*'
WINDOW = re.compile(r'^\s*(\d+(?:\.\d+)?)' + DASH + r'(\d+(?:\.\d+)?)\s*s\b' + DASH + r'(.+)$')
CUE = re.compile(r'(\d+(?:\.\d+)?)(?:' + DASH + r'(\d+(?:\.\d+)?))?\s*s\s*:')
DIMENSIONS = {  # width × height per resolution and aspect, for the token estimate only
    '480p': {'16:9': (854, 480), '9:16': (480, 854), '1:1': (480, 480), '4:3': (640, 480), '3:4': (480, 640), '21:9': (1120, 480)},
    '720p': {'16:9': (1280, 720), '9:16': (720, 1280), '1:1': (720, 720), '4:3': (960, 720), '3:4': (720, 960), '21:9': (1680, 720)},
    '1080p': {'16:9': (1920, 1080), '9:16': (1080, 1920), '1:1': (1080, 1080), '4:3': (1440, 1080), '3:4': (1080, 1440), '21:9': (2520, 1080)},
}


class Fail(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


# ---------- the script ----------

def read_script(path):
    """→ (front matter dict, prompt text, {block: text}). The prompt is everything after the front matter."""
    try:
        text = open(path, encoding='utf-8').read().replace('\r\n', '\n')
    except OSError as e:
        raise Fail(2, f'cannot read {path}: {e.strerror}')
    meta = {}
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ':' in line and not line.lstrip().startswith('#'):
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip()
        text = text[m.end():]
    prompt = text.strip()
    blocks = {}
    marks = list(re.finditer(r'^\[(' + '|'.join(re.escape(b) for b in BLOCKS) + r')\]', prompt, re.M))
    for i, mk in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(prompt)
        blocks[mk.group(1)] = prompt[mk.end():end].strip()
    return meta, prompt, blocks


def check_script(meta, prompt, blocks, duration):
    """→ (beats, cues, problems, warnings). beats = [(start, end, text)]."""
    problems, warnings = [], []
    for b in BLOCKS:
        if b not in blocks:
            problems.append(f'missing block [{b}]')
        elif not blocks[b]:
            problems.append(f'block [{b}] is empty')
    beats = []
    for line in blocks.get('TIMELINE', '').splitlines():
        m = WINDOW.match(line)
        if m:
            beats.append((float(m.group(1)), float(m.group(2)), m.group(3).strip()))
        elif line.strip():
            if beats:  # a wrapped line continues the beat above it
                s, e, t = beats[-1]
                beats[-1] = (s, e, t + ' ' + line.strip())
            else:
                problems.append(f'timeline line without a window: {line.strip()[:60]}')
    if 'TIMELINE' in blocks and not beats:
        problems.append('the timeline has no "a–b s — …" windows')
    t = 0.0
    for s, e, txt in beats:
        if abs(s - t) > 0.01:
            problems.append(f'the clock jumps from {t:g}s to {s:g}s (a gap or an overlap)')
        if e <= s:
            problems.append(f'window {s:g}–{e:g}s ends before it starts')
        if len(txt.split()) < 4:
            warnings.append(f'{s:g}–{e:g}s says little ("{txt}"): a vague window is where a long take drifts')
        t = e
    if beats and abs(t - duration) > 0.01:
        problems.append(f'the timeline ends at {t:g}s but the duration is {duration:g}s')
    audio = blocks.get('AUDIO', '')
    marks = list(CUE.finditer(audio))
    cues = []
    for i, m in enumerate(marks):
        a = float(m.group(1))
        b = float(m.group(2)) if m.group(2) else None
        cues.append((a, b))
        if (b or a) > duration:
            problems.append(f'an audio cue at {m.group(0)} is past the {duration:g}s end')
        if b is None:
            continue
        said = audio[m.end():marks[i + 1].start() if i + 1 < len(marks) else len(audio)]
        q = re.search(r'["“]([^"”]+)["”]', said)
        if q:
            words = len([w for w in q.group(1).split() if re.search(r'\w', w)])
            fit = int((b - a) * 2.5 + 0.5)
            if words > fit + 2:
                warnings.append(f'{a:g}–{b:g}s voice line has {words} words; about {fit} fit at a natural pace')
    lock = blocks.get('CHARACTER', '')
    if lock and not re.search(r'identical|unchanged|the same', lock, re.I):
        warnings.append('[CHARACTER] has no lock line ("Keep … identical for all N seconds")')
    neg = blocks.get('NEGATIVE', '').lower()
    for word in ('text', 'logo'):
        if neg and word not in neg:
            warnings.append(f'[NEGATIVE] does not forbid {word}s: models paint them on props')
    if len(prompt) > 4500:
        warnings.append(f'the prompt is {len(prompt)} characters; long prompts may be truncated by the provider')
    return beats, cues, problems, warnings


def params_for(meta, args):
    p = dict(DEFAULTS)
    for k in ('model', 'aspect', 'resolution'):
        if meta.get(k):
            p[k] = meta[k]
    if meta.get('duration'):
        p['duration'] = float(meta['duration'])
    for k in ('model', 'duration', 'aspect', 'resolution'):
        v = getattr(args, k, None)
        if v is not None:
            p[k] = v
    p['duration'] = float(p['duration'])
    return p


# ---------- OpenRouter ----------

def read_key(key_file):
    if key_file:
        try:
            key = open(os.path.expanduser(key_file), encoding='utf-8').read().strip()
        except OSError as e:
            raise Fail(4, f'cannot read the key file: {e.strerror}')
    else:
        key = os.environ.get('OPENROUTER_API_KEY', '').strip()
    if not key:
        raise Fail(4, 'no OpenRouter key: pass --key-file or set OPENROUTER_API_KEY')
    return key


def call(method, url, key=None, body=None, raw=False, timeout=120):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header('User-Agent', UA)
    if body is not None:
        req.add_header('Content-Type', 'application/json')
    if key:
        req.add_unredirected_header('Authorization', f'Bearer {key}')  # never follows a redirect to another host
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            data = res.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'replace')[:600]
        raise Fail(2 if e.code == 400 else 1, f'OpenRouter answered HTTP {e.code}: {detail}')
    except urllib.error.URLError as e:
        raise Fail(1, f'could not reach OpenRouter: {e.reason}')
    return data if raw else json.loads(data.decode('utf-8'))


def model_info(model_id):
    data = call('GET', f'{API}/videos/models')['data']
    for m in data:
        if m['id'] == model_id:
            return m
    raise Fail(2, f'{model_id} is not an OpenRouter video model (see: models)')


def price(m, p, audio):
    """→ (dollars or None, how it was worked out)."""
    skus = m.get('pricing_skus') or {}
    sec, res = p['duration'], p['resolution']
    if 'video_tokens' in skus:
        w, h = DIMENSIONS.get(res, {}).get(p['aspect'], (None, None))
        if not w:
            return None, 'priced per video token; no size known for this resolution/aspect'
        rate = float(skus.get(f'video_tokens_{res}', skus['video_tokens']))
        tokens = w * h * 24 * sec / 1024
        return tokens * rate, f'ESTIMATE: {int(tokens):,} video tokens (≈ {w}×{h} × 24 fps × {sec:g}s ÷ 1024) × ${rate}'
    for key in (f'duration_seconds_with_audio_{res}' if audio else f'duration_seconds_without_audio_{res}',
                'duration_seconds_with_audio' if audio else 'duration_seconds_without_audio',
                f'duration_seconds_{res}', 'duration_seconds'):
        if key in skus:
            return float(skus[key]) * sec, f'{sec:g}s × ${skus[key]}/s ({key})'
    for key in (f'cents_per_video_output_second_{res}', f'cents_per_second_output_{res}', 'cents_per_second_output'):
        if key in skus:
            return float(skus[key]) / 100 * sec, f'{sec:g}s × {skus[key]}¢/s ({key})'
    return None, 'no matching price in the model listing'


def validate(m, p, audio):
    def need(name, value, allowed):
        if allowed and value not in allowed:
            raise Fail(2, f'{m["id"]} offers {name} {allowed}, not {value}')
    dur = int(p['duration']) if float(p['duration']).is_integer() else p['duration']
    need('durations', dur, m.get('supported_durations'))
    need('resolutions', p['resolution'], m.get('supported_resolutions'))
    need('aspect ratios', p['aspect'], m.get('supported_aspect_ratios'))
    if audio and m.get('generate_audio') is False:
        print(f'note: {m["id"]} makes no audio; rendering silent', file=sys.stderr)
        return False
    return audio


# ---------- commands ----------

def cmd_check(args):
    meta, prompt, blocks = read_script(args.script)
    p = params_for(meta, args)
    beats, cues, problems, warnings = check_script(meta, prompt, blocks, p['duration'])
    print(f'{os.path.basename(args.script)}: {p["duration"]:g}s {p["aspect"]} {p["resolution"]} on {p["model"]} · '
          f'{len(prompt):,} characters · {len(beats)} beats · {len(cues)} audio cues')
    for s, e, t in beats:
        print(f'  {s:5.1f}–{e:5.1f}s  {t[:110]}{"…" if len(t) > 110 else ""}')
    for w in warnings:
        print(f'warning: {w}')
    for pr in problems:
        print(f'PROBLEM: {pr}')
    if problems:
        raise Fail(2, f'{len(problems)} problem(s); nothing sent')
    return meta, prompt, p, beats


def cmd_models(args):
    data = call('GET', f'{API}/videos/models')['data']
    for m in data:
        if args.model and m['id'] != args.model:
            continue
        print(f"{m['id']}\n  durations {m.get('supported_durations')} · resolutions {m.get('supported_resolutions')} · "
              f"aspects {m.get('supported_aspect_ratios')} · audio {m.get('generate_audio')} · "
              f"frames {m.get('supported_frame_images')}\n  price {json.dumps(m.get('pricing_skus'))}")


def cmd_render(args):
    meta, prompt, p, beats = cmd_check(args)
    audio = not args.no_audio
    m = model_info(p['model'])
    audio = validate(m, p, audio)
    dollars, how = price(m, p, audio)
    print(f'price: {"$%.2f" % dollars if dollars is not None else "unknown"} — {how}')
    if args.dry_run:
        print('--dry-run: nothing sent')
        return
    key = read_key(args.key_file)
    body = {'model': p['model'], 'prompt': prompt, 'duration': int(p['duration']) if float(p['duration']).is_integer() else p['duration'],
            'resolution': p['resolution'], 'aspect_ratio': p['aspect'], 'generate_audio': audio}
    if args.seed is not None:
        body['seed'] = args.seed
    os.makedirs(args.output, exist_ok=True)
    name = os.path.splitext(os.path.basename(args.script))[0]
    started = time.time()
    job = call('POST', f'{API}/videos', key, body)
    job_id = job.get('id')
    poll = job.get('polling_url') or f'{API}/videos/{job_id}'
    print(f'submitted {job_id}; polling every {args.poll}s (a 30-second film usually takes a few minutes)', flush=True)
    while True:
        time.sleep(args.poll)
        st = call('GET', poll, key)
        state = st.get('status')
        print(f'  {int(time.time() - started)}s: {state}', flush=True)
        if state == 'completed':
            break
        if state in ('failed', 'cancelled', 'expired'):
            raise Fail(1, f'the job ended {state}: {st.get("error") or "no reason given"}')
        if time.time() - started > args.timeout * 60:
            raise Fail(1, f'still {state} after {args.timeout} minutes; job {job_id} can be fetched later')
    url = (st.get('unsigned_urls') or [f'{API}/videos/{job_id}/content?index=0'])[0]
    video = call('GET', url, key, raw=True, timeout=600)
    out = os.path.join(args.output, f'{name}.mp4')
    with open(out + '.part', 'wb') as f:
        f.write(video)
    os.replace(out + '.part', out)
    sidecar = {
        'script': os.path.abspath(args.script), 'model': p['model'], 'params': {k: v for k, v in body.items() if k != 'prompt'},
        'prompt_sha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(), 'prompt': prompt,
        'job_id': job_id, 'generation_id': st.get('generation_id'), 'usage': st.get('usage'),
        'price_before': {'dollars': dollars, 'how': how},
        'submitted_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(started)), 'seconds_to_complete': int(time.time() - started),
    }
    with open(os.path.join(args.output, f'{name}.json'), 'w', encoding='utf-8') as f:
        json.dump(sidecar, f, indent=1, ensure_ascii=False)
    cost = (st.get('usage') or {}).get('cost')
    print(f'saved {out} ({len(video) / 1e6:.1f} MB) · charged {"$%s" % cost if cost is not None else "see usage"} · sidecar {name}.json')


def cmd_sheet(args):
    if not shutil.which('ffmpeg'):
        raise Fail(2, 'sheet needs ffmpeg')
    meta, prompt, blocks = read_script(args.script)
    p = params_for(meta, args)
    beats, _, problems, _ = check_script(meta, prompt, blocks, p['duration'])
    if not beats:
        raise Fail(2, 'no beats to sample')
    tmp = os.path.splitext(args.video)[0] + '_beats'
    os.makedirs(tmp, exist_ok=True)
    frames = []
    for i, (s, e, _) in enumerate(beats):
        f = os.path.join(tmp, f'{i:02d}_{(s + e) / 2:05.1f}s.jpg')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{(s + e) / 2:.2f}', '-i', args.video, '-frames:v', '1',
                        '-vf', f"scale=640:-2,drawtext=text='{s:g}–{e:g}s':x=12:y=12:fontsize=26:fontcolor=white:box=1:boxcolor=black@0.55",
                        f], check=True)
        frames.append(f)
    cols = 4 if len(frames) > 4 else len(frames)
    rows = (len(frames) + cols - 1) // cols
    out = tmp + '.jpg'
    inputs = []
    for f in frames:
        inputs += ['-i', f]
    layout = '|'.join(f'{(i % cols) * 640}_{(i // cols) * 360}' for i in range(len(frames)))
    scaled = ''.join(f'[{i}:v]scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2[v{i}];' for i in range(len(frames)))
    stack = ''.join(f'[v{i}]' for i in range(len(frames)))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex',
                    f'{scaled}{stack}xstack=inputs={len(frames)}:layout={layout}:fill=black', out], check=True)
    print(f'saved {out} ({len(frames)} beats, {cols}×{rows}); frames in {tmp}/')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('check', 'render', 'sheet'):
        sp = sub.add_parser(name)
        if name == 'sheet':
            sp.add_argument('video')
        sp.add_argument('script')
        sp.add_argument('--model')
        sp.add_argument('--duration', type=float)
        sp.add_argument('--aspect')
        sp.add_argument('--resolution')
        if name == 'render':
            sp.add_argument('-o', '--output', default='.')
            sp.add_argument('--key-file')
            sp.add_argument('--seed', type=int)
            sp.add_argument('--no-audio', action='store_true')
            sp.add_argument('--dry-run', action='store_true')
            sp.add_argument('--poll', type=int, default=20, help='seconds between status checks')
            sp.add_argument('--timeout', type=int, default=30, help='minutes before giving up waiting')
    sm = sub.add_parser('models')
    sm.add_argument('--model')
    args = ap.parse_args()
    try:
        {'check': cmd_check, 'models': cmd_models, 'render': cmd_render, 'sheet': cmd_sheet}[args.cmd](args)
    except Fail as e:
        print(f'error: {e}', file=sys.stderr)
        sys.exit(e.code)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == '__main__':
    main()
