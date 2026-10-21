"""Isolated, deterministic media post-processing. No LLM or generation APIs."""
import argparse
import contextlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def progress(value, stage):
    print(json.dumps(dict(progress=value, stage=stage), ensure_ascii=True), flush=True, file=sys.__stdout__)


def vendor(name):
    spec = importlib.util.spec_from_file_location('easel_'+name, ROOT/'vendor/easel-media'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if name == 'subtitle_ops':
        original = module._parse_ass
        # Easel's parser otherwise treats the Styles Format as Events Format.
        module._parse_ass = lambda raw: original(raw.split('[Events]',1)[-1])
    return module


def probe(path):
    import av
    with av.open(str(path)) as media:
        streams = []
        for stream in media.streams:
            streams.append(dict(codec_type=stream.type, codec_name=stream.codec_context.name,
                                width=getattr(stream, 'width', 0), height=getattr(stream, 'height', 0),
                                duration=float(stream.duration*stream.time_base) if stream.duration is not None else None,
                                fps=float(stream.average_rate) if stream.type == 'video' and stream.average_rate else None))
        length = media.duration/1_000_000 if media.duration is not None else max((s['duration'] or 0 for s in streams), default=0)
    return dict(format=dict(duration=length), streams=streams)


def execute(arguments, *, capture=False, span=(20, 75), length=None):
    import imageio_ffmpeg
    args = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-threads', '2', '-filter_threads', '2'] + list(arguments[1:])
    if capture:
        return subprocess.run(args, check=True, capture_output=True, text=True, timeout=1800)
    args[1:1] = ['-progress', 'pipe:1', '-nostats']
    # Logs stay in the owned job directory and are never public artifacts.
    with Path('ffmpeg.log').open('ab') as log:
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=log, text=True)
        last = -1
        try:
            for line in process.stdout:
                if line.startswith('out_time_us=') and length:
                    try:
                        fraction = max(0, min(1, int(line.split('=', 1)[1])/1_000_000/length))
                        current = round(span[0]+fraction*(span[1]-span[0]))
                        if current != last:
                            progress(current, '处理媒体'); last = current
                    except ValueError:
                        pass
            if process.wait():
                raise RuntimeError('Media processing failed')
        finally:
            if process.poll() is None:
                process.kill(); process.wait()
    return SimpleNamespace(returncode=0, stdout='', stderr='')


def window(cues, start, end):
    return [dict(cue, start=round(max(cue['start'], start)-start, 3), end=round(min(cue['end'], end)-start, 3))
            for cue in cues if cue['end'] > start and cue['start'] < end]


def safe_cues(path):
    from html import unescape
    subtitles = vendor('subtitle_ops')
    cues = subtitles.parse_file(path)
    previous = -1
    for cue in cues:
        if not all(math.isfinite(cue[k]) for k in ('start', 'end')) or cue['start'] < previous or cue['start'] < 0 or cue['end'] <= cue['start']:
            raise ValueError('Invalid subtitle timeline')
        previous = cue['start']
        # ASS overrides and SRT markup are not executable user styling.
        cue['text'] = re.sub(r'\{[^}]*\}|<[^>]*>', '', unescape(cue['text'])).replace('\\', '／')
    if not cues:
        raise ValueError('No subtitle cues')
    return cues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    os.chdir(directory)
    options = json.loads(Path('options.json').read_text(encoding='utf-8'))
    operation = options['operation']
    subtitles = vendor('subtitle_ops')
    result_files = []
    report = dict(schema='shaniu-media-post/1', operation=operation, semantic_review=False,
                  limitations=['技术检查不判断物种、事实、画面与台词语义，也不检测数字人口型同步。'])
    progress(15, '读取媒体信息')
    if operation == 'subtitle':
        cues = safe_cues(Path('source.srt'))
        destination = Path('subtitles.'+options['format'])
        subtitles._write_subtitle(cues, destination, options['format'], bilingual=False, order='orig-top', font='Microsoft YaHei')
        if len(subtitles.parse_file(destination)) != len(cues):
            raise ValueError('Subtitle round-trip failed')
        result_files.append(destination.name)
        report.update(cue_count=len(cues), timing_preserved=True)
    else:
        info = probe('source.mp4')
        duration = float(info['format']['duration'])
        if not 0 < duration <= 600 or not any(s['codec_type'] == 'video' for s in info['streams']):
            raise ValueError('Video must be between 0 and 600 seconds')
        output = Path('result.mp4')
        ops = vendor('video_ops')
        ops._run = lambda cmd, **kw: execute(cmd, **kw, length=duration)
        ops._done = lambda *a, **k: None
        ops._has_audio = lambda path: any(s['codec_type'] == 'audio' for s in probe(path)['streams'])
        cues = safe_cues(Path('source.srt')) if Path('source.srt').exists() else []
        original = operation in {'cover', 'review'}
        source = Path('source.mp4')
        if not original and options['source'] == 'clean':
            execute(['ffmpeg', '-y', '-i', 'source.mp4', '-i', 'voice.audio', '-map', '0:v:0', '-map', '1:a:0',
                     '-c:v', 'copy', '-c:a', 'aac', '-shortest', 'clean.mp4'], span=(15,20), length=duration)
            source = Path('clean.mp4')
            report['source'] = 'clean_video_and_original_voice'
            report['original_bgm_preserved'] = False
        else:
            report['source'] = 'original_completed_video'
        start, end = 0., duration
        with contextlib.redirect_stdout(sys.stderr):
            # Upstream utility output is sent to a private log; progress is JSON.
            if operation == 'cut':
                start, end = options['start'], options['end']
                if not 0 <= start < end <= duration+.05:
                    raise ValueError('Cut window outside video')
                end = min(end, duration)
                ops.cmd_cut(SimpleNamespace(input=str(source), output=str(output), start=str(start), end=None,
                                            duration=str(end-start), reencode=True, crf=20, preset='fast'))
            elif operation == 'compress':
                ops.cmd_compress(SimpleNamespace(input=str(source), output=str(output), bitrate=None, crf=options['crf'],
                                                 preset='fast', scale=None, audio_bitrate='128k'))
            elif operation == 'reframe':
                frame = vendor('reframe')
                frame._check_ffmpeg = lambda: None
                frame._probe_wh = lambda p: next((s['width'],s['height']) for s in probe(p)['streams'] if s['codec_type']=='video')
                frame._has_audio = ops._has_audio
                frame._done = lambda *a, **k: None
                frame._run = ops._run
                dimensions = {'9:16':'720x1280', '16:9':'1280x720', '1:1':'720x720'}
                frame.cmd_reframe(SimpleNamespace(input=str(source),output=str(output),ratio=options['aspect'],mode=options['mode'],
                                                 size=dimensions[options['aspect']],focus_x=.5,focus_y=.5,blur_sigma=20))
            elif operation == 'cover':
                if not 0 <= options['time'] < duration:
                    raise ValueError('Cover timestamp outside video')
                ops.cmd_frame(SimpleNamespace(input=str(source),output='cover.jpg',time=str(options['time']),width=1280,quality=2))
                result_files.append('cover.jpg')
            elif operation != 'review':
                raise ValueError('Unsupported operation')
        if operation in {'cut', 'reframe', 'compress'}:
            out_cues = window(cues, start, end)
            if out_cues:
                subtitles._write_subtitle(out_cues, Path('subtitles.srt'), 'srt', bilingual=False, order='orig-top', font='Microsoft YaHei')
                result_files.append('subtitles.srt')
            if options['source'] == 'clean' and options['subtitles']:
                if not out_cues:
                    raise ValueError('No subtitles in output window')
                fonts = 'C\\:/Windows/Fonts' if os.name == 'nt' else '/usr/share/fonts'
                execute(['ffmpeg','-y','-i',str(output),'-vf',f"subtitles=subtitles.srt:fontsdir='{fonts}':force_style='FontName=Microsoft YaHei'",
                         '-c:v','libx264','-preset','fast','-crf','20','-c:a','copy','captioned.mp4'], span=(75,85),length=end-start)
                Path('captioned.mp4').replace(output)
            result_files.insert(0, output.name)
            info = probe(output)
            actual = float(info['format']['duration'])
            if abs(actual-(end-start)) > .35:
                raise ValueError('Unexpected output duration')
            report.update(expected_duration=end-start, output_duration=actual,
                          subtitles_burned=options['subtitles'] if options['source']=='clean' else 'preserved_from_original')
            source = output
        progress(87, '检查产物')
        if operation != 'cover':
            execute(['ffmpeg','-v','error','-i',str(source),'-f','null','-'],span=(87,92),length=end-start)
            report.update(full_decode_ok=True, media=probe(source))
        if operation == 'review':
            from PIL import Image, ImageDraw
            sheet = Image.new('RGB',(960,600),'#202820')
            draw = ImageDraw.Draw(sheet)
            for i, fraction in enumerate((.1,.3,.5,.7,.85,.95)):
                execute(['ffmpeg','-y','-ss',str(duration*fraction),'-i',str(source),'-frames:v','1','-vf','scale=480:-2',f'frame-{i}.jpg'])
                with Image.open(f'frame-{i}.jpg') as picture:
                    x,y=(i%2)*480,(i//2)*200
                    picture.thumbnail((480,175)); sheet.paste(picture,(x,y))
                    draw.text((x+8,y+178),f'{duration*fraction:.2f}s',fill='white')
            sheet.save('review.jpg'); result_files.append('review.jpg')
            import imageio_ffmpeg
            level = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-i',str(source),'-vn','-af','volumedetect','-f','null','-'],
                                   capture_output=True,text=True,timeout=300)
            values = re.findall(r'(mean_volume|max_volume):\s*([-\w.]+) dB',level.stderr)
            report['audio_levels_dbfs'] = dict(values)
            report['audio_analysis_available'] = bool(values)
        if operation == 'cover':
            from PIL import Image
            with Image.open('cover.jpg') as picture:
                picture.verify()
            report['image_decode_ok'] = True
    report['files'] = result_files+['report.json']
    Path('report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    progress(99, '后期处理完成')


if __name__ == '__main__':
    main()
