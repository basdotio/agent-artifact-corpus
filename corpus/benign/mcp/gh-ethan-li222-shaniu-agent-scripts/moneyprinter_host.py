"""External ASGI entrypoint; compatibility wrapper exists only in this process.

MoneyPrinterTurbo's AudioRequest/SubtitleRequest lack VideoParams fields consumed
unconditionally by task.start (e.g. video_concat_mode). Normalize before handing
off; never writes or replaces any file in the original checkout.
"""
import os
from pathlib import Path
from moneyprinter_runtime import configure_project, subtitle_font
from moneyprinter_compat import install_edge_compat

install_edge_compat()

configure_project(Path.cwd())

from moneyprinter_llm import load_config
from app.config import config

llm_config = load_config()
llm_config.apply(config.app)

# Redirect generated files before the original ASGI app mounts its task directory.
# Fonts/songs remain read-only resources of the original checkout.
from app.utils import utils

STORAGE = Path(os.getenv('SHANIU_MPT_STORAGE', str(Path(__file__).resolve().parents[1] / 'data/moneyprinter'))).resolve()


def storage_dir(sub_dir='', create=False):
    path = STORAGE / sub_dir
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return str(path)


utils.storage_dir = storage_dir

from app.asgi import app
from app.services import task
from app.models.schema import VideoParams, VideoTransitionMode
from app.services import state
from loguru import logger
from moneyprinter_state import PersistentState, track_stage
from moneyprinter_speech import install as install_speech

install_speech(task.voice)

state.state = PersistentState(STORAGE / 'task-state.sqlite3')
for function, stage in [('generate_script', 'script'), ('generate_terms', 'terms'), ('generate_audio', 'audio'), ('generate_subtitle', 'subtitle'), ('get_video_materials', 'materials'), ('generate_final_videos', 'render')]:
    setattr(task, function, track_stage(getattr(task, function), stage, state.state))


@app.get('/shaniu/health')
def shaniu_health():
    return dict(wrapper='shaniu', version=3, persistent_tasks=True, staged_errors=True, llm=llm_config.public())

# The upstream root static mount otherwise shadows externally added routes.
app.router.routes.insert(0, app.router.routes.pop())

original_start = task.start


def normalize_params(params, stop_at, video_params_type):
    if isinstance(params, video_params_type):
        return params
    if stop_at not in {'audio', 'subtitle'}:
        raise ValueError('Unsupported task parameters')
    values = params.model_dump()
    values.update(video_subject='Shaniu 音频字幕任务', video_source='local')
    if stop_at == 'subtitle':
        values['subtitle_enabled'] = True
    return video_params_type(**values)


def start(task_id, params, stop_at='video'):
    try:
        params = normalize_params(params, stop_at, VideoParams)
        if stop_at == 'video' and params.subtitle_enabled:
            params.font_name = subtitle_font(params.font_name, utils.font_dir())
        if stop_at == 'video' and params.bgm_type == 'random' and not params.bgm_file and not list(Path(utils.song_dir()).glob('*.mp3')):
            # The public bundle does not redistribute unlicensed music assets.
            params.bgm_type = ''
            logger.warning('No local background music installed; rendering without BGM')
        # combine_videos accesses .value even when the HTTP default is None.
        if params.video_transition_mode is None:
            params.video_transition_mode = VideoTransitionMode.none
        return original_start(task_id, params, stop_at=stop_at)
    except Exception as error:
        # The original task manager otherwise leaves crashed tasks processing
        # forever. Keep a truthful terminal state without exposing exception data.
        previous = state.state.get_task(task_id) or {}
        state.state.update_task(task_id, state=-1, failure_reason=previous.get('failure_reason', 'generation_failed'))
        logger.warning('Shaniu external task failed ({})', type(error).__name__)
        return None


task.start = start
