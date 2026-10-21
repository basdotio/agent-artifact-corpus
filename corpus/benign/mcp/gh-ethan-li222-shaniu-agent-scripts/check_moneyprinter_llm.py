"""Opt-in real script/terms check. Calls the configured LLM, creates no video task."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from moneyprinter_llm import load_config
from project_paths import moneyprinter_project
from moneyprinter_runtime import configure_project


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=moneyprinter_project())
    args = parser.parse_args()
    project = args.project.resolve()
    config_path = configure_project(project)
    before = hashlib.sha256(config_path.read_bytes()).hexdigest()
    settings = load_config()
    os.chdir(project)
    sys.path.insert(0, str(project))
    from app.config import config
    settings.apply(config.app)
    from app.services import llm
    subject = '\u96ea\u8c79\u79d1\u666e\uff0c\u4e00\u6bb5\u7b80\u77ed\u4e2d\u6587\u65c1\u767d\uff0c\u7ea6100\u5b57'
    calls = 0
    original_response = llm._generate_response
    def response(prompt):
        nonlocal calls
        calls += 1
        return original_response(prompt)
    llm._generate_response = response
    script = llm.generate_script(subject, language='zh-CN', paragraph_number=1)
    assert script and not script.startswith('Error:'), 'MoneyPrinter script generation failed'
    terms = llm.generate_terms(subject, script, amount=3)
    assert isinstance(terms, list) and terms and all(isinstance(t, str) and t for t in terms), 'MoneyPrinter search terms generation failed'
    assert hashlib.sha256(config_path.read_bytes()).hexdigest() == before, 'Original config changed'
    report = dict(ok=True, llm=settings.public(), native_moneyprinter_calls=calls,
                  script=script, terms=terms, original_config_unchanged=True, video_task_created=False)
    target = Path(__file__).resolve().parents[1] / 'artifacts/moneyprinter-llm-check.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(ok=True, llm=settings.public(), native_moneyprinter_calls=calls,
                          script_characters=len(script), terms_count=len(terms), original_config_unchanged=True)))


if __name__ == '__main__':
    main()
