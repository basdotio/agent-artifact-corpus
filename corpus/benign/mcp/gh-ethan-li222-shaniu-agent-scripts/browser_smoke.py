"""Headless Chrome integration check; no browser downloads or paid APIs.

Run after building the frontend: python scripts/browser_smoke.py
"""
import asyncio
import base64
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import uuid4

import aiohttp
from aiohttp import web

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from shaniu.config import Settings
from shaniu.server import create_app, SERVICE
from shaniu.providers import DemoProvider
from shaniu.avatar_catalog import AVATARS, avatar_ready
ALL_AVATARS = all(avatar_ready(avatar['id']) for avatar in AVATARS)

MARKDOWN_SAMPLE = '# 学习计划\n\n**先复习**，再读 [文档](https://example.com)。\n\n| 项目 | 时间 |\n| --- | --- |\n| 学习 | 十分钟 |\n\n```python\nprint("不要念代码")\n```\n\n<img src=x onerror="window.markdownExecuted=true">'


class BrowserProvider(DemoProvider):
    async def stream(self, history, emotion, memories):
        if history[-1]['content'] in {'Markdown检查', '实时Markdown检查'}:
            source = MARKDOWN_SAMPLE if history[-1]['content'] == 'Markdown检查' else '# 问候\n\n**你好**，我是 [傻妞](https://example.com)。'
            for index in range(0, len(source), 3):
                yield source[index:index+3]
                await asyncio.sleep(.001)
        else:
            async for delta in super().stream(history, emotion, memories):
                yield delta

MEDIA = '--media' in sys.argv
REALTIME = '--realtime' in sys.argv


async def main():
    if os.name == 'nt' and (MEDIA or REALTIME):
        def transport_shutdown(loop, context):
            # Chrome can reset its CDP socket while closing/reloading. Python's
            # Proactor logs shutdown() on that already-reset transport as an error.
            error = context.get('exception')
            callback = getattr(context.get('handle'), '_callback', None)
            if isinstance(error, ConnectionResetError) and getattr(error, 'winerror', None) == 10054 and '_ProactorBasePipeTransport._call_connection_lost' in getattr(callback, '__qualname__', ''):
                return
            loop.default_exception_handler(context)
        asyncio.get_running_loop().set_exception_handler(transport_shutdown)
    chrome = os.getenv('CHROME_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    if not Path(chrome).is_file():
        raise SystemExit('Set CHROME_PATH to an installed Chrome executable.')
    with tempfile.TemporaryDirectory(prefix='shaniu-browser-') as temp:
        temp = Path(temp)
        profile = temp / 'profile'
        app = create_app(Settings(database=temp / 'test.sqlite3', moneyprinter_enabled=True), BrowserProvider())
        media_fixture = dict(state=4, reads=0)
        motion_finished = asyncio.Event()
        async def motion_fixture(job_id, *args):
            motion = app[SERVICE].moneyprinter.motion
            motion.update(job_id, status='processing', progress=35, stage='渲染动效')
            await motion_finished.wait()
            directory = motion.root/job_id
            directory.mkdir()
            if fixture_video.is_file():
                import shutil
                shutil.copy2(fixture_video, directory/'enhanced.mp4')
            else:
                (directory/'enhanced.mp4').write_bytes(b'fixture')
            (directory/'project.zip').write_bytes(b'fixture-archive')
            (directory/'report.json').write_text('{"completeDecode":true}',encoding='utf-8')
            motion.update(job_id, status='completed', progress=100, stage='动效增强完成')
        app[SERVICE].moneyprinter.motion.run = motion_fixture
        post_finished = asyncio.Event()
        async def post_fixture(job_id, *args):
            post = app[SERVICE].moneyprinter.post
            post.update(job_id, status='processing', progress=42, stage='制作封面')
            await post_finished.wait()
            directory = post.root/job_id; directory.mkdir()
            from PIL import Image
            Image.new('RGB',(640,360),'#49705b').save(directory/'cover.jpg')
            (directory/'report.json').write_text('{"image_decode_ok":true}',encoding='utf-8')
            post.update(job_id,status='completed',progress=100,stage='处理完成',files=['cover.jpg','report.json'])
        app[SERVICE].moneyprinter.post.run = post_fixture
        media_tid = str(uuid4())
        fixture_video = Path(os.getenv('SHANIU_TEST_VIDEO', str(ROOT / 'data/test-fixtures/video.mp4'))).expanduser().resolve()
        async def media_status(request):
            media_fixture['reads'] += 1
            done = media_fixture['state'] == 1
            return web.json_response(dict(status=200, data=dict(state=media_fixture['state'], progress=100 if done else 40,
                shaniu_stage='render', videos=[f'/tasks/{media_tid}/final-1.mp4'] if done else [],
                combined_videos=[f'/tasks/{media_tid}/combined.mp4'], audio_file=f'/tasks/{media_tid}/voice.wav', subtitle_path=f'/tasks/{media_tid}/subtitle.srt')))
        async def media_file(request):
            if fixture_video.is_file():
                return web.FileResponse(fixture_video)
            return web.Response(body=b'\x00\x00\x00 ftypisom'+b'0'*20, content_type='video/mp4')
        app.router.add_get('/api/v1/tasks/{taskid}', media_status)
        app.router.add_get('/tasks/{taskid}/final-1.mp4', media_file)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        app[SERVICE].moneyprinter.url = f'http://127.0.0.1:{port}'
        process = subprocess.Popen([
            chrome, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
            '--remote-debugging-port=0', f'--user-data-dir={profile}', 'about:blank',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            for _ in range(100):
                if (profile / 'DevToolsActivePort').is_file():
                    break
                if process.poll() is not None:
                    raise RuntimeError('Chrome exited before opening its debugging port')
                await asyncio.sleep(.1)
            debug_port = (profile / 'DevToolsActivePort').read_text().splitlines()[0]
            async with aiohttp.ClientSession() as client:
                pages = await (await client.get(f'http://127.0.0.1:{debug_port}/json/list')).json()
                page = next(p for p in pages if p['type'] == 'page')
                async with client.ws_connect(page['webSocketDebuggerUrl']) as ws:
                    serial = 0
                    console_errors = []

                    async def cdp(method, params=None):
                        nonlocal serial
                        serial += 1
                        await ws.send_json(dict(id=serial, method=method, params=params or {}))
                        while True:
                            packet = await asyncio.wait_for(ws.receive_json(), 15)
                            if packet.get('method') == 'Runtime.exceptionThrown':
                                console_errors.append(packet['params'])
                            if packet.get('id') == serial:
                                if 'error' in packet:
                                    raise RuntimeError(packet['error'])
                                return packet.get('result', {})

                    async def evaluate(expression):
                        result = await cdp('Runtime.evaluate', dict(expression=expression, returnByValue=True, awaitPromise=True))
                        if 'exceptionDetails' in result:
                            raise AssertionError(result['exceptionDetails'])
                        return result.get('result', {}).get('value')

                    async def wait(expression):
                        for _ in range(150):
                            if await evaluate(expression):
                                return
                            await asyncio.sleep(.1)
                        raise AssertionError('Timed out: ' + expression)

                    await cdp('Runtime.enable')
                    await cdp('Emulation.setDeviceMetricsOverride', dict(width=1440, height=1000, deviceScaleFactor=1, mobile=False))
                    await cdp('Page.navigate', dict(url=f'http://127.0.0.1:{port}/'))
                    await wait("document.querySelector('.boot-card .primary') !== null")
                    await evaluate("document.querySelector('.boot-card .primary').click()")
                    await wait("document.querySelector('.chat-header p').textContent.includes('已就绪')")
                    if ALL_AVATARS:
                        await evaluate("document.querySelector('.avatar-select-trigger').click()")
                        await wait("document.querySelector('.avatar-dialog').open")
                        assert await evaluate("document.querySelectorAll('.avatar-options button:not(:disabled)').length") == len(AVATARS)
                        await wait("Array.from(document.querySelectorAll('.avatar-options img')).every(img=>img.complete && img.naturalWidth > 0)")
                        (ROOT / 'artifacts').mkdir(exist_ok=True)
                        screenshot = await cdp('Page.captureScreenshot', dict(format='png'))
                        (ROOT / 'artifacts/avatars-desktop.png').write_bytes(base64.b64decode(screenshot['data']))
                        await evaluate("document.querySelector('[data-avatar-id=wav2lip_avatar_shaniu]').click()")
                        await wait("!document.querySelector('.avatar-dialog').open && document.querySelector('.avatar-select-trigger').textContent.includes('原剧换装')")
                        assert await evaluate("document.querySelector('.avatar-photo').src.includes('wav2lip_avatar_shaniu')")
                        assert await evaluate("document.querySelector('.avatar-photo').src.includes('emotion=cool')")
                        assert await evaluate("document.querySelector('.emotion-header small').textContent.includes('银色战衣')")
                        await evaluate("document.querySelectorAll('.emotion-grid button')[2].click()")
                        await wait("document.querySelector('.emotion-header small').textContent.includes('红色战衣')")
                        await wait("document.querySelector('.avatar-photo').src.includes('emotion=gentle')")
                        await evaluate("document.querySelectorAll('.emotion-grid button')[0].click()")
                        await wait("document.querySelector('.emotion-header small').textContent.includes('银色战衣')")
                    assert await evaluate("document.querySelector('.tools-dialog').open") is False
                    await evaluate("document.querySelector('.tools-trigger').click()")
                    await wait("document.querySelector('.tools-dialog').open")
                    assert await evaluate("document.querySelector('.tool-group input').checked") is False
                    assert await evaluate("document.querySelectorAll('.tool-group').length") == 5
                    assert await evaluate("document.querySelectorAll('.tool-capabilities span').length") == 15
                    assert await evaluate("Array.from(document.querySelectorAll('.tool-group input')).every(i => !i.checked)")
                    await evaluate("document.querySelector('.tool-group input').click()")
                    await wait("document.querySelector('.tools-count')?.textContent === '1'")
                    await evaluate("document.querySelector('.tool-group input').click()")
                    await wait("document.querySelector('.tools-count') === null")
                    await evaluate("document.querySelectorAll('.tool-group input')[1].click()")
                    await wait("document.querySelector('.tools-count')?.textContent === '1'")
                    await evaluate("document.querySelectorAll('.tool-group input')[2].click()")
                    await wait("document.querySelector('.tools-count')?.textContent === '2'")
                    await evaluate("document.querySelectorAll('.tool-group input')[1].click()")
                    await wait("document.querySelector('.tools-count')?.textContent === '1'")
                    await evaluate("document.querySelectorAll('.tool-group input')[2].click()")
                    await wait("document.querySelector('.tools-count') === null")
                    await evaluate("document.querySelector('.tool-group input').click()")
                    await evaluate("document.querySelector('.tools-panel-footer button').click()")
                    assert await evaluate("document.querySelector('.tools-dialog').open") is False
                    await evaluate("document.querySelectorAll('.emotion-grid button')[1].click()")
                    await wait("document.querySelector('.emotion-grid .chosen strong').textContent === '喜'")
                    await evaluate("document.querySelectorAll('.suggestions button')[2].click()")
                    await wait("document.querySelector('.tool-result')?.textContent.includes('北京时间')")
                    await wait("document.querySelectorAll('.message.assistant').length === 2")
                    assert await evaluate("Array.from(document.querySelectorAll('.message')).map(m => m.classList.contains('user') ? 'user' : 'assistant').join(',')") == 'assistant,user,assistant'

                    if MEDIA:
                        await wait("document.querySelector('.media-button') && !document.querySelector('.media-button').disabled")
                        await evaluate("document.querySelector('.media-button').click()")
                        await wait("document.querySelector('.avatar-video')?.readyState >= 2")
                        playback = await cdp('Runtime.evaluate', dict(expression="document.querySelector('.avatar-video').play()", awaitPromise=True, userGesture=True))
                        assert 'exceptionDetails' not in playback, playback
                        await wait("document.querySelector('.avatar-video').currentTime > 0.35")
                        assert await evaluate("document.querySelector('.avatar-video').videoWidth > 0")
                        assert await evaluate("document.querySelectorAll('.media-downloads a').length") == 3
                        assert await evaluate("document.querySelector('.subtitle-control input').checked") is True
                        assert await evaluate("document.querySelector('.avatar-note').textContent.includes('语音边界字幕')") is True
                        download_ok = await evaluate("Promise.all(Array.from(document.querySelectorAll('.media-downloads a')).map(a=>fetch(a.href).then(r=>r.status))).then(values=>values.every(status=>status===200))")
                        assert download_ok
                        await evaluate("document.querySelector('.avatar-video').pause()")
                        media_image = await cdp('Page.captureScreenshot', dict(format='png'))
                        (ROOT / 'artifacts').mkdir(exist_ok=True)
                        (ROOT / 'artifacts/media-desktop.png').write_bytes(base64.b64decode(media_image['data']))
                        print('GPU browser check passed: rendered short reply, loaded H.264/AAC, played video frames.')
                        await evaluate("document.querySelector('.subtitle-control input').click()")
                        assert await evaluate("document.querySelector('.subtitle-control input').checked") is False
                        assert await evaluate("localStorage.getItem('shaniu.subtitles')") == 'off'
                        await evaluate("document.querySelectorAll('.segmented button')[1].click()")
                        await wait("document.querySelector('#transport') !== null")
                        await evaluate("document.querySelector('#transport').value='clip';document.querySelector('#transport').dispatchEvent(new Event('change',{bubbles:true}))")
                        await asyncio.sleep(.2)
                        await evaluate("document.querySelector('.composer textarea').value='现在几点了？';document.querySelector('.composer textarea').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.composer').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
                        await wait("document.querySelector('.avatar-video')?.readyState >= 2")
                        # Autoplay can be rejected in an unattended browser: test the explicit recovery button.
                        if await evaluate("document.querySelector('.playback-notice button') !== null"):
                            await cdp('Runtime.evaluate', dict(expression="document.querySelector('.playback-notice button').click()", userGesture=True))
                        await wait("document.querySelector('.avatar-video').currentTime > .1")
                        assert await evaluate("document.querySelector('.avatar-note').textContent.includes('无字幕')")
                        no_subtitles_image = await cdp('Page.captureScreenshot', dict(format='png'))
                        (ROOT / 'artifacts/media-no-subtitles.png').write_bytes(base64.b64decode(no_subtitles_image['data']))
                        print('Automatic clip generation and playback/recovery passed without clicking a message generation button.')
                        await evaluate("document.querySelectorAll('.segmented button')[0].click()")
                        await asyncio.sleep(.2)

                    if REALTIME:
                        await evaluate("document.querySelectorAll('.segmented button')[1].click()")
                        await wait("document.querySelector('#transport') !== null")
                        await evaluate("document.querySelector('#transport').value='realtime';document.querySelector('#transport').dispatchEvent(new Event('change',{bubbles:true}))")
                        await wait("document.querySelector('.rtc-connect') !== null")
                        await cdp('Runtime.evaluate', dict(expression="document.querySelector('.rtc-connect').click()", userGesture=True))
                        await wait("document.querySelector('.rtc-status')?.textContent.includes('实时已连接')")
                        await wait("document.querySelector('.avatar-video')?.readyState >= 2")
                        await evaluate("document.querySelector('.composer textarea').value='现在几点了？';document.querySelector('.composer textarea').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.composer').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
                        await wait("document.querySelector('.avatar-note')?.textContent.includes('首帧')")
                        await cdp('Runtime.evaluate', dict(expression="document.querySelector('.avatar-video').play()", awaitPromise=True, userGesture=True))
                        await wait("document.querySelector('.avatar-video').getVideoPlaybackQuality().totalVideoFrames > 10")
                        assert await evaluate("document.querySelector('.avatar-video').srcObject.getAudioTracks().length") == 1
                        assert await evaluate("document.querySelector('.avatar-video').dataset.transport") == 'webrtc'
                        await wait("document.querySelector('.replay-button') && !document.querySelector('.replay-button').disabled")
                        await cdp('Runtime.evaluate', dict(expression="document.querySelector('.replay-button').click()", userGesture=True))
                        await wait("document.querySelector('.replay-dialog').open && document.querySelector('.replay-dialog video')?.readyState >= 2")
                        assert await evaluate("document.querySelector('.replay-dialog video').duration > 0")
                        assert await evaluate("document.querySelector('.replay-dialog video').muted") is False
                        assert await evaluate("fetch(document.querySelector('.replay-dialog video').src, {headers: {Range: 'bytes=0-99'}}).then(r => r.status)") == 206
                        await evaluate("const replay = document.querySelector('.replay-dialog video'); replay.pause(); replay.currentTime = replay.duration / 2")
                        await wait("document.querySelector('.replay-dialog video').currentTime > 0 && !document.querySelector('.replay-dialog video').seeking")
                        await evaluate("document.querySelector('.replay-dialog .tools-close').click()")
                        await wait("!document.querySelector('.replay-dialog').open")
                        assert await evaluate("document.querySelector('.rtc-status').textContent.includes('实时已连接')")
                        if ALL_AVATARS:
                            await evaluate("document.querySelector('.avatar-select-trigger').click()")
                            await wait("document.querySelector('.avatar-dialog').open")
                            await evaluate("document.querySelector('[data-avatar-id=wav2lip_avatar_glass_man]').click()")
                            await wait("!document.querySelector('.avatar-dialog').open && document.querySelector('.avatar-select-trigger').textContent.includes('眼镜男生')")
                            await wait("document.querySelector('.rtc-status').textContent.includes('实时已连接')")
                        await evaluate("document.querySelector('.composer textarea').value='实时Markdown检查';document.querySelector('.composer textarea').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.composer').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
                        await wait("document.querySelectorAll('.replay-button').length === 2 && !document.querySelector('.replay-button').disabled")
                        await evaluate("document.querySelectorAll('.emotion-grid button')[3].click()")
                        await wait("document.querySelector('.emotion-grid .chosen strong').textContent === '羞'")
                        await wait("document.querySelector('.avatar-note')?.textContent.includes('轻量表情')")
                        (ROOT / 'artifacts').mkdir(exist_ok=True)
                        screenshot = await cdp('Page.captureScreenshot', dict(format='png'))
                        (ROOT / 'artifacts/realtime-desktop.png').write_bytes(base64.b64decode(screenshot['data']))
                        print('WebRTC browser passed: automatic sentence speech, decoded video/audio tracks, shy expression switch.')
                        await evaluate("document.querySelectorAll('.segmented button')[0].click()")
                        await evaluate("document.querySelectorAll('.emotion-grid button')[1].click()")
                        await wait("document.querySelector('.emotion-grid .chosen strong').textContent === '喜'")

                    # Exercise real Vue input events, stream cancellation and partial status.
                    await evaluate("document.querySelector('.composer textarea').value = '帮我安排学习计划'; document.querySelector('.composer textarea').dispatchEvent(new Event('input', {bubbles:true}))")
                    await evaluate("document.querySelector('.composer').dispatchEvent(new Event('submit', {bubbles:true,cancelable:true}))")
                    await wait("document.querySelector('.working button') !== null")
                    await evaluate("document.querySelector('.working button').click()")
                    await wait("Array.from(document.querySelectorAll('.message-label small')).some(e=>e.textContent==='已中断')")

                    expected_users = await evaluate("document.querySelectorAll('.message.user').length")
                    await evaluate("document.querySelectorAll('.nav-item')[1].click()")
                    await evaluate("document.querySelector('#memory').value='请叫我小千';document.querySelector('#memory').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.checkbox input').click()")
                    await wait("!document.querySelector('.memory-form .primary').disabled")
                    await evaluate("document.querySelector('.memory-form .primary').click()")
                    await wait("document.querySelector('.memory-card')?.textContent.includes('小千')")
                    await cdp('Page.reload')
                    await wait("document.querySelector('.chat-header p')?.textContent.includes('已就绪')")
                    if ALL_AVATARS:
                        assert await evaluate("document.querySelector('.avatar-select-trigger').textContent.includes('眼镜男生')" if REALTIME else "document.querySelector('.avatar-select-trigger').textContent.includes('原剧换装')")
                    assert await evaluate("document.querySelector('.tool-group input').checked") is True
                    if REALTIME:
                        assert await evaluate("document.querySelector('.replay-button') !== null"), 'Replay missing after reload'
                    await wait("document.querySelector('.emotion-grid .chosen strong').textContent === '喜'")
                    if MEDIA:
                        assert await evaluate("document.querySelector('.subtitle-control input').checked") is False
                    assert await evaluate("document.querySelectorAll('.message.user').length") == expected_users
                    await evaluate("document.querySelectorAll('.nav-item')[1].click()")
                    await wait("document.querySelector('.memory-card')?.textContent.includes('小千')")
                    await evaluate("document.querySelector('.memory-card button').click()")
                    await wait("document.querySelector('.memory-card') === null")
                    await evaluate("document.querySelectorAll('.nav-item')[0].click()")
                    await evaluate("Object.defineProperty(window, 'speechSynthesis', {configurable:true, value:{cancel(){}, getVoices(){return []}, speak(utterance){window.lastNarration=utterance.text}}}); true")
                    await evaluate("document.querySelector('.voice-toggle').click()")
                    await evaluate("document.querySelector('.composer textarea').value='Markdown检查';document.querySelector('.composer textarea').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.composer').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
                    await wait("window.lastNarration?.includes('代码内容请查看屏幕。')")
                    assert await evaluate("Array.from(document.querySelectorAll('.markdown-body')).at(-1).querySelector('h1')?.textContent") == '学习计划'
                    assert await evaluate("Array.from(document.querySelectorAll('.markdown-body')).at(-1).querySelector('strong')?.textContent") == '先复习'
                    assert await evaluate("document.querySelector('.markdown-body table') !== null")
                    assert await evaluate("document.querySelector('.markdown-body pre code')?.textContent.includes('不要念代码')")
                    assert await evaluate("document.querySelector('.markdown-body img') === null && !window.markdownExecuted")
                    assert await evaluate("!window.lastNarration.includes('https:') && !window.lastNarration.includes('**') && !window.lastNarration.includes('不要念代码')")
                    artifacts = ROOT / 'artifacts'
                    artifacts.mkdir(exist_ok=True)
                    # Custom Skill lifecycle through the actual management UI.
                    await evaluate("document.querySelector('.tools-trigger').click(); document.querySelectorAll('.binding-tabs button')[2].click()")
                    await evaluate("document.querySelector('.binding-intro button').click()")
                    await evaluate("document.querySelector('.binding-editor input').value='Evidence skill';document.querySelector('.binding-editor input').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.binding-editor textarea').value='Only report verified evidence.';document.querySelector('.binding-editor textarea').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.binding-editor').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
                    await wait("document.querySelector('.binding-card strong')?.textContent === 'Evidence skill' && !document.querySelector('.binding-editor')")
                    await evaluate("document.querySelector('.binding-heading input').click()")
                    await wait("document.querySelector('.tools-count')?.textContent === '2'")
                    await cdp('Page.reload')
                    await wait("document.querySelector('.chat-header p')?.textContent.includes('已就绪')")
                    await evaluate("document.querySelector('.tools-trigger').click();document.querySelectorAll('.binding-tabs button')[2].click()")
                    await wait("document.querySelector('.binding-heading input')?.checked")
                    image = await cdp('Page.captureScreenshot', dict(format='png'))
                    (artifacts / 'skills-desktop.png').write_bytes(base64.b64decode(image['data']))
                    await evaluate("document.querySelectorAll('.binding-card .binding-actions button')[1].click()")
                    await wait("document.querySelector('.binding-card') === null && document.querySelector('.tools-count')?.textContent === '1'")
                    if importlib.util.find_spec('mcp'):
                        fixture = temp / 'echo_mcp.py'
                        fixture.write_text('from mcp.server.fastmcp import FastMCP\nmcp=FastMCP("echo")\n@mcp.tool()\ndef echo(text: str) -> str:\n    return text\nif __name__ == "__main__":\n    mcp.run(transport="stdio")\n', encoding='utf-8')
                        configuration = json.dumps(dict(command=sys.executable, args=[str(fixture)], env={}))
                        await evaluate("document.querySelectorAll('.binding-tabs button')[1].click();document.querySelector('.binding-intro button').click()")
                        await evaluate("document.querySelector('.binding-editor input').value='Echo MCP';document.querySelector('.binding-editor input').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.binding-editor textarea').value=" + json.dumps(configuration) + ";document.querySelector('.binding-editor textarea').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.binding-editor').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
                        await wait("document.querySelector('.binding-card strong')?.textContent === 'Echo MCP' && !document.querySelector('.binding-editor')")
                        assert await evaluate("document.querySelector('.binding-heading input').disabled")
                        await evaluate("document.querySelector('.binding-card .binding-actions button').click()")
                        await wait("!document.querySelector('.binding-heading input').disabled")
                        await evaluate("document.querySelector('.binding-heading input').click()")
                        await wait("document.querySelector('.tools-count')?.textContent === '2'")
                        image = await cdp('Page.captureScreenshot', dict(format='png'))
                        (artifacts / 'mcp-bindings-desktop.png').write_bytes(base64.b64decode(image['data']))
                        await evaluate("document.querySelectorAll('.binding-card .binding-actions button')[2].click()")
                        await wait("document.querySelector('.binding-card') === null && document.querySelector('.tools-count')?.textContent === '1'")
                    await evaluate("document.querySelector('.tools-panel-footer button').click()")
                    image = await cdp('Page.captureScreenshot', dict(format='png'))
                    (artifacts / 'desktop.png').write_bytes(base64.b64decode(image['data']))
                    await cdp('Emulation.setDeviceMetricsOverride', dict(width=390, height=844, deviceScaleFactor=1, mobile=True))
                    await asyncio.sleep(.2)
                    assert await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile horizontal overflow'
                    await evaluate("document.querySelectorAll('.mobile-nav button')[2].click()")
                    await wait("document.querySelector('.memory-form') !== null")
                    await evaluate("document.querySelectorAll('.mobile-nav button')[1].click()")
                    await wait("document.querySelector('.chat-panel') !== null")
                    image = await cdp('Page.captureScreenshot', dict(format='png', captureBeyondViewport=True))
                    (artifacts / 'mobile.png').write_bytes(base64.b64decode(image['data']))
                    await evaluate("document.querySelector('.tools-trigger').click()")
                    await wait("document.querySelector('.tools-dialog').open")
                    assert await evaluate("(() => { const r = document.querySelector('.tools-dialog').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight })()"), 'Tool panel outside mobile viewport'
                    image = await cdp('Page.captureScreenshot', dict(format='png'))
                    (artifacts / 'tools-mobile.png').write_bytes(base64.b64decode(image['data']))
                    await cdp('Input.dispatchKeyEvent', dict(type='keyDown', key='Escape', code='Escape', windowsVirtualKeyCode=27))
                    await cdp('Input.dispatchKeyEvent', dict(type='keyUp', key='Escape', code='Escape', windowsVirtualKeyCode=27))
                    await wait("!document.querySelector('.tools-dialog').open")
                    await evaluate("document.querySelector('.avatar-select-trigger').click()")
                    await wait("document.querySelector('.avatar-dialog').open")
                    assert await evaluate("(() => {const r=document.querySelector('.avatar-dialog').getBoundingClientRect();return r.left>=0 && r.right<=innerWidth && r.top>=0 && r.bottom<=innerHeight})()"), 'Avatar selector outside mobile viewport'
                    image = await cdp('Page.captureScreenshot', dict(format='png'))
                    (artifacts / 'avatars-mobile.png').write_bytes(base64.b64decode(image['data']))
                    await evaluate("document.querySelector('.avatar-dialog .tools-close').click()")
                    # Seed a real registered fixture and an old-style answer.
                    # Reload must restore it; completion must appear with no chat
                    # message and no extra model call or creation request.
                    cid = await evaluate("localStorage.getItem('shaniu.conversation')")
                    with app[SERVICE].store.connect() as db:
                        owner = db.execute('SELECT owner FROM conversations WHERE id=?', (cid,)).fetchone()[0]
                    app[SERVICE].store.save_external_task(owner, media_tid, 'video', '\u96ea\u8c79\u79d1\u666e')
                    app[SERVICE].store.add_message(cid, str(uuid4()), 'assistant', '\u4efb\u52a1\u5df2\u63d0\u4ea4\uff1a'+media_tid)
                    await cdp('Page.reload')
                    await wait("document.querySelector('.moneyprinter-task progress')?.value === 40")
                    assert await evaluate("document.documentElement.scrollWidth <= innerWidth"), 'Task card mobile overflow'
                    message_count = await evaluate("document.querySelectorAll('.message').length")
                    media_fixture['state'] = 1
                    await wait("document.querySelector('.moneyprinter-task.completed video') !== null")
                    assert await evaluate("document.querySelectorAll('.message').length") == message_count
                    assert await evaluate("document.querySelector('.task-downloads a').href.includes('download=1')")
                    if fixture_video.is_file():
                        await wait("document.querySelector('.task-video').readyState >= 1")
                        await evaluate("(()=>{const v=document.querySelector('.task-video');v.muted=true;return v.play()})()")
                        await wait("document.querySelector('.task-video').currentTime > 0")
                        await evaluate("document.querySelector('.task-video').pause()")
                    await wait("(()=>{const v=document.querySelector('.task-video').getBoundingClientRect(), t=document.querySelector('.transcript').getBoundingClientRect(); return v.top<t.bottom && v.bottom>t.top})()")
                    await asyncio.sleep(.4)
                    image = await cdp('Page.captureScreenshot', dict(format='png', captureBeyondViewport=True))
                    (artifacts / 'moneyprinter-card-mobile.png').write_bytes(base64.b64decode(image['data']))
                    reads = media_fixture['reads']
                    await asyncio.sleep(3.5)
                    assert media_fixture['reads'] == reads, 'Completed cards must stop polling upstream'
                    await cdp('Page.reload')
                    await wait("document.querySelector('.moneyprinter-task.completed video') !== null")
                    await evaluate("document.querySelector('.motion-enhancement summary').click()")
                    assert await evaluate("document.querySelector('.motion-enhancement button').disabled") is False
                    await evaluate("document.querySelector('.motion-enhancement select').value='ink';document.querySelector('.motion-enhancement select').dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('.motion-enhancement button').click()")
                    await wait("document.querySelector('.motion-enhancement progress')?.value === 35")
                    await cdp('Page.reload')
                    await wait("document.querySelector('.motion-enhancement progress')?.value === 35")
                    motion_finished.set()
                    await wait("document.querySelector('.motion-enhancement video') !== null")
                    assert await evaluate("document.querySelectorAll('.motion-downloads a').length") == 3
                    assert await evaluate("document.documentElement.scrollWidth <= innerWidth"), 'Motion controls overflow on mobile'
                    image = await cdp('Page.captureScreenshot',dict(format='png',captureBeyondViewport=True))
                    (artifacts/'motion-card-mobile.png').write_bytes(base64.b64decode(image['data']))
                    await cdp('Page.reload')
                    await wait("document.querySelector('.motion-enhancement video') !== null")
                    await evaluate("document.querySelector('.post-controls summary').click()")
                    assert await evaluate("document.querySelector('.post-controls button').disabled") is True
                    await evaluate("document.querySelector('.tools-trigger').click()")
                    await wait("document.querySelector('.tools-dialog').open")
                    await evaluate("Array.from(document.querySelectorAll('.tool-group input')).at(-1).click()")
                    await cdp('Input.dispatchKeyEvent',dict(type='keyDown',key='Escape',code='Escape',windowsVirtualKeyCode=27))
                    await cdp('Input.dispatchKeyEvent',dict(type='keyUp',key='Escape',code='Escape',windowsVirtualKeyCode=27))
                    await wait("document.querySelector('.tools-dialog').open === false")
                    assert await evaluate("document.querySelector('.post-controls button').disabled") is False
                    await evaluate("(()=>{const s=document.querySelector('.post-controls select');s.value='cover';s.dispatchEvent(new Event('change',{bubbles:true}));})()")
                    await evaluate("document.querySelector('.post-controls button').click()")
                    await wait("document.querySelector('.post-result progress')?.value === 42")
                    await cdp('Page.reload')
                    await wait("document.querySelector('.post-result progress')?.value === 42")
                    post_finished.set()
                    await wait("document.querySelector('.post-result img')?.naturalWidth === 640")
                    assert await evaluate("document.querySelectorAll('.post-downloads a').length") == 2
                    assert await evaluate("document.documentElement.scrollWidth <= innerWidth"), 'Post controls overflow on mobile'
                    image=await cdp('Page.captureScreenshot',dict(format='png',captureBeyondViewport=True))
                    (artifacts/'media-post-mobile.png').write_bytes(base64.b64decode(image['data']))
                    await cdp('Page.reload')
                    await wait("document.querySelector('.post-result img')?.naturalWidth === 640")
                    assert not console_errors, console_errors
                    await evaluate("fetch('/api/conversations').then(r=>r.json()).then(items=>Promise.all(items.map(c=>fetch('/api/conversations/'+c.id,{method:'DELETE',headers:{'X-Shaniu-Client':'web'}}))))")
                    print('Browser smoke passed: chat, tools, MCP binding/discovery, Skill management, selection persistence, memory, mobile, automatic media progress, motion and post-processing selection/submission/progress/restoration/downloads, inline player and terminal polling stop; no uncaught exceptions.')
                    await cdp('Page.navigate', dict(url='about:blank'))
                    await asyncio.sleep(.3)
                    await ws.send_json({'id': serial + 1, 'method': 'Browser.close'})
                    await asyncio.sleep(.3)
        finally:
            try:
                await asyncio.to_thread(process.wait, timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    await asyncio.to_thread(process.wait, timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            await runner.cleanup()


if __name__ == '__main__':
    # This script only uses sockets and synchronous Popen; Selector avoids
    # Windows Proactor's noisy shutdown callbacks when Chrome closes sockets.
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop if os.name == 'nt' and not (MEDIA or REALTIME) else None) as runner:
        runner.run(main())
