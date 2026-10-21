"""Verify native tools; optionally create and query a real short audio task."""
import argparse
import asyncio
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from shaniu.config import Settings
from shaniu.moneyprinter import MoneyPrinterTools, TOOLS, ToolError
from shaniu.providers import CompatibleProvider
from shaniu.storage import Store


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--create-audio', action='store_true', help='实际提交短音频任务并通过模型查询结果')
    options = parser.parse_args()
    settings = replace(Settings.from_env(), moneyprinter_enabled=True)
    if settings.provider != 'compatible':
        raise SystemExit('需要配置真实 compatible 模型。')
    with tempfile.TemporaryDirectory() as temp:
        tools = MoneyPrinterTools(settings, Store(Path(temp) / 'test.db'))
        calls = []
        results = []
        async def execute(name, args):
            calls.append(name)
            try:
                result = await tools.call('check', name, args)
            except ToolError as error:
                result = dict(error=str(error))
            results.append((name, result))
            return result
        selected = TOOLS if options.create_audio else TOOLS[:1]
        definitions = [dict(type='function', function=dict(name=tool['name'], description=tool['description'], parameters=tool['inputSchema'])) for tool in selected]
        try:
            prompt = '请调用 moneyprinter_create 创建且只创建一次 audio 任务，名称是接口联调，完整文案是：你好，我是傻妞。只告诉我提交状态和任务ID，先不要查询。' if options.create_audio else '请必须调用 moneyprinter_health 工具检查视频制作服务是否在线，然后用一句话告诉我真实结果。不要创建任何任务。'
            answer = ''.join([part async for part in CompatibleProvider(settings).stream_with_tools(
                [dict(role='user', content=prompt, status='done')],
                'cool', [], definitions, execute)])
            if options.create_audio:
                assert calls.count('moneyprinter_create') == 1
                created = next(result for name, result in results if name == 'moneyprinter_create')
                tid = created['task_id']
                for _ in range(90):
                    status = await tools.call('check', 'moneyprinter_status', dict(task_id=tid))
                    if status['status'] in {'completed', 'failed'}:
                        break
                    await asyncio.sleep(1)
                assert status['status'] == 'completed'
                answer = ''.join([part async for part in CompatibleProvider(settings).stream_with_tools(
                    [dict(role='user', content=f'请调用 moneyprinter_status 查询我提交的任务 {tid}，告诉我真实状态及完整文件链接，不要创建任何新任务。', status='done')],
                    'cool', [], definitions, execute)])
                checked = [result for name, result in results if name == 'moneyprinter_status']
                assert checked and checked[-1]['status'] == 'completed' and checked[-1]['artifacts']
                assert calls.count('moneyprinter_create') == 1
                assert tid in answer or checked[-1]['artifacts'][0]['url'] in answer
            else:
                assert calls == ['moneyprinter_health'], '模型没有调用指定工具或重复调用'
            assert answer.strip(), '模型没有返回结果说明'
        except Exception as error:
            print(json.dumps(dict(ok=False, error_type=type(error).__name__, message=str(error) if isinstance(error, RuntimeError) else '工具调用检查失败'), ensure_ascii=False))
            return 1
        print(json.dumps(dict(ok=True, model=settings.model, native_tool_calls=calls, answer=answer), ensure_ascii=False))
        if options.create_audio:
            target = ROOT / 'artifacts/moneyprinter-agent-live.json'
            target.parent.mkdir(exist_ok=True)
            target.write_text(json.dumps(dict(ok=True, model=settings.model, task_id=tid, native_tool_calls=calls, results=results), ensure_ascii=False, indent=2), encoding='utf-8')
        return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
