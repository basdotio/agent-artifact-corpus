"""Real offline rendering through the HTTP tool and task-card API; no paid APIs."""
import asyncio
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import imageio_ffmpeg
from aiohttp import CookieJar, FormData, web
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from shaniu.config import Settings
from shaniu.motion import parse_srt
from shaniu.server import SERVICE, create_app


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=Path(os.getenv('SHANIU_TEST_MEDIA_DIR', str(ROOT / 'data/test-fixtures/moneyprinter'))))
    parser.add_argument('--landscape', action='store_true')
    args = parser.parse_args()
    target = ROOT/'artifacts'/('motion-check-'+uuid4().hex[:8])
    target.mkdir(parents=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    fixture = args.fixture.expanduser().resolve()
    landscape = args.landscape
    if fixture.is_dir():
        command = [ffmpeg,'-y','-v','error','-i',str(fixture/'combined-1.mp4'),'-t','8','-an']
        if not landscape:
            command += ['-vf','crop=ih*9/16:ih,scale=360:640']
        subprocess.run(command+['-c:v','libx264',str(target/'base.mp4')],check=True)
        subprocess.run([ffmpeg,'-y','-v','error','-i',str(fixture/'audio.mp3'),'-t','8',str(target/'voice.wav')],check=True)
        source = (fixture/'subtitle.srt').read_text(encoding='utf-8-sig')
        cues = [cue for cue in parse_srt(source) if cue['t0']<7.9]
        def stamp(value):
            ms=round(value*1000); return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
        subtitle='\n\n'.join(f"{i+1}\n{stamp(c['t0'])} --> {stamp(min(c['t1'],8))}\n{c['zh']}" for i,c in enumerate(cues))
    else:
        subprocess.run([ffmpeg,'-y','-v','error','-f','lavfi','-i','testsrc2=size=360x640:rate=24','-t','3','-c:v','libx264',str(target/'base.mp4')],check=True)
        subprocess.run([ffmpeg,'-y','-v','error','-f','lavfi','-i','sine=frequency=300:duration=3',str(target/'voice.wav')],check=True)
        subtitle='1\n00:00:00,000 --> 00:00:02,800\n雪豹生活在高山地区。'
    (target/'source.srt').write_text(subtitle,encoding='utf-8')
    tid = str(uuid4())
    async def status(request):
        return web.json_response(dict(status=200,data=dict(state=1,progress=100,videos=[f'/tasks/{tid}/final.mp4'],combined_videos=[f'/tasks/{tid}/base.mp4'],audio_file=f'/tasks/{tid}/voice.wav',subtitle_path=f'/tasks/{tid}/source.srt')))
    async def asset(request):
        return web.FileResponse(target/request.match_info['filename'])
    upstream = web.Application()
    upstream.router.add_get('/api/v1/tasks/{taskid}',status)
    upstream.router.add_get('/tasks/{taskid}/{filename}',asset)
    async with TestServer(upstream) as remote:
        app = create_app(Settings(database=target/'check.db',moneyprinter_enabled=True,moneyprinter_url=str(remote.make_url('')).rstrip('/')))
        async with TestClient(TestServer(app),cookie_jar=CookieJar(unsafe=True)) as client:
            await client.get('/api/health')
            owner = next(c.value for c in client.session.cookie_jar if c.key=='shaniu_owner')
            service = app[SERVICE]
            cid = service.store.create(owner,'cool')['id']
            mid = service.store.add_message(cid,str(uuid4()),'assistant','测试任务')
            service.store.save_external_task(owner,tid,'video','雪豹：雪山中的生存高手')
            service.store.link_external_task(owner,tid,mid)
            headers={'X-Shaniu-Client':'web'}
            options={}
            if landscape:
                # An explicit test tone validates upload and sidechain mixing;
                # this is a test fixture, not an automatically selected song.
                subprocess.run([ffmpeg,'-y','-v','error','-f','lavfi','-i','sine=frequency=160:duration=12','-af','volume=0.12',str(target/'music.wav')],check=True)
                form=FormData(); form.add_field('file',(target/'music.wav').read_bytes(),filename='test-tone.wav',content_type='audio/wav')
                upload=await client.post('/api/motion/music',data=form,headers=headers)
                assert upload.status==200,await upload.text()
                options['music_id']=(await upload.json())['music_id']
            response=await client.post('/api/agent/tools/moneyprinter_enhance',json=dict(task_id=tid,style='ink' if landscape else 'clean',subtitles=not landscape,sound_effects=not landscape,enabled_tool_groups=['moneyprinter'],**options),headers=headers)
            assert response.status==200,await response.text()
            job=(await response.json())['enhancement']['job_id']
            await asyncio.wait_for(service.moneyprinter.motion.tasks[job],300)
            result=service.moneyprinter.motion.latest(owner,tid)
            assert result['status']=='completed',result
            response=await client.get(f'/api/conversations/{cid}/media-tasks')
            task=(await response.json())['tasks'][0]
            response=await client.get(task['enhancement']['video_url'],headers={'Range':'bytes=0-31'})
            assert response.status==206,response.status
            assert len(await response.read())==32
            response=await client.get(task['enhancement']['project_url'])
            assert response.status==200
            report=await (await client.get(task['enhancement']['report_url'])).json()
            assert report['completeDecode'] and report['voiceRetimed'] is False
            client.session.cookie_jar.clear()
            assert (await client.get(task['enhancement']['video_url'])).status==404
            print(json.dumps(dict(status='passed',job_id=job,layout='landscape' if landscape else 'portrait',directory=str(target/'motion'/job),report=report),ensure_ascii=False,indent=2))


if __name__=='__main__':
    asyncio.run(main())
