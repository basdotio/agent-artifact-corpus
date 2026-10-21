"""Opt-in real local render with synthetic fixtures; no model, stock or TTS APIs.

Requires requirements-moneyprinter.txt. --subtitles also needs an installed CJK
font. Uses the actual bundled API/task/MoviePy/FFmpeg pipeline, temporary private
config, two-second generated media, and a deliberately small render resolution.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subtitles', action='store_true')
    args = parser.parse_args()
    engine = ROOT / 'vendor/moneyprinter'
    sys.path.insert(0, str(engine))
    from loguru import logger
    logger.remove()
    import imageio_ffmpeg
    from fastapi.testclient import TestClient
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    with tempfile.TemporaryDirectory(prefix='shaniu-engine-check-') as temp:
        work = Path(temp)
        os.environ.update(SHANIU_MPT_CONFIG=str(work / 'config.toml'),
                          SHANIU_MPT_STORAGE=str(work / 'storage'),
                          SHANIU_MPT_LLM_PROVIDER='upstream')
        os.chdir(engine)
        import moneyprinter_host as host
        logger.remove()  # Upstream const.py installs a sink during import.
        import app
        assert Path(app.__file__).resolve().is_relative_to(engine)
        assert Path(host.config.config_file).resolve() == work / 'config.toml'

        def command(*arguments):
            subprocess.run([ffmpeg, '-y', '-loglevel', 'error', *map(str, arguments)],
                           check=True, capture_output=True, timeout=60)

        clip = work / 'test-color.mp4'
        command('-f', 'lavfi', '-i', 'color=c=blue:s=320x180:r=24:d=2',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip)
        from moneyprinter_compat import LegacySubMaker

        def synthetic_tts(text, voice_name, voice_rate, voice_file):
            command('-f', 'lavfi', '-i', 'sine=frequency=440:duration=2',
                    '-c:a', 'libmp3lame', '-ar', '24000', voice_file)
            maker = LegacySubMaker()
            maker.create_sub((0, 20_000_000), text)
            return maker

        def unexpected_online(*args, **kwargs):
            raise AssertionError('The offline check must not call model or stock APIs')

        host.task.voice.tts = synthetic_tts
        host.task.llm.generate_script = unexpected_online
        host.task.llm.generate_terms = unexpected_online
        host.task.material.download_videos = unexpected_online
        from app.models.schema import VideoAspect
        VideoAspect.to_resolution = lambda self: (320, 180)

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), TestClient(host.app) as client:
            assert client.get('/shaniu/health').json()['wrapper'] == 'shaniu'
            routes = client.get('/openapi.json').json()['paths']
            assert {'/api/v1/videos', '/api/v1/audio', '/api/v1/subtitle', '/api/v1/tasks/{task_id}'} <= set(routes)
            response = client.post('/api/v1/videos', json=dict(
                video_subject='Bundled engine offline check',
                video_script='这是内置视频引擎的离线合成检查。', video_source='local',
                video_materials=[dict(provider='local', url=str(clip), duration=2)],
                video_aspect='16:9', video_clip_duration=2,
                voice_name='zh-CN-XiaoxiaoNeural-Female', subtitle_enabled=args.subtitles,
                font_size=18, stroke_width=1, bgm_type='random', n_threads=1))
            assert response.status_code == 200
            tid = response.json()['data']['task_id']
            deadline = time.monotonic() + 90
            while True:
                result = host.state.state.get_task(tid)
                if result.get('state') in {-1, 1}:
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError('Local render did not complete in 90 seconds')
                time.sleep(.05)
            assert result.get('state') == 1, result.get('failure_reason', 'task failed')
            assert client.get('/api/v1/tasks/' + tid).status_code == 200
            final = Path(result['videos'][0])
            assert final.is_file() and final.stat().st_size > 0
            command('-i', final, '-f', 'null', '-')
            subtitle = result.get('subtitle_path', '')
            if args.subtitles:
                assert subtitle and Path(subtitle).is_file()
            report = dict(ok=True, source='bundled API, not the original checkout',
                          api_create_and_status=True, completed=True,
                          full_ffmpeg_decode=True, subtitles=args.subtitles,
                          empty_random_music_disabled=True,
                          final_bytes=final.stat().st_size,
                          inputs='synthetic color video and sine audio', resolution='320x180',
                          online_model_stock_and_tts_tested=False, private_config_isolated=True)
    target = ROOT / 'artifacts/bundled-moneyprinter-check.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
