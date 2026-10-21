#!/usr/bin/env python3
"""repo-multiverse helper: live sessions, main timelines and the workers under them, the timeline tree.

Reads ~/.claude/sessions and git. Writes only ~/.claude/multiverse/<repo-key>/, never inside the repo.
Run with --help for subcommands.
"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import time

SESS_DIR = os.path.expanduser('~/.claude/sessions')
STATE_HOME = os.environ.get('MULTIVERSE_HOME') or os.path.expanduser('~/.claude/multiverse')
NAME_PREFIX = os.environ.get('MULTIVERSE_NAME_PREFIX', 'loki-agent-')


def git(*args, cwd=None, check=True):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f'git {" ".join(args)} failed: {r.stderr.strip()}')
    return r.stdout.rstrip()


def repo_key():
    common = git('rev-parse', '--path-format=absolute', '--git-common-dir')
    root = os.path.dirname(common) if os.path.basename(common) == '.git' else common
    return re.sub(r'[^A-Za-z0-9]', '-', root)


def mv_dir():
    d = os.environ.get('MULTIVERSE_DIR') or os.path.join(STATE_HOME, repo_key())
    os.makedirs(os.path.join(d, 'sessions'), exist_ok=True)
    return d


def load_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def config():
    return load_json(os.path.join(mv_dir(), 'config.json'), {})


def worktrees():
    out, cur = [], {}
    for line in git('worktree', 'list', '--porcelain').splitlines() + ['']:
        if not line:
            if cur:
                out.append(cur)
            cur = {}
            continue
        key, _, val = line.partition(' ')
        if key == 'worktree':
            cur['path'] = val
        elif key == 'branch':
            cur['branch'] = val.removeprefix('refs/heads/')
        elif key in ('detached', 'prunable', 'locked'):
            cur[key] = val or True
        elif key == 'HEAD':
            cur['head'] = val[:7]
    return out


def main_path():
    return worktrees()[0]['path']


def alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, ValueError, TypeError):
        return True


def live_sessions():
    out = []
    for f in glob.glob(os.path.join(SESS_DIR, '*.json')):
        s = load_json(f)
        if s and alive(s.get('pid')):
            out.append(s)
    return out


def live_by_sid():
    return {s.get('sessionId'): s for s in live_sessions() if s.get('sessionId')}


def my_session():
    pid = os.environ.get('CLAUDE_PID')
    candidates = [pid] if pid else []
    p = os.getppid()
    for _ in range(8):
        candidates.append(str(p))
        r = subprocess.run(['ps', '-o', 'ppid=', '-p', str(p)], capture_output=True, text=True)
        if not r.stdout.strip():
            break
        p = int(r.stdout.strip())
    for c in candidates:
        s = load_json(os.path.join(SESS_DIR, f'{c}.json'))
        if s:
            return s
    sys.exit('cannot find this session in ~/.claude/sessions (run inside a Claude Code session)')


def reg_path(sid):
    return os.path.join(mv_dir(), 'sessions', f'{sid}.json')


def legacy_sacred():
    return load_json(os.path.join(mv_dir(), 'sacred.json'))


def registrations():
    regs, names = {}, {}
    for f in sorted(glob.glob(os.path.join(mv_dir(), 'sessions', '*.json'))):
        r = load_json(f)
        if not r:
            continue
        stem = os.path.basename(f)[:-5]
        sid = r.get('session') or stem
        if sid in regs and stem != sid:
            continue
        r = dict(r, session=sid)
        if r.get('role') == 'gatekeeper':
            r['role'] = 'timeline'
        regs[sid] = r
        for n in [r.get('name')] + r.get('aliases', []):
            if n:
                names[n] = sid
    h = legacy_sacred()
    if h and h.get('session'):
        r = regs.setdefault(h['session'], {'session': h['session'], 'name': h.get('name'), 'branches': []})
        r['role'] = 'timeline'
    for r in regs.values():
        if r.get('role') == 'worker' and not r.get('timeline') and r.get('gatekeeper'):
            r['timeline'] = names.get(r['gatekeeper'])
            r.setdefault('timeline_name', r['gatekeeper'])
    return regs


def save_reg(r):
    sid = r['session']
    r.pop('gatekeeper', None)
    r['updated'] = now()
    save_json(reg_path(sid), r)
    for f in glob.glob(os.path.join(mv_dir(), 'sessions', '*.json')):
        if os.path.basename(f)[:-5] != sid and (load_json(f) or {}).get('session') == sid:
            os.remove(f)
    h = legacy_sacred()
    if h and h.get('session') == sid:
        os.remove(os.path.join(mv_dir(), 'sacred.json'))


def drop_reg(sid):
    for f in glob.glob(os.path.join(mv_dir(), 'sessions', '*.json')):
        if os.path.basename(f)[:-5] == sid or (load_json(f) or {}).get('session') == sid:
            os.remove(f)
    h = legacy_sacred()
    if h and h.get('session') == sid:
        os.remove(os.path.join(mv_dir(), 'sacred.json'))


def name_of(sid, regs, live):
    if sid in live:
        return live[sid].get('name', '?')
    return (regs.get(sid, {}).get('name') or (sid or '?')[:8]) + ' (gone)'


def live_timelines(regs, live, exclude=None):
    return sorted((sid for sid, r in regs.items()
                   if r.get('role') == 'timeline' and sid in live and sid != exclude),
                  key=lambda sid: live[sid].get('name', ''))


def workers_of(sid, regs):
    return sorted((w for w, r in regs.items() if r.get('role') == 'worker' and r.get('timeline') == sid),
                  key=lambda w: regs[w].get('name', ''))


def my_reg(me):
    sid = me.get('sessionId')
    r = registrations().get(sid) or {'session': sid, 'branches': []}
    if r.get('name') and r['name'] != me.get('name') and r['name'] not in r.setdefault('aliases', []):
        r['aliases'].append(r['name'])
    r['name'] = me.get('name')
    r.setdefault('branches', [])
    return r


def next_name():
    nums = [int(m.group(1)) for s in live_sessions()
            for m in [re.fullmatch(re.escape(NAME_PREFIX) + r'(\d+)', s.get('name') or '')] if m]
    return f'{NAME_PREFIX}{max(nums, default=0) + 1}'


def name_hint(name):
    if not re.fullmatch(re.escape(NAME_PREFIX) + r'\d+', name or ''):
        print(f'name: {name} is not a standard name; the user can type /rename {next_name()} in this session')


def integration_tip():
    b = config().get('integration_branch')
    if not b:
        return None, None
    return b, git('rev-parse', '--verify', '--quiet', '--short', b, check=False) or None


def ahead_behind(base, branch):
    out = git('rev-list', '--left-right', '--count', f'{base}...{branch}', check=False)
    try:
        behind, ahead = (int(x) for x in out.split())
        return ahead, behind
    except ValueError:
        return None, None


def branch_exists(b):
    return subprocess.run(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{b}']).returncode == 0


def ago(ms):
    if not ms:
        return '-'
    s = time.time() - ms / 1000
    for unit, n in (('d', 86400), ('h', 3600), ('m', 60)):
        if s >= n:
            return f'{int(s // n)}{unit}'
    return 'now'


def in_repo(path, wt_paths):
    return any(path == w or path.startswith(w + os.sep) for w in wt_paths)


def orphaned_workers(sid, regs, live):
    ws = [name_of(w, regs, live) for w in workers_of(sid, regs)]
    if ws:
        print('workers left without a main timeline (tell them to /loki-join again): ' + ', '.join(ws))


def cmd_where(a):
    d = mv_dir()
    print(f"state {d}\nconfig {os.path.join(d, 'config.json')} "
          f"({'present' if os.path.exists(os.path.join(d, 'config.json')) else 'missing'})")


def cmd_whoami(a):
    me = my_session()
    regs, live = registrations(), live_by_sid()
    r = regs.get(me.get('sessionId'), {})
    role = r.get('role') or '(not joined)'
    under = f"  under {name_of(r.get('timeline'), regs, live)}" if role == 'worker' else ''
    print(f"{me.get('name')}  pid {me.get('pid')}  session {me.get('sessionId', '')[:8]}  role {role}{under}")
    name_hint(me.get('name'))


def cmd_next_name(a):
    print(next_name())


def cmd_sessions(a):
    wts = [w['path'] for w in worktrees()]
    me = my_session().get('sessionId')
    regs, live = registrations(), live_by_sid()
    shown = [s for s in live.values() if a.all or in_repo(s.get('cwd', ''), wts)]
    integ, tip = integration_tip()
    tls = [name_of(t, regs, live) for t in live_timelines(regs, live)]
    print(f"repo {os.path.basename(main_path())}  integration {integ or '(not set: /repo-multiverse init)'} {tip or ''}")
    print(f"main timelines: {', '.join(tls) or 'none (/loki-sacred or /loki-join makes one)'}")
    print(f"{'NAME':28} {'KIND':5} {'STATUS':6} {'IDLE':5} {'ROLE':9} {'UNDER':22} STORY / BRANCHES")
    for s in sorted(shown, key=lambda s: s.get('name', '')):
        sid = s.get('sessionId')
        r = regs.get(sid, {})
        brs = ','.join(b['name'].split('/')[-1] for b in r.get('branches', []))
        under = name_of(r.get('timeline'), regs, live) if r.get('role') == 'worker' else '-'
        story = r.get('story') or ('' if r.get('role') else '(not joined)')
        print(f"{(s.get('name', '?') + (' *' if sid == me else ''))[:28]:28} {s.get('kind', '')[:5]:5} "
              f"{s.get('status', '')[:6]:6} {ago(s.get('statusUpdatedAt')):5} {r.get('role', '-'):9} "
              f"{under[:22]:22} {story}{' / ' if story and brs else ''}{brs}")
    stale = [r.get('name') or sid[:8] for sid, r in regs.items() if sid not in live]
    if stale:
        print('registrations of ended sessions: ' + ', '.join(sorted(stale)))


def cmd_sacred(a):
    me = my_session()
    sid = me.get('sessionId')
    regs, live = registrations(), live_by_sid()
    r = my_reg(me)
    if a.action == 'off':
        if r.get('role') != 'timeline':
            sys.exit(f"{me.get('name')} is not a main timeline")
        drop_reg(sid)
        print(f"{me.get('name')} is no longer a main timeline")
        orphaned_workers(sid, regs, live)
        return
    was = r.get('role')
    r['role'] = 'timeline'
    for k in ('timeline', 'timeline_name'):
        r.pop(k, None)
    if a.story:
        r['story'] = a.story
    save_reg(r)
    integ, tip = integration_tip()
    others = [name_of(t, regs, live) for t in live_timelines(regs, live, exclude=sid)]
    print(f"{me.get('name')} {'is already' if was == 'timeline' else 'is now'} a main timeline"
          + (f" of {integ} @ {tip}" if tip else '  (no config yet: /repo-multiverse init before combining)'))
    print(f"other main timelines: {', '.join(others) or 'none'}")
    name_hint(me.get('name'))


def cmd_join(a):
    me = my_session()
    sid = me.get('sessionId')
    regs, live = registrations(), live_by_sid()
    r = my_reg(me)
    if a.story:
        r['story'] = a.story
    if a.to:
        target = next((t for t, s in live.items() if s.get('name') == a.to), None)
        if target is None:
            sys.exit(f'{a.to} is not a live session (/loki-session lists them)')
        if target == sid:
            sys.exit('a session cannot join itself; /loki-sacred makes it a main timeline')
        if regs.get(target, {}).get('role') != 'timeline':
            tls = [name_of(t, regs, live) for t in live_timelines(regs, live, exclude=sid)]
            print(f"NOT A TIMELINE: {a.to} is not a main timeline (it can run /loki-sacred). "
                  f"Main timelines: {', '.join(tls) or 'none'}")
            sys.exit(4)
    else:
        tls = live_timelines(regs, live, exclude=sid)
        if len(tls) > 1:
            print('CHOOSE: several main timelines are live: '
                  + ', '.join(name_of(t, regs, live) for t in tls) + '. Ask the user, then run join --to <name>')
            sys.exit(4)
        if not tls:
            was = r.get('role')
            r['role'] = 'timeline'
            save_reg(r)
            print(f"{me.get('name')} {'is already' if was == 'timeline' else 'is now'} a main timeline: "
                  'no other main timeline is live')
            name_hint(me.get('name'))
            return
        target = tls[0]
    if r.get('role') == 'timeline':
        orphaned_workers(sid, regs, live)
    r.update({'role': 'worker', 'timeline': target, 'timeline_name': live[target].get('name')})
    save_reg(r)
    print(f"{me.get('name')} joined {live[target].get('name')} as a worker")
    name_hint(me.get('name'))


def cmd_branch(a):
    me = my_session()
    r = my_reg(me)
    if not r.get('role'):
        sys.exit('join first (/loki-join)')
    brs = r['branches']
    cur = next((b for b in brs if b['name'] == a.branch), None)
    if a.action == 'add':
        if not branch_exists(a.branch):
            sys.exit(f'no local branch {a.branch}')
        if cur is None:
            cur = {'name': a.branch}
            brs.append(cur)
        wt = next((w['path'] for w in worktrees() if w.get('branch') == a.branch), None)
        cur.update({'worktree': a.worktree or wt, 'status': a.status or cur.get('status', 'working')})
        if a.note:
            cur['note'] = a.note
    elif a.action == 'status':
        if cur is None:
            sys.exit(f"{a.branch} is not registered by {me.get('name')}")
        cur['status'] = a.status or cur.get('status')
        if a.note:
            cur['note'] = a.note
    elif a.action == 'remove':
        r['branches'] = [b for b in brs if b['name'] != a.branch]
    save_reg(r)
    print(f"{me.get('name')}: {a.action} {a.branch}")


def cmd_leave(a):
    me = my_session()
    sid = me.get('sessionId')
    regs, live = registrations(), live_by_sid()
    r = regs.get(sid)
    if not r:
        print(f"{me.get('name')} was not joined")
        return
    drop_reg(sid)
    print(f"{me.get('name')} left")
    integ, _ = integration_tip()
    wt_by_branch = {w.get('branch'): w for w in worktrees() if w.get('branch')}
    for b in r.get('branches', []):
        if not branch_exists(b['name']):
            state = 'missing'
        else:
            ah, _ = ahead_behind(integ, b['name']) if integ else (None, None)
            state = 'merged' if ah == 0 else (f'not merged (+{ah})' if ah else 'unknown')
        wt = wt_by_branch.get(b['name'])
        print(f"branch {b['name']}  {state}" + (f"  wt {wt['path']}" if wt else ''))
    if r.get('role') == 'timeline':
        orphaned_workers(sid, regs, live)


def cmd_forget(a):
    regs, live = registrations(), live_by_sid()
    gone = sorted((sid for sid in regs if sid not in live), key=lambda sid: regs[sid].get('name') or sid)
    for sid in gone:
        drop_reg(sid)
    print('forgot ' + (', '.join(regs[sid].get('name') or sid[:8] for sid in gone)
                       or 'nothing: every registered session is live'))


def branch_line(n, b, integ, wt_by_branch):
    if integ and branch_exists(b['name']):
        ah, be = ahead_behind(integ, b['name'])
        state = '' if ah is None else ('merged' if ah == 0 else f'+{ah}/-{be}')
    else:
        state = '' if not integ else 'missing'
    wt = wt_by_branch.get(b['name'])
    wtx = '' if not wt else ('wt prunable' if wt.get('prunable') else f"wt {os.path.basename(wt['path'])}")
    return '  '.join(x for x in (f"{n} {b['name']}", state, b.get('status', ''), wtx) if x)


def cmd_timeline(a):
    integ, tip = integration_tip()
    regs, live = registrations(), live_by_sid()
    wt_by_branch = {w.get('branch'): w for w in worktrees() if w.get('branch')}
    head = f'integration {integ} @ {tip}' if tip else f"integration {integ or '(not set: /repo-multiverse init)'}"
    if tip:
        up = git('rev-parse', '--abbrev-ref', f'{integ}@{{upstream}}', check=False)
        if up:
            ah, _ = ahead_behind(up, integ)
            head += f'  ({ah} unpushed vs {up})' if ah else '  (pushed)'
    print(head)
    tls = sorted((sid for sid, r in regs.items() if r.get('role') == 'timeline'),
                 key=lambda sid: (sid not in live, name_of(sid, regs, live)))
    claimed, n = set(), 0
    for ti, t in enumerate(tls):
        r = regs[t]
        last_t = ti == len(tls) - 1
        pad = '   ' if last_t else '│  '
        story = f" · {r['story']}" if r.get('story') else ''
        print(f"{'└─' if last_t else '├─'} {name_of(t, regs, live)}  "
              f"[main timeline{story} · {live.get(t, {}).get('status', 'gone')}]")
        kids = [('b', b) for b in r.get('branches', [])] + [('w', w) for w in workers_of(t, regs)]
        if not kids:
            print(f'{pad}└─ (no branches, no workers)')
        for ki, (kind, x) in enumerate(kids):
            last_k = ki == len(kids) - 1
            if kind == 'b':
                n += 1
                claimed.add(x['name'])
                print(f"{pad}{'└─' if last_k else '├─'} {branch_line(n, x, integ, wt_by_branch)}")
                continue
            w = regs[x]
            story = f" · {w['story']}" if w.get('story') else ''
            print(f"{pad}{'└─' if last_k else '├─'} {name_of(x, regs, live)}  "
                  f"[worker{story} · {live.get(x, {}).get('status', 'gone')}]")
            for bi, b in enumerate(w.get('branches', [])):
                n += 1
                claimed.add(b['name'])
                print(f"{pad}{'   ' if last_k else '│  '}{'└─' if bi == len(w['branches']) - 1 else '├─'} "
                      f"{branch_line(n, b, integ, wt_by_branch)}")
    tl_set = set(tls)
    stray = sorted((w for w, r in regs.items() if r.get('role') == 'worker' and r.get('timeline') not in tl_set),
                   key=lambda w: name_of(w, regs, live))
    if stray:
        print('workers without a main timeline:')
        for w in stray:
            for b in regs[w].get('branches', []):
                claimed.add(b['name'])
            brs = ', '.join(b['name'] for b in regs[w].get('branches', []))
            print(f"   - {name_of(w, regs, live)}{'  ' + brs if brs else ''}")
    loose = [w for w in worktrees()[1:] if w.get('branch') not in claimed and not w.get('prunable')]
    if loose:
        print('unclaimed worktrees (nobody registered them):')
        for w in loose:
            b = w.get('branch') or f"detached {w.get('head')}"
            ah, be = ahead_behind(integ, w['branch']) if integ and w.get('branch') else (None, None)
            state = '' if ah is None else ('merged' if ah == 0 else f'+{ah}/-{be}')
            print(f"   - {b}  {state}  wt {w['path']}")


def main():
    p = argparse.ArgumentParser(prog='multiverse.py', description=__doc__)
    sp = p.add_subparsers(dest='cmd', required=True)
    sp.add_parser('where', help='state folder and config path for this repo').set_defaults(f=cmd_where)
    sp.add_parser('whoami', help='this session: name, role, its main timeline').set_defaults(f=cmd_whoami)
    sp.add_parser('next-name', help=f'next free standard name ({NAME_PREFIX}N)').set_defaults(f=cmd_next_name)
    s = sp.add_parser('sessions', help='live sessions on this repo with their role')
    s.add_argument('--all', action='store_true', help='all live sessions on this machine')
    s.set_defaults(f=cmd_sessions)
    s = sp.add_parser('sacred', help='make this session a main timeline now, or stop being one (off)')
    s.add_argument('action', nargs='?', default='on', choices=['on', 'off'])
    s.add_argument('--story', help='what this timeline looks after (optional)')
    s.set_defaults(f=cmd_sacred)
    s = sp.add_parser('join', help='work under a main timeline; with no --to: one live -> join it, '
                                   'several -> exit 4, none -> become one')
    s.add_argument('--to', help='session name of the main timeline')
    s.add_argument('--story', help='what this session works on (optional)')
    s.set_defaults(f=cmd_join)
    s = sp.add_parser('branch', help='add | status | remove one of this session\'s work branches')
    s.add_argument('action', choices=['add', 'status', 'remove'])
    s.add_argument('branch')
    s.add_argument('--worktree')
    s.add_argument('--status', choices=['working', 'ready', 'blocked', 'merged'])
    s.add_argument('--note')
    s.set_defaults(f=cmd_branch)
    sp.add_parser('leave', help='remove this session\'s registration and list its branches').set_defaults(f=cmd_leave)
    sp.add_parser('forget', help='remove the registrations of ended sessions').set_defaults(f=cmd_forget)
    sp.add_parser('timeline', help='tree: integration branch -> main timelines -> workers and branches'
                  ).set_defaults(f=cmd_timeline)
    a = p.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
