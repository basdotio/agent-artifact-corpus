import json
import logging
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

_LOOPS_DIR = Path(__file__).parents[1] / 'loops'
_EXAMPLE = _LOOPS_DIR / 'config.example.json'


def _example_config():
    return json.loads(_EXAMPLE.read_text(encoding='utf-8'))


def test_public_example_uses_only_relative_input_roots():
    config = _example_config()
    roots = config['watch_paths']
    assert roots == ['./input']
    assert all(not Path(root).is_absolute() for root in roots)


def test_public_example_ollama_url_reaches_the_generate_endpoint():
    # call_ollama POSTs to ollama_url exactly as configured, so the example
    # must name the full /api/generate endpoint, not only the server address.
    if str(_LOOPS_DIR) not in sys.path:
        sys.path.insert(0, str(_LOOPS_DIR))
    import triage_loop

    settings = triage_loop.resolve_llm_settings(_example_config())
    posted = []

    def fake_post(url, json=None, timeout=None, allow_redirects=True):
        posted.append(url)
        reply = Mock(status_code=200)
        reply.json.return_value = {'response': 'NONE'}
        return reply

    with patch.object(triage_loop.requests, 'post', side_effect=fake_post):
        result = triage_loop.call_ollama(settings, 'PROMPT',
                                         logging.getLogger('t'))
    assert result.status == 'ok'
    assert len(posted) == 1
    assert urlsplit(posted[0]).path == '/api/generate'
