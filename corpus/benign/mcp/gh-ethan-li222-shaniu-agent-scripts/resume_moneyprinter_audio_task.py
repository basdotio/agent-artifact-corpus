"""Resume a registered audio-failed task using saved script/terms, without new LLM calls.

Run with the same interpreter/config/storage as start_moneyprinter.py, while no
other MoneyPrinter task is processing. This is a local maintenance command.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid
from project_paths import moneyprinter_project

ROOT = Path(__file__).resolve().parents[1]


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task_id')
    parser.add_argument('--project', type=Path, default=moneyprinter_project())
    args = parser.parse_args()
    tid = str(uuid.UUID(args.task_id))
    storage = Path(os.getenv('SHANIU_MPT_STORAGE', str(ROOT/'data/moneyprinter'))).resolve()
    with sqlite3.connect(storage/'task-state.sqlite3') as db:
        tasks = {key: json.loads(raw) for key, raw in db.execute('SELECT task_id,data FROM tasks')}
    if any(value.get('state') not in {-1, 1} for value in tasks.values()):
        raise SystemExit('Another task is processing; resume deferred')
    previous = tasks.get(tid, {})
    if previous.get('state') != -1 or previous.get('failure_reason') not in {'audio_failed', 'audio_fallback_failed', 'audio_online_failed'}:
        raise SystemExit('Only audio-failed tasks can be resumed')
    with sqlite3.connect(ROOT/'data/shaniu.sqlite3') as db:
        if not db.execute('SELECT 1 FROM external_tasks WHERE task_id=?', (tid,)).fetchone():
            raise SystemExit('Task is not registered in Shaniu')
    saved = json.loads((storage/'tasks'/tid/'script.json').read_text(encoding='utf-8'))
    if not saved.get('script') or not saved.get('search_terms'):
        raise SystemExit('Saved script and search terms are required; no LLM regeneration allowed')
    project = args.project.resolve()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(project))
    os.chdir(project)
    import moneyprinter_host as host
    params = host.VideoParams(**{**saved['params'], 'video_script': saved['script'], 'video_terms': saved['search_terms']})
    host.state.state.update_task(tid, progress=20, failure_reason=None)
    # Unfreeze the failed result cached by the chat task card.
    with sqlite3.connect(ROOT/'data/shaniu.sqlite3') as db:
        db.execute('DELETE FROM external_task_results WHERE task_id=?', (tid,))
    host.start(tid, params)
    result = host.state.state.get_task(tid)
    print(json.dumps({key: result.get(key) for key in ['task_id', 'state', 'progress', 'shaniu_stage', 'failure_reason', 'speech_provider']}, ensure_ascii=True))


if __name__ == '__main__':
    main()
