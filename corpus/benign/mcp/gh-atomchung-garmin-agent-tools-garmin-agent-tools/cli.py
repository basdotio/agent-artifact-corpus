"""Command line entry. Secrets are accepted only through private user interaction."""
from __future__ import annotations
import argparse
import datetime as dt
import getpass
import json
import sys
from . import core


def main():
    parser=argparse.ArgumentParser(description='Direct Garmin connectivity tools for an agent computer')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor',help='Runtime only; does not authenticate')
    login=sub.add_parser('login',help='Private interactive terminal login; never send credentials in chat')
    login.add_argument('--region',choices=['international','china'],default='international')
    web=sub.add_parser('login-web',help='Private same-computer browser login helper')
    web.add_argument('--region',choices=['international','china'],default='international')
    web.add_argument('--port',type=int,default=8765)
    web.add_argument('--timeout',type=int,default=600)
    read=sub.add_parser('snapshot',help='Live selected fields; does not save health data')
    read.add_argument('--date',required=True,help='Explicit YYYY-MM-DD in the athlete timezone')
    preview=sub.add_parser('test-preview',help='Preview a fixed 5/10/5 minute open-target test')
    preview.add_argument('--tag',required=True)
    preview.add_argument('--date',help='Schedule on this date; omit for template only')
    preview.add_argument('--device-id',type=int)
    apply=sub.add_parser('test-apply',help='Apply one exact approved preview')
    apply.add_argument('--approve',required=True,help='Exact preview SHA-256 after owner confirmation')
    verify=sub.add_parser('workout',help='Read back one provider workout')
    verify.add_argument('workout_id',type=int)
    calendar=sub.add_parser('calendar',help='Read date+workout binding from Garmin')
    calendar.add_argument('--date',required=True)
    calendar.add_argument('--workout-id',required=True,type=int)
    mcp=sub.add_parser('mcp',help='Serve bounded tools over local stdio')
    mcp.add_argument('--backend',choices=['api','browser'],default='api')
    args=parser.parse_args()
    try:
        if args.command=='doctor': result=core.doctor()
        elif args.command=='login-web':
            from .login_web import serve
            if not 1024<=args.port<=65535 or not 30<=args.timeout<=1800:
                raise core.ToolError('Port or timeout out of range')
            serve(args.region,args.port,args.timeout); return
        elif args.command=='login':
            if not sys.stdin.isatty():
                raise core.ToolError('Login requires a private interactive terminal; use login-web for browser takeover')
            from garminconnect import Garmin
            email=input('Garmin email: ').strip()
            password=getpass.getpass('Garmin password: ')
            g=Garmin(email=email,password=password,is_cn=args.region=='china',prompt_mfa=lambda:getpass.getpass('Garmin verification code: '))
            g.login(); core.save_session(g,args.region)
            email=password=None
            result={'authenticated':True,'region':g.client.domain,'workouts_written':False}
        elif args.command=='mcp':
            if args.backend=='browser':
                from .browser.server import run
            else:
                from .mcp_server import run
            run(); return
        else:
            g=core.authenticated()
            if args.command=='snapshot': result=core.snapshot(g,args.date)
            elif args.command=='test-preview': result=core.preview_test(g,args.tag,args.date,args.device_id)
            elif args.command=='test-apply': result=core.apply_test(g,args.approve)
            elif args.command=='workout': result=core.readback(g,args.workout_id)
            elif args.command=='calendar': result={'matches':core.calendar_readback(g,args.date,args.workout_id)}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception as exc:
        message=str(exc) if isinstance(exc,core.ToolError) else 'Operation failed; inspect status without printing provider responses or credentials'
        print(json.dumps({'status':'failed','error_type':type(exc).__name__,'message':message}),file=sys.stderr)
        raise SystemExit(1) from None

if __name__=='__main__': main()
