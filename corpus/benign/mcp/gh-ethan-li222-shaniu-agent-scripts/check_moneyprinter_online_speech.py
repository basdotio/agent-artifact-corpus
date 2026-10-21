"""Read and execute upstream Edge speech functions; never use local fallback.

No upstream imports/config writes, LLM calls, or stock API calls. Logs omit URLs
and credentials. Output is saved only under Shaniu artifacts.
"""
import ast
import argparse
import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
import re
import sys
from typing import Union
from project_paths import moneyprinter_project

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=moneyprinter_project())
    parser.add_argument('--edge-module', type=Path, help='Isolated edge-tts package directory')
    parser.add_argument('--label', default='current')
    args = parser.parse_args()
    if args.label not in {'current', 'upstream-pinned'}:
        parser.error('Invalid report label')
    if args.edge_module:
        sys.path.insert(0, str(args.edge_module.resolve()))
    import edge_tts
    from edge_tts import submaker
    from loguru import logger
    import aiohttp
    output = ROOT/'artifacts/moneyprinter-online-check'/args.label
    output.mkdir(parents=True, exist_ok=True)
    source = args.project.resolve() / 'app/services/voice.py'
    native_compatible = hasattr(submaker, 'mktimestamp') and hasattr(edge_tts.SubMaker, 'create_sub')
    logger.remove()  # Upstream logs raw connection URLs on error.
    from moneyprinter_compat import install_edge_compat
    install_edge_compat()
    original = edge_tts.Communicate
    errors = []
    class DiagnosticCommunicate(original):
        async def stream(self):
            try:
                async for chunk in super().stream():
                    yield chunk
            except Exception as error:
                detail = dict(type=type(error).__name__)
                if isinstance(error, aiohttp.ClientResponseError):
                    detail['status'] = error.status
                    date = (error.headers or {}).get('Date')
                    if date:
                        try:
                            detail['server_clock_difference_seconds'] = round((parsedate_to_datetime(date)-datetime.now(timezone.utc)).total_seconds())
                        except (ValueError, TypeError):
                            pass
                errors.append(detail)
                raise
    edge_tts.Communicate = DiagnosticCommunicate
    names = {'azure_tts_v1', 'parse_voice_name', 'convert_rate_to_percent', 'get_audio_duration'}
    tree = ast.parse(source.read_text(encoding='utf-8'))
    module = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[])
    namespace = dict(asyncio=asyncio, edge_tts=edge_tts, SubMaker=edge_tts.SubMaker,
                     submaker=submaker, Union=Union, logger=logger, re=re)
    exec(compile(module, str(source), 'exec'), namespace)
    text = '你好，这是 MoneyPrinter 在线配音检查。大熊猫生活在中国。'
    results = []
    target = output/'upstream.mp3'
    maker = namespace['azure_tts_v1'](text, 'zh-CN-XiaoxiaoNeural-Female', 1.0, str(target))
    results.append(dict(path='upstream_azure_tts_v1_with_subtitle_compat', ok=bool(maker),
                        bytes=target.stat().st_size if target.exists() else 0,
                        boundaries=len(maker.subs) if maker else 0, errors=list(errors)))
    errors.clear()
    if not args.edge_module:
        from moneyprinter_speech import online
        target = output/'shaniu-online.mp3'
        try:
            maker = asyncio.run(online(text, 'zh-CN-XiaoxiaoNeural', 1.0, target))
            results.append(dict(path='shaniu_online_no_fallback', ok=True, bytes=target.stat().st_size, boundaries=len(maker.subs)))
        except Exception as error:
            results.append(dict(path='shaniu_online_no_fallback', ok=False, type=type(error).__name__, errors=list(errors)))
    report = dict(edge_tts_version=edge_tts.__version__, native_upstream_subtitle_api_compatible=native_compatible,
                  python=sys.version.split()[0], fallback_used=False, results=results)
    for file in output.glob('*.mp3'):
        if file.stat().st_size == 0:
            file.unlink()
    (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
