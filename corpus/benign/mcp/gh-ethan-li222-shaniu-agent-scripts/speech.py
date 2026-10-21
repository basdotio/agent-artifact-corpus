"""Speech + timed captions, informed by MoneyPrinterTurbo's boundary-first design.

No dependency on that checkout. Boundary metadata is aligned to the original text;
when alignment fails we disclose sentence-level timing instead of inventing words.
"""
import asyncio
from dataclasses import dataclass
from html import unescape
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import wave
from array import array
from prosody import natural_pauses, profile

ROOT = Path(__file__).resolve().parents[1]


class SpeechCancelled(Exception):
    pass


@dataclass
class SpeechResult:
    path: Path
    cues: list
    provider: str
    voice: str
    alignment: str
    warning: str = ''
    natural: bool = True
    added_pause_seconds: float = 0.0


def duration(path):
    with wave.open(str(path), 'rb') as audio:
        return audio.getnframes()/audio.getframerate()


def captions(text, boundaries, length):
    plain = ''.join(c for c in text if c.isalnum()).casefold()
    positions = [i for i, c in enumerate(text) if c.isalnum()]
    # Avoid ambiguous expansions such as casefold(ß): disclose fallback.
    if len(plain) != len(positions):
        boundaries = []
    cursor = 0
    aligned = []
    for boundary in boundaries:
        token = ''.join(c for c in unescape(boundary.get('text', '')) if c.isalnum()).casefold()
        if not token:
            continue
        index = plain.find(token, cursor)
        if index != cursor:
            aligned = []
            break
        start = max(0, min(length, float(boundary['start'])))
        end = max(start, min(length, float(boundary.get('end', length))))
        if not math.isfinite(float(boundary['start'])) or not math.isfinite(float(boundary.get('end', length))) or end <= start:
            aligned = []
            break
        if aligned and start < aligned[-1]['start']:
            aligned = []
            break
        aligned.append(dict(start=start, end=end, a=positions[index], b=positions[index+len(token)-1]+1))
        cursor = index+len(token)
    if not aligned or cursor != len(plain):
        return [dict(start=0.0, end=round(length, 3), text=text)], 'sentence_fallback'
    cues = []
    for i, word in enumerate(aligned[:-1]):
        word['end'] = min(word['end'], aligned[i+1]['start'])
    group = None
    for i, word in enumerate(aligned):
        a = word['a'] if i else 0
        b = aligned[i+1]['a'] if i+1 < len(aligned) else len(text)
        part = text[a:b]
        if group and (len(group['text'])+len(part) > 22 or word['start']-group['end'] > .6):
            cues.append(group)
            group = None
        if group is None:
            group = dict(start=round(word['start'], 3), end=round(word['end'], 3), text=part)
        else:
            group['text'] += part
            group['end'] = round(word['end'], 3)
        if re.search(r'[。！？!?；;\n]', part):
            cues.append(group)
            group = None
    if group:
        cues.append(group)
    if any(c['end'] <= c['start'] for c in cues):
        return [dict(start=0.0, end=round(length, 3), text=text)], 'sentence_fallback'
    return cues, 'word_boundary'


def timestamp(value, separator=','):
    milliseconds = max(0, int(round(value*1000)))
    seconds, ms = divmod(milliseconds, 1000)
    minutes, sec = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f'{hours:02}:{minute:02}:{sec:02}{separator}{ms:03}'


def write_subtitles(base, cues):
    blocks = [f'{i}\n{timestamp(c["start"])} --> {timestamp(c["end"])}\n{c["text"]}\n' for i, c in enumerate(cues, 1)]
    base.with_suffix('.srt').write_text('\n'.join(blocks), encoding='utf-8')
    vtt = [f'{timestamp(c["start"], ".")} --> {timestamp(c["end"], ".")}\n{c["text"]}\n' for c in cues]
    base.with_suffix('.vtt').write_text('WEBVTT\n\n'+'\n'.join(vtt), encoding='utf-8')


def windows_boundaries(events, length):
    events = sorted(events, key=lambda event: (event['start'], event.get('position', 0)))
    unique = []
    seen = set()
    for event in events:
        key = (event.get('position'), event.get('count'))
        # SAPI can emit several progress events for a single expanded date or
        # number. They refer to the same source span, not repeated script text.
        if key in seen:
            continue
        seen.add(key)
        unique.append(dict(event))
    for i, event in enumerate(unique):
        event['end'] = unique[i+1]['start'] if i+1 < len(unique) else length
    return unique


def windows(text, path, emotion, stop, rate=None):
    timings = path.with_suffix('.boundaries.json')
    payload = dict(text=text, output=str(path), timings=str(timings), rate=rate if rate is not None else {'cool': 1, 'happy': 2, 'gentle': 0, 'shy': 0}.get(emotion, 1))
    process = subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT/'scripts/synthesize_windows.ps1')],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        process.stdin.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        process.stdin.close()
        deadline = time.monotonic()+60
        while process.poll() is None:
            if stop.wait(.02):
                raise SpeechCancelled()
            if time.monotonic() > deadline:
                raise RuntimeError('Local speech timed out')
        if process.returncode:
            raise RuntimeError('Local Chinese speech failed')
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
    length = duration(path)
    events = json.loads(timings.read_text(encoding='utf-8')) if timings.exists() else []
    return windows_boundaries(events, length), 'Microsoft zh-CN desktop'


async def edge(text, path, emotion, voice, stop, natural=True):
    import edge_tts
    import imageio_ffmpeg
    mp3 = path.with_suffix('.mp3')
    boundaries = []
    style = profile(emotion)
    rate = style['rate']
    async def collect():
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=style['pitch'] if natural else '+0Hz', boundary='WordBoundary', connect_timeout=5, receive_timeout=8)
        with mp3.open('wb') as audio:
            async for chunk in communicate.stream():
                if stop.is_set():
                    raise SpeechCancelled()
                if chunk['type'] == 'audio':
                    audio.write(chunk['data'])
                elif chunk['type'] == 'WordBoundary':
                    boundaries.append(dict(text=chunk['text'], start=chunk['offset']/10_000_000, end=(chunk['offset']+chunk['duration'])/10_000_000))
    task = asyncio.create_task(collect())
    started = time.monotonic()
    try:
        while not task.done():
            if stop.is_set():
                raise SpeechCancelled()
            if time.monotonic()-started > 15:
                raise RuntimeError('Online speech timed out')
            await asyncio.sleep(.02)
        await task
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    if stop.is_set():
        raise SpeechCancelled()
    # Decode once; this exact waveform feeds both Wav2Lip and playback.
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', str(mp3), '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', str(path)],
        check=True, capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    return boundaries, voice


def synthesize(text, path, emotion='cool', config=None, stop=None):
    config = config or {}
    stop = stop or threading.Event()
    provider = config.get('provider', 'windows')
    voice = config.get('voice', 'zh-CN-XiaoxiaoNeural')
    warning = ''
    if stop.is_set():
        raise SpeechCancelled()
    if provider == 'edge':
        try:
            boundaries, voice = asyncio.run(edge(text, path, emotion, voice, stop, natural=config.get('natural', True)))
        except SpeechCancelled:
            raise
        except Exception:
            if not config.get('fallback', True):
                raise RuntimeError('Edge TTS unavailable; enable local fallback or check network') from None
            warning = 'Edge TTS 不可用，本轮已切换本机中文语音'
            provider = 'windows'
            boundaries, voice = windows(text, path, emotion, stop)
    elif provider == 'windows':
        boundaries, voice = windows(text, path, emotion, stop)
    else:
        raise RuntimeError('Unknown speech provider')
    if stop.is_set():
        raise SpeechCancelled()
    initial_duration = duration(path)
    if config.get('natural', True) and path.is_file():
        boundaries = natural_pauses(path, text, boundaries, emotion, stop, include_terminal=config.get('terminal_pause', True))
    if stop.is_set():
        raise SpeechCancelled()
    length = duration(path)
    cues, alignment = captions(text, boundaries, length)
    return SpeechResult(path, cues, provider, voice, alignment, warning, config.get('natural', True), round(max(0, length-initial_duration), 3))


def trim_realtime_padding(result, stop):
    """Remove only excessive quiet padding around separately synthesized chunks."""
    with wave.open(str(result.path), 'rb') as audio:
        params = audio.getparams()
        if params.nchannels != 1 or params.sampwidth != 2:
            return
        samples = array('h', audio.readframes(params.nframes))
    step = max(1, round(params.framerate*.005))
    def quiet(start):
        values = samples[start:start+step]
        return bool(values) and sum(v*v for v in values)/len(values) < 120**2
    first, last = 0, len(samples)
    while first+step < last and quiet(first):
        first += step
    while last-step > first and quiet(last-step):
        last -= step
    if last-first < step or stop.is_set():
        return
    start = max(0, first-round(params.framerate*.03))
    end = min(len(samples), last+round(params.framerate*.12))
    if start == 0 and end == len(samples):
        return
    with wave.open(str(result.path), 'wb') as audio:
        audio.setparams(params)
        audio.writeframes(samples[start:end].tobytes())
    offset, length = start/params.framerate, (end-start)/params.framerate
    result.cues = [dict(cue, start=max(0, cue['start']-offset), end=min(length, cue['end']-offset)) for cue in result.cues if cue['end']>offset and cue['start']<offset+length]


def draw_caption(image, cues, second, bottom_margin=None):
    from PIL import Image, ImageDraw, ImageFont
    text = next((c['text'] for c in cues if c['start'] <= second < c['end']), '')
    if not text:
        return image
    font = caption_font(max(22, int(image.shape[1]/13)))
    picture = Image.fromarray(image[:, :, ::-1])
    draw = ImageDraw.Draw(picture, 'RGBA')
    lines = []
    current = ''
    for char in text.strip():
        if current and (char == '\n' or draw.textlength(current+char, font=font) > image.shape[1]-24):
            lines.append(current)
            current = ''
        if char != '\n':
            current += char
    if current:
        lines.append(current)
    # At most the viewport's height; unusually long fallback text is handled
    # as a sentence-level cue, with explicit alignment status in the UI.
    line_height = font.size+7
    bottom = image.shape[0]-(max(80, int(image.shape[0]*.25)) if bottom_margin is None else max(0, min(image.shape[0]-1, int(bottom_margin))))
    top = max(0, bottom-len(lines)*line_height-12)
    draw.rounded_rectangle((6, top, image.shape[1]-6, bottom), radius=8, fill=(0, 0, 0, 175))
    for i, line in enumerate(lines):
        width = draw.textlength(line, font=font)
        draw.text(((image.shape[1]-width)/2, top+5+i*line_height), line, font=font, fill='white', stroke_width=1, stroke_fill=(0, 0, 0, 255))
    import numpy as np
    return np.asarray(picture)[:, :, ::-1].copy()


from functools import lru_cache
@lru_cache(maxsize=8)
def caption_font(size):
    from PIL import ImageFont
    font = Path(os.getenv('WINDIR', 'C:/Windows'))/'Fonts/msyh.ttc'
    if not font.is_file():
        raise RuntimeError('Chinese subtitle font unavailable')
    return ImageFont.truetype(str(font), size)
