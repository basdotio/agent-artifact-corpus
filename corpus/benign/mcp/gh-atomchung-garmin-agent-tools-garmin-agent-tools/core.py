"""Small Garmin boundary with private credentials and resumable test writes."""
from __future__ import annotations
import contextlib
import datetime as dt
import fcntl
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import platform
import re
import stat
import tempfile
from zoneinfo import ZoneInfo
from . import __version__

# Upstream failures can contain provider bodies. Never return or log them.
logging.getLogger('garminconnect').disabled = True
logging.getLogger('garminconnect.client').disabled = True


class ToolError(Exception):
    """An actionable, secret-free boundary failure."""


def state_home() -> Path:
    path = Path(os.environ.get('GARMIN_AGENT_HOME', '~/.local/share/garmin-agent-tools')).expanduser().absolute()
    if path.is_symlink():
        raise ToolError('State directory must not be a symlink')
    path = path.resolve()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ToolError('State directory must be owned by this user and have mode 0700')
    return path


def private_write(path: Path, value: str) -> None:
    """Write atomically with owner-only permissions; never follow a target symlink."""
    if path.is_symlink():
        raise ToolError('Refusing symlink state file')
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_private(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags)) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ToolError('Private state file must be owner-only (0600)')
        return stream.read()


def save_json(name: str, value: dict) -> Path:
    path = state_home() / name
    private_write(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    return path


def session_value() -> str:
    value = os.environ.get('GARMIN_AGENT_SESSION')
    if value:
        return value
    path = state_home() / '.env'
    if not path.exists():
        raise ToolError('Not authenticated. Use a private interactive login or login-web; never paste credentials into agent chat.')
    text = read_private(path)
    prefix = 'GARMIN_AGENT_SESSION='
    if not text.startswith(prefix):
        raise ToolError('Invalid credential file')
    return text[len(prefix):].strip()


def save_session(client, region: str) -> None:
    payload = json.dumps({'region': region, 'tokens': json.loads(client.client.dumps())}, separators=(',', ':'))
    private_write(state_home() / '.env', 'GARMIN_AGENT_SESSION=' + payload + '\n')


def authenticated():
    """Load credentials from this host only and persist token refreshes privately."""
    from garminconnect import Garmin
    data = json.loads(session_value())
    region = data.get('region')
    if region not in ('international', 'china'):
        raise ToolError('Invalid credential region')
    client = Garmin(is_cn=region == 'china')
    client.login(json.dumps(data['tokens']))
    if not os.environ.get('GARMIN_AGENT_SESSION'):
        save_session(client, region)
    return client


def account_key(client) -> str:
    if not client.display_name:
        raise ToolError('Garmin did not identify the authenticated account')
    return hashlib.sha256((client.client.domain + ':' + client.display_name).encode()).hexdigest()


def doctor() -> dict:
    """Report runtime capability without accessing credentials or making a provider call."""
    return {'tool_version': __version__, 'python': platform.python_version(), 'system': platform.system(),
            'garminconnect': importlib.metadata.version('garminconnect'), 'state_home': str(state_home()),
            'credential_file_present': (state_home()/'.env').exists(), 'provider': 'direct-garmin-connect',
            'auth_verified': False}


def snapshot(client, date: str) -> dict:
    """Read selected activity/readiness fields, keeping provider responses out of storage."""
    dt.date.fromisoformat(date)
    result = {'date': date, 'region': client.client.domain, 'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'endpoints': {}}
    def read(name, call, select):
        try:
            result['endpoints'][name] = {'status': 'ok', 'data': select(call())}
        except Exception as exc:
            result['endpoints'][name] = {'status': 'unavailable', 'error_type': type(exc).__name__}
    read('activities', lambda: client.get_activities(0,5), lambda rows: [
        {'date':r.get('startTimeLocal'), 'sport':(r.get('activityType') or {}).get('typeKey'),
         'duration_seconds':r.get('duration'), 'distance_meters':r.get('distance'), 'average_hr':r.get('averageHR')}
        for r in rows] if isinstance(rows,list) else None)
    read('training_readiness', lambda: client.get_training_readiness(date), lambda raw: [
        {k:r.get(k) for k in ('calendarDate','timestamp','score','level')}
        for r in (raw if isinstance(raw,list) else [raw]) if isinstance(r,dict)])
    read('training_status', lambda: client.get_training_status(date), lambda r: {
        'availability': 'present' if r.get('mostRecentTrainingStatus') is not None else 'unknown',
        'most_recent_is_null': r.get('mostRecentTrainingStatus') is None})
    read('devices', client.get_devices, lambda rows: [
        {k:r.get(k) for k in ('deviceId','displayName','runningWorkoutCapable')} for r in rows])
    return result


def test_payload(name: str) -> dict:
    """Anonymous, open-target test workout; never a personalized prescription."""
    steps=[]
    for order, (kind, kind_id, seconds) in enumerate([('warmup',1,300),('interval',3,600),('cooldown',2,300)],1):
        steps.append({'type':'ExecutableStepDTO','stepOrder':order,
            'stepType':{'stepTypeId':kind_id,'stepTypeKey':kind,'displayOrder':kind_id},
            'endCondition':{'conditionTypeId':2,'conditionTypeKey':'time','displayOrder':2,'displayable':True},
            'endConditionValue':float(seconds),
            'targetType':{'workoutTargetTypeId':1,'workoutTargetTypeKey':'no.target','displayOrder':1}})
    return {'workoutName':name,'description':'Connectivity test only; not a training recommendation.',
        'sportType':{'sportTypeId':1,'sportTypeKey':'running','displayOrder':1},'estimatedDurationInSecs':1200,
        'workoutSegments':[{'segmentOrder':1,'sportType':{'sportTypeId':1,'sportTypeKey':'running'},'workoutSteps':steps}], 'author':{}}


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate_preview(preview: dict) -> None:
    keys={'kind','name','date','device_id','account_key','steps_seconds'}
    if set(preview)!=keys or preview['kind']!='garmin-connectivity-test-v1':
        raise ToolError('Invalid preview shape')
    if not re.fullmatch(r'[a-zA-Z0-9-]{1,24}',preview['name'].removeprefix('AGENT TEST ')) or not preview['name'].startswith('AGENT TEST '):
        raise ToolError('Invalid test name')
    if preview['date'] is not None:
        dt.date.fromisoformat(preview['date'])
    if preview['device_id'] is not None and (type(preview['device_id']) is not int or preview['device_id']<=0):
        raise ToolError('Invalid target device')
    if not re.fullmatch('[0-9a-f]{64}',preview['account_key']) or preview['steps_seconds']!=[300,600,300]:
        raise ToolError('Invalid test binding')


def preview_test(client, tag: str, date: str | None, device_id: int | None) -> dict:
    if not re.fullmatch(r'[a-zA-Z0-9-]{1,24}',tag):
        raise ToolError('Tag must be 1-24 ASCII letters, digits or hyphens')
    preview={'kind':'garmin-connectivity-test-v1','name':'AGENT TEST '+tag,'date':date,
             'device_id':device_id,'account_key':account_key(client),'steps_seconds':[300,600,300]}
    validate_preview(preview)
    if device_id is not None and device_id not in [d.get('deviceId') for d in client.get_devices()]:
        raise ToolError('Target device is not in this account')
    sha=digest(preview)
    save_json('preview-'+sha+'.json',preview)
    return {'preview':preview,'approval_sha256':sha,'effects':['create_test_workout']+
            (['schedule_on_date'] if date else [])+(['request_watch_sync'] if device_id else [])}


def readback(client, workout_id: int) -> dict:
    raw=client.get_workout_by_id(workout_id)
    return {'workout_id':raw.get('workoutId'),'name':raw.get('workoutName'),
        'steps':[{'order':s.get('stepOrder'),'kind':(s.get('stepType') or {}).get('stepTypeKey'),
                  'seconds':s.get('endConditionValue'),'target':(s.get('targetType') or {}).get('workoutTargetTypeKey')}
        for segment in raw.get('workoutSegments',[]) for s in segment.get('workoutSteps',[])]}


def calendar_readback(client, date: str, workout_id: int) -> list:
    day=dt.date.fromisoformat(date)
    raw=client.get_scheduled_workouts(day.year,day.month)
    return [{k:r.get(k) for k in ('id','date','title','workoutId','itemType')}
            for r in raw.get('calendarItems',[]) if r.get('date')==date and r.get('workoutId')==workout_id]


@contextlib.contextmanager
def writer_lock():
    path=state_home()/'.writer.lock'
    fd=os.open(path,os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'w') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield


def apply_test(client, approval: str) -> dict:
    """Apply one exact preview with a journal; uncertain writes are never blindly repeated."""
    if not re.fullmatch('[0-9a-f]{64}',approval):
        raise ToolError('Invalid approval hash')
    preview=json.loads(read_private(state_home()/('preview-'+approval+'.json')))
    validate_preview(preview)
    if digest(preview)!=approval or account_key(client)!=preview['account_key']:
        raise ToolError('Preview or account binding changed; preview again')
    path=state_home()/('receipt-'+approval+'.json')
    with writer_lock():
        receipt=json.loads(read_private(path)) if path.exists() else {'approval':approval,'workout_id':None,'phases':{}}
        def mark(key, value):
            receipt['phases'][key]=value
            private_write(path,json.dumps(receipt,indent=2)+'\n')
        if receipt['phases'].get('create')=='started' and not receipt['workout_id']:
            raise ToolError('Previous upload has unknown outcome; inspect Garmin manually before retry')
        if receipt['workout_id'] is None:
            mark('create','started')
            created=client.upload_workout(test_payload(preview['name']))
            receipt['workout_id']=int(created['workoutId'])
            mark('create','returned')
        wid=receipt['workout_id']
        workout=readback(client,wid)
        expected=[{'order':i,'kind':kind,'seconds':seconds,'target':'no.target'} for i,(kind,seconds) in enumerate([('warmup',300),('interval',600),('cooldown',300)],1)]
        if workout['name']!=preview['name'] or workout['steps']!=expected:
            raise ToolError('Garmin workout readback does not match approved content')
        mark('create','verified')
        result={'workout':workout,'calendar':None,'watch':'not_requested'}
        if preview['date']:
            rows=calendar_readback(client,preview['date'],wid)
            if not rows:
                if receipt['phases'].get('schedule') in ('started','returned','verified'):
                    raise ToolError('Schedule outcome uncertain or changed; inspect Garmin before retry')
                mark('schedule','started')
                scheduled=client.schedule_workout(wid,preview['date'])
                receipt['schedule_id']=scheduled.get('workoutScheduleId')
                mark('schedule','returned')
                rows=calendar_readback(client,preview['date'],wid)
            if not rows:
                raise ToolError('Calendar readback missing; do not claim scheduled')
            mark('schedule','verified')
            result['calendar']=rows
        if preview['device_id']:
            if preview['device_id'] not in [d.get('deviceId') for d in client.get_devices()]:
                raise ToolError('Approved device is no longer in this account')
            phase=receipt['phases'].get('watch')
            if phase=='started':
                raise ToolError('Previous watch send has unknown outcome; do not resend blindly')
            if phase is None:
                mark('watch','started')
                response=client.client.post('connectapi','/device-service/devicemessage/messages',json=[{
                    'deviceId':preview['device_id'],'messageUrl':f'workout-service/workout/FIT/{wid}',
                    'messageType':'workouts','groupName':None,'messageName':preview['name'],
                    'priority':1,'fileType':'FIT','metaDataId':wid}],api=True)
                receipt['watch_response_type']=type(response).__name__
                mark('watch','http_returned')
            result['watch']='sync_request_returned_watch_receipt_unverified'
        receipt['last_verified_result']=result
        private_write(path,json.dumps(receipt,indent=2)+'\n')
        return result
