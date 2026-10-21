"""Generate synthetic listening samples without model calls or user data."""
import json
from pathlib import Path
from speech import duration, synthesize, write_subtitles

ROOT = Path(__file__).resolve().parents[1]
TEXT = '你来了呀！今天过得怎么样？如果有点累，就先休息一下。别着急，我们一步一步来，好吗？'


def main():
    folder = ROOT / 'artifacts/speech-natural'
    folder.mkdir(parents=True, exist_ok=True)
    cases = [('before', '原本的本地语音', 'windows', 'cool', False),
             ('local-natural', '本地语音 · 优化停顿', 'windows', 'cool', True),
             ('edge-standard', '晓晓 · 默认音高与停顿', 'edge', 'cool', False),
             ('cool', '晓晓 · 酷', 'edge', 'cool', True),
             ('happy', '晓晓 · 喜', 'edge', 'happy', True),
             ('gentle', '晓晓 · 乖', 'edge', 'gentle', True),
             ('shy', '晓晓 · 羞', 'edge', 'shy', True)]
    reports, blocks = [], []
    for name, title, provider, emotion, natural in cases:
        path = folder / (name+'.wav')
        result = synthesize(TEXT, path, emotion, dict(provider=provider, natural=natural, fallback=False))
        write_subtitles(path, result.cues)
        report = dict(name=name, provider=result.provider, voice=result.voice, duration=round(duration(path), 3), added_pause_seconds=result.added_pause_seconds, alignment=result.alignment, cues=len(result.cues))
        reports.append(report)
        blocks.append(f'<article><h2>{title}</h2><audio controls preload="metadata" src="{path.name}"></audio><p>{report["duration"]} 秒 · {result.alignment}</p></article>')
        print(json.dumps(report, ensure_ascii=True), flush=True)
    (folder / 'report.json').write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding='utf-8')
    (folder / 'index.html').write_text('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>傻妞语音试听</title><style>body{font:16px/1.7 system-ui;background:#faf8f4;color:#34313a;max-width:800px;margin:40px auto;padding:20px}article{background:white;padding:16px 24px;border-radius:16px;margin:16px 0}h2{font-size:18px}audio{width:100%}p{color:#777}</style><h1>傻妞 · 语音对比</h1><p>'+TEXT+'</p>'+''.join(blocks), encoding='utf-8')


if __name__ == '__main__':
    main()
