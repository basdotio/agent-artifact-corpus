"""Stateless, signed continuation over three clean streams; no disk registry."""
import base64
import hmac
import json

from .errors import OmniError
from .models import serialize

REF_LIMIT = 96


def stale_cursor():
    return OmniError('STALE_CURSOR', 'Cursor is invalid or page content changed; start a fresh observe without cursor.', 4)


def paginate(source, candidates, metadata, tab_id, max_bytes, pretty, cursor=None):
    content = source['content']
    streams = {kind: [c for c in candidates if c[2] == kind] for kind in ('links', 'controls')}
    # Only sanitized extraction + exact node identities enter this keyed fingerprint.
    # No layout coordinates, title/clock, editable values or raw AX/snapshot data.
    key = bytes.fromhex(metadata['cursor_key'])
    state = json.dumps([metadata['id'], tab_id, metadata['url'], content, candidates, source['coverage']],
                       ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    digest = hmac.digest(key, state, 'sha256')

    def sign(payload):
        return hmac.digest(key, digest + payload, 'sha256')

    def encode(position, turn):
        payload = serialize([1, *position, turn]).encode()
        return base64.urlsafe_b64encode(payload + sign(payload)).decode().rstrip('=')

    position, turn = [0, 0, 0], 0
    if cursor is not None:
        try:
            if not isinstance(cursor, str) or len(cursor) > 512:
                raise ValueError
            raw = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
            payload, tag = raw[:-32], raw[-32:]
            if not hmac.compare_digest(sign(payload), tag):
                raise ValueError
            parsed = json.loads(payload)
            if not isinstance(parsed, list) or len(parsed) != 5 or parsed[0] != 1 or any(type(n) is not int for n in parsed):
                raise ValueError
            position, turn = parsed[1:4], parsed[4]
            if not 0 <= turn < 3:
                raise ValueError
        except (ValueError, TypeError, UnicodeError):
            raise stale_cursor() from None
    lengths = [len(content), len(streams['links']), len(streams['controls'])]
    if any(not 0 <= p <= n for p, n in zip(position, lengths)):
        raise stale_cursor()
    start = position.copy()
    chosen = []
    result = {**source, 'content': '', 'links': [], 'controls': [],
              'coverage': dict(source['coverage']), 'has_more': True, 'next_cursor': None}
    extraction_cut = source['coverage']['content_truncated']
    result['coverage']['extraction_content_truncated'] = extraction_cut

    def refresh():
        more = any(p < n for p, n in zip(position, lengths))
        result['has_more'] = more
        result['next_cursor'] = encode(position, turn) if more else None
        coverage = result['coverage']
        coverage['content_truncated'] = extraction_cut or len(result['content']) < len(content)
        for kind in ('links', 'controls'):
            coverage[kind + '_omitted'] = source['coverage'][kind + '_omitted'] + len(streams[kind]) - len(result[kind])
        coverage['positions'] = dict(zip(('content', 'links', 'controls'), [[a, b] for a, b in zip(start, position)]))
        result['truncated'] = (coverage['content_truncated'] or coverage['processing_limited'] or
                               bool(coverage['links_omitted'] or coverage['controls_omitted']))
        return len(serialize(result, pretty).encode()) + 1

    if refresh() > max_bytes:
        raise OmniError('OUTPUT_BUDGET', 'Observation metadata exceeds the budget; raise --max-bytes.', 2)
    idle = 0
    while any(p < n for p, n in zip(position, lengths)):
        stream = turn
        if position[stream] >= lengths[stream] or stream > 0 and len(chosen) >= REF_LIMIT:
            turn = (turn + 1) % 3
            idle += 1
            if idle >= 3:
                break
            continue
        idle = 0
        old_position, old_content = position.copy(), result['content']
        if stream == 0:
            chunk = content[position[0]:position[0] + 256]
            result['content'] += chunk
            position[0] += len(chunk)
        else:
            kind = ('links', 'controls')[stream - 1]
            candidate = streams[kind][position[stream]]
            result[kind].append({'ref': metadata['id'] + '.n' + '9' * 20, **candidate[3]})
            position[stream] += 1
        turn = (turn + 1) % 3
        if refresh() > max_bytes:
            position[:] = old_position
            result['content'] = old_content
            if stream > 0:
                result[kind].pop()
            turn = stream  # Give the blocked stream first priority next response.
            refresh()
            if stream == 0:
                lo, hi = 0, len(chunk)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    result['content'] = old_content + chunk[:mid]
                    position[0] = old_position[0] + mid
                    if refresh() <= max_bytes:
                        lo = mid
                    else:
                        hi = mid - 1
                result['content'] = old_content + chunk[:lo]
                position[0] = old_position[0] + lo
                refresh()
            if position == start:
                raise OmniError('OUTPUT_BUDGET', 'One observation item exceeds the budget; raise --max-bytes. No item was clipped.', 2)
            break
        if stream > 0:
            chosen.append(candidate)
    refresh()
    return result, chosen
