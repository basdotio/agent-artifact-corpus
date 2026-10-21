"""Real post-processing via HTTP tools and isolated workers, using existing media."""
import asyncio
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import imageio_ffmpeg
from aiohttp import CookieJar, web
from aiohttp.test_utils import TestClient, TestServer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from shaniu.config import Settings
from shaniu.motion import parse_srt
from shaniu.server import SERVICE, create_app


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=Path(os.getenv('SHANIU_TEST_MEDIA_DIR', str(ROOT / 'data/test-fixtures/moneyprinter'))))
    args = parser.parse_args()
    target=ROOT/'artifacts'/('media-post-check-'+uuid4().hex[:8]); target.mkdir(parents=True)
    fixture=args.fixture.expanduser().resolve()
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    if not (fixture/'final-1.mp4').is_file():
        raise SystemExit('Use --fixture to select a completed video directory with final-1.mp4, combined-1.mp4, audio.mp3 and subtitle.srt; no paid generation is performed')
    for original,name in [('final-1.mp4','final.mp4'),('combined-1.mp4','base.mp4')]:
        subprocess.run([ffmpeg,'-y','-v','error','-i',str(fixture/original),'-t','6','-vf','scale=640:360','-c:v','libx264','-preset','fast',str(target/name)],check=True)
    subprocess.run([ffmpeg,'-y','-v','error','-i',str(fixture/'audio.mp3'),'-t','6',str(target/'voice.wav')],check=True)
    cues=[c for c in parse_srt((fixture/'subtitle.srt').read_text(encoding='utf-8-sig')) if c['t0']<6]
    def stamp(value):
        ms=round(value*1000); return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
    (target/'source.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(c['t0'])} --> {stamp(min(c['t1'],6))}\n{c['zh']}" for i,c in enumerate(cues)),encoding='utf-8')
    tid=str(uuid4())
    async def status(request):
        return web.json_response(dict(status=200,data=dict(state=1,progress=100,videos=[f'/tasks/{tid}/final.mp4'],combined_videos=[f'/tasks/{tid}/base.mp4'],audio_file=f'/tasks/{tid}/voice.wav',subtitle_path=f'/tasks/{tid}/source.srt')))
    async def asset(request): return web.FileResponse(target/request.match_info['filename'])
    upstream=web.Application(); upstream.router.add_get('/api/v1/tasks/{taskid}',status); upstream.router.add_get('/tasks/{taskid}/{filename}',asset)
    results=[]
    async with TestServer(upstream) as remote:
        app=create_app(Settings(database=target/'check.db',moneyprinter_enabled=True,moneyprinter_url=str(remote.make_url('')).rstrip('/')))
        async with TestClient(TestServer(app),cookie_jar=CookieJar(unsafe=True)) as client:
            await client.get('/api/health'); owner=next(c.value for c in client.session.cookie_jar if c.key=='shaniu_owner')
            service=app[SERVICE]; cid=service.store.create(owner,'cool')['id']; mid=service.store.add_message(cid,str(uuid4()),'assistant','后期测试')
            service.store.save_external_task(owner,tid,'video','大熊猫'); service.store.link_external_task(owner,tid,mid)
            cases=[dict(operation='cut',start=1,end=4),dict(operation='cut',start=1,end=4,source='clean',subtitles=False),
                   dict(operation='cut',start=1,end=4,source='clean',subtitles=True),dict(operation='reframe',aspect='9:16',mode='blur'),
                   dict(operation='reframe',aspect='1:1',mode='crop'),dict(operation='compress',crf=30),dict(operation='cover',time=2),
                   *[dict(operation='subtitle',format=fmt) for fmt in ['srt','vtt','ass']],dict(operation='review')]
            for case in cases:
                response=await client.post('/api/agent/tools/media_postprocess',json=dict(task_id=tid,enabled_tool_groups=['media_post'],**case),headers={'X-Shaniu-Client':'web'})
                value=await response.json(); assert response.status==200,value
                job_id=value['postprocess']['job_id']
                deadline=asyncio.get_running_loop().time()+240
                while True:
                    task=(await (await client.get(f'/api/conversations/{cid}/media-tasks')).json())['tasks'][0]
                    job=next(j for j in task['postprocess'] if j['job_id']==job_id)
                    if job['status'] in {'completed','failed'}: break
                    assert asyncio.get_running_loop().time()<deadline,'Worker timeout'
                    await asyncio.sleep(.4)
                if job['status']!='completed':
                    print('Failed job log:',service.moneyprinter.post.root/job_id/'worker.log',flush=True)
                    raise AssertionError(job)
                for artifact in job['artifacts']:
                    fetched=await client.get(artifact['url']); assert fetched.status==200; assert await fetched.read()
                video=next((a for a in job['artifacts'] if a['filename']=='result.mp4'),None)
                if video:
                    fetched=await client.get(video['url'],headers={'Range':'bytes=0-9'}); assert fetched.status==206
                report=json.loads((service.moneyprinter.post.root/job_id/'report.json').read_text(encoding='utf-8'))
                results.append(dict(case=case,job_id=job_id,report=report))
                print(json.dumps(dict(case=case,status='passed'),ensure_ascii=True),flush=True)
    (target/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Real offline media checks passed:',target,flush=True)


if __name__=='__main__': asyncio.run(main())
