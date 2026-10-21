"""Speech resilience for the external MoneyPrinter process, owned by Shaniu."""
import asyncio
import math
import os
from pathlib import Path
import subprocess
import threading

from moneyprinter_compat import LegacySubMaker


class SpeechUnavailable(RuntimeError):
    failure_reason = 'audio_fallback_failed'


class OnlineSpeechUnavailable(SpeechUnavailable):
    failure_reason = 'audio_online_failed'


async def online(text, voice, rate, path):
    import edge_tts
    maker = LegacySubMaker()
    async def collect():
        communicate = edge_tts.Communicate(text, voice, rate=f'{round((rate-1)*100):+d}%',
                                          boundary='WordBoundary', connect_timeout=5, receive_timeout=10)
        with path.open('wb') as audio:
            async for chunk in communicate.stream():
                if chunk['type'] == 'audio':
                    audio.write(chunk['data'])
                elif chunk['type'] == 'WordBoundary':
                    maker.create_sub((chunk['offset'], chunk['duration']), chunk['text'])
    await asyncio.wait_for(collect(), timeout=120)
    if not maker.subs or not path.stat().st_size:
        raise RuntimeError('Empty online speech')
    maker.shaniu_provider = 'edge'
    return maker


def local(text, rate, path):
    from speech import windows, duration, captions
    import imageio_ffmpeg
    wav = path.with_suffix('.fallback.wav')
    try:
        boundaries, _ = windows(text, wav, 'cool', threading.Event(),
                                rate=max(-10, min(10, round(10*math.log2(rate)))))
        length = duration(wav)
        if length <= 0 or not boundaries:
            raise RuntimeError('Local speech has no timing data')
        cues, alignment = captions(text, boundaries, length)
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', str(wav),
                        '-c:a', 'libmp3lame', '-ar', '24000', str(path)], check=True,
                       capture_output=True, timeout=60,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if not path.stat().st_size:
            raise RuntimeError('Empty local speech')
        maker = LegacySubMaker()
        for cue in cues:
            maker.create_sub((round(cue['start']*10_000_000), round((cue['end']-cue['start'])*10_000_000)), cue['text'])
        # Duration is derived from the waveform, not the final progress event.
        maker.offset[-1] = (maker.offset[-1][0], round(length*10_000_000))
        maker.shaniu_cues = cues
        maker.shaniu_provider = 'windows'
        maker.shaniu_alignment = alignment
        return maker
    finally:
        wav.unlink(missing_ok=True)
        wav.with_suffix('.boundaries.json').unlink(missing_ok=True)


def synthesize(text, voice_name, voice_rate, voice_file):
    path = Path(voice_file)
    temporary = path.with_name(path.stem+'.pending.mp3')
    provider = os.getenv('SHANIU_MPT_TTS_PROVIDER', 'edge').lower()
    fallback = os.getenv('SHANIU_MPT_TTS_FALLBACK', 'true').lower() == 'true'
    if provider not in {'edge', 'windows'}:
        raise ValueError('SHANIU_MPT_TTS_PROVIDER must be edge or windows')
    try:
        if provider == 'edge':
            try:
                maker = asyncio.run(online(text, voice_name, voice_rate, temporary))
            except Exception:
                if not fallback or os.name != 'nt' or not voice_name.startswith('zh-CN-'):
                    raise OnlineSpeechUnavailable('Online speech unavailable; local fallback disabled or unsupported') from None
                maker = local(text, voice_rate, temporary)
                maker.shaniu_warning = '在线配音不可用，已使用 Windows 本地中文语音，音色与在线配音不同。'
        else:
            if os.name != 'nt' or not voice_name.startswith('zh-CN-'):
                raise SpeechUnavailable('Local Chinese speech requires Windows and a zh-CN voice')
            maker = local(text, voice_rate, temporary)
        temporary.replace(path)
        return maker
    except Exception as error:
        # Never leave an empty/partial MP3 that can be mistaken for a result.
        if path.exists() and path.stat().st_size == 0:
            path.unlink()
        if isinstance(error, SpeechUnavailable):
            raise
        raise SpeechUnavailable('Speech synthesis unavailable; check online speech and installed Chinese desktop voices') from None
    finally:
        temporary.unlink(missing_ok=True)


def install(voice):
    original_subtitle = voice.create_subtitle
    def create_subtitle(sub_maker, text, subtitle_file):
        if hasattr(sub_maker, 'shaniu_cues'):
            from speech import timestamp
            blocks = [f'{i}\n{timestamp(c["start"])} --> {timestamp(c["end"])}\n{c["text"]}\n'
                      for i, c in enumerate(sub_maker.shaniu_cues, 1)]
            Path(subtitle_file).write_text('\n'.join(blocks), encoding='utf-8')
        else:
            original_subtitle(sub_maker=sub_maker, text=text, subtitle_file=subtitle_file)
    # Other upstream voice providers retain their existing dispatch paths.
    voice.azure_tts_v1 = synthesize
    voice.create_subtitle = create_subtitle
