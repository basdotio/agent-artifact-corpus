"""Optional local face-mesh preparation; inspect dependencies before hosted work."""
from pathlib import Path
import subprocess,shutil
ROOT=Path(__file__).resolve().parent

def run(src,folder,status=print):
    from pipeline import normalize
    from audio_workflow import separate,prepare_seedance_video
    from preflight import preflight_job,bind_preparation
    from job_state import job_lock,atomic_json
    report=preflight_job(src,'face_mesh')
    folder=Path(folder)
    with job_lock(folder):
        identity=bind_preparation(folder,report)
        src=folder/'upload.mp4'
        status('Normalizing video');meta=normalize(src,folder/'original.mp4',report['source'])
        status('Tracking face mesh locally · no depth or SAM')
        subprocess.run([report['mesh_python'],str(ROOT/'mesh_worker.py'),str(folder)],check=True)
        separate(src,folder,status)
        prepare_seedance_video(folder)
        meta.update(preparation_identity=identity,source_identity=report['source']['sha256'])
        atomic_json(folder/'manifest.json',meta)
        atomic_json(folder/'preparation-state.json',{'identity':identity,'state':'prepared'})
        status('Face mesh ready · review tracking and pitched audio')


def run_depth(src,folder,prompt='person',provider='replicate',status=print):
    from pipeline import _run
    from audio_workflow import prepare_seedance_video
    from preflight import preflight_job,bind_preparation
    from job_state import job_lock,atomic_json
    report=preflight_job(src,'depth_mesh',provider)
    folder=Path(folder)
    with job_lock(folder):
        identity=bind_preparation(folder,report,prompt)
        _run(folder/'upload.mp4',folder,prompt,provider,status,mode='depth_mesh',preflight_report=report)
        shutil.copy2(folder/'composite-silent.mp4',folder/'depth-composite-silent.mp4')
        status('Adding face mesh from original video onto depth composite')
        subprocess.run([report['mesh_python'],str(ROOT/'mesh_worker.py'),str(folder),'--depth'],check=True)
        prepare_seedance_video(folder)
        atomic_json(folder/'preparation-state.json',{'identity':identity,'state':'prepared'})
        status('Depth + face mesh ready · full mask and facial tracking review required')
