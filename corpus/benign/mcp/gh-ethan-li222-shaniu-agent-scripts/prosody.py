"""Conservative phrasing: preserve native intonation, extend short real pauses."""
from array import array
from bisect import bisect_left, bisect_right
import math
from html import unescape
import re
import sys
import wave


PROFILES = {
    'cool': dict(rate='+10%', pitch='-2Hz', pause=1.0),
    'happy': dict(rate='+24%', pitch='+4Hz', pause=.85),
    'gentle': dict(rate='+4%', pitch='-1Hz', pause=1.1),
    'shy': dict(rate='+6%', pitch='+2Hz', pause=1.15),
}


def profile(emotion):
    return PROFILES.get(emotion, PROFILES['cool'])


def pause_seconds(punctuation, emotion):
    if '\n' in punctuation:
        value = .38
    elif re.search(r'[…]|\.{3,}', punctuation):
        value = .42
    elif re.search(r'[！？!?]', punctuation):
        value = .30
    elif re.search(r'[。；;]', punctuation):
        value = .26
    elif re.search(r'[，,：:、]', punctuation):
        value = .12
    else:
        return 0
    return value * profile(emotion)['pause']


def punctuation_boundaries(text, boundaries):
    """Map complete real word events to punctuation without changing the script."""
    plain = ''.join(c for c in text if c.isalnum()).casefold()
    positions = [i for i, c in enumerate(text) if c.isalnum()]
    if len(plain) != len(positions):
        return []
    aligned, cursor = [], 0
    for boundary in boundaries:
        token = ''.join(c for c in unescape(boundary.get('text', '')) if c.isalnum()).casefold()
        if not token:
            continue
        if not plain.startswith(token, cursor):
            return []
        start, end = float(boundary['start']), float(boundary['end'])
        if not math.isfinite(start) or not math.isfinite(end) or end <= start or (aligned and start < aligned[-1]['start']):
            return []
        aligned.append(dict(start=start, end=end, last=positions[cursor+len(token)-1]))
        cursor += len(token)
    if cursor != len(plain):
        return []
    result = []
    for index, word in enumerate(aligned):
        next_char = word['last']+1
        punctuation = re.match(r'[^\w\u4e00-\u9fff]*', text[next_char:]).group()
        after = next_char+len(punctuation)
        if text[word['last']].isdigit() and after < len(text) and text[after].isdigit() and punctuation in {',', '，', ':', '：'}:
            punctuation = ''
        position = aligned[index+1]['start'] if index+1 < len(aligned) else None
        result.append(dict(position=position, earliest=word['start'], punctuation=punctuation))
    return result


def natural_pauses(path, text, boundaries, emotion, stop, include_terminal=True):
    """Insert only missing silence at native boundaries; shift caption events too.

    Never remove audio or cut a voiced boundary. Unaligned input stays unchanged.
    """
    markers = punctuation_boundaries(text, boundaries)
    if not markers:
        return boundaries
    with wave.open(str(path), 'rb') as audio:
        params = audio.getparams()
        if params.nchannels != 1 or params.sampwidth != 2 or params.comptype != 'NONE':
            return boundaries
        samples = array('h', audio.readframes(params.nframes))
    if sys.byteorder != 'little':
        return boundaries
    rate = params.framerate
    step = max(1, int(rate*.005))
    insertions = []
    for marker in markers:
        if stop.is_set():
            return boundaries
        if marker['position'] is None and not include_terminal:
            continue
        desired = pause_seconds(marker['punctuation'], emotion)
        if not desired:
            continue
        position = len(samples) if marker['position'] is None else max(0, min(len(samples), round(marker['position']*rate)))
        earliest = max(0, round(marker['earliest']*rate), position-int(rate*.65))
        cursor = position
        while cursor-step >= earliest:
            chunk = samples[cursor-step:cursor]
            rms = math.sqrt(sum(value*value for value in chunk)/len(chunk))
            if rms > 120:
                break
            cursor -= step
        silence = position-cursor
        # Protect phonemes if a TTS timestamp lies inside audible speech.
        if silence < step*2:
            continue
        missing = max(0, round(desired*rate)-silence)
        if missing:
            insertions.append((position, missing))
    if not insertions:
        return boundaries
    pieces, previous = [], 0
    for position, count in insertions:
        pieces.append(samples[previous:position].tobytes())
        pieces.append(bytes(count*2))
        previous = position
    pieces.append(samples[previous:].tobytes())
    with wave.open(str(path), 'wb') as audio:
        audio.setparams(params)
        audio.writeframes(b''.join(pieces))
    positions = [position for position, _ in insertions]
    cumulative = [0]
    for _, count in insertions:
        cumulative.append(cumulative[-1]+count/rate)
    return [dict(event, start=event['start']+cumulative[bisect_right(positions, round(event['start']*rate))], end=event['end']+cumulative[bisect_left(positions, round(event['end']*rate))]) for event in boundaries]
