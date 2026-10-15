"""One provider catalog for legacy dispatch, CLI discovery and MCP discovery."""
import json,os,shutil,subprocess,sys,platform
from pathlib import Path
from .common import GreaError,package_root,digest

def load():
    value=json.loads((package_root()/'registry.json').read_text())
    entries=value['tools'];ids=[x['id'] for x in entries]
    if len(ids)!=len(set(ids)):raise GreaError('INVALID_REGISTRY','Duplicate tool IDs.')
    lock_path=package_root()/'providers.lock.json'
    acquisition={x['tool_id']:x for x in json.loads(lock_path.read_text())['providers']} if lock_path.is_file() else {}
    for entry in entries:
        if entry['id'] in acquisition:entry['acquisition']=acquisition[entry['id']]
    by_id={x['id']:x for x in entries}
    overrides={}
    if os.environ.get('GREA_PROVIDERS'):
        config=json.loads(Path(os.environ['GREA_PROVIDERS']).expanduser().read_text())
        if not isinstance(config,dict) or set(config)!={'schema_version','providers'} or config['schema_version']!=1 or not isinstance(config['providers'],dict):
            raise GreaError('INVALID_PROVIDER_CONFIG','Expected schema_version=1 and a providers object.')
        overrides=config['providers']
        for key,override in overrides.items():
            if key not in by_id or by_id[key].get('alias_of'):raise GreaError('INVALID_PROVIDER_CONFIG','Override a known canonical provider ID.',details={'tool_id':key})
            if not isinstance(override,dict) or set(override)-{'command','probe','systems','architectures'} or not override.get('systems'):
                raise GreaError('INVALID_PROVIDER_CONFIG','Overrides require systems and explicit command/probe arrays.')
            for field in ('command','probe','systems','architectures'):
                if field in override and (not isinstance(override[field],list) or not override[field] or not all(isinstance(x,str) and x for x in override[field])):
                    raise GreaError('INVALID_PROVIDER_CONFIG','Override arrays must contain nonempty strings.')
            if not any(k in override for k in ('command','probe')):raise GreaError('INVALID_PROVIDER_CONFIG','Override must specify command or probe.')
    def resolve(key,seen=()):
        if key in seen or key not in by_id:raise GreaError('INVALID_REGISTRY','Missing or cyclic alias.',details={'tool_id':key})
        entry=dict(by_id[key])
        if entry.get('alias_of'):
            canonical=resolve(entry['alias_of'],(*seen,key))
            for field in ('execution','probe','files','required_files','host_support','configuration_source','system_binary'):entry[field]=canonical.get(field)
            entry['canonical_id']=canonical.get('canonical_id',canonical['id'])
        if key in overrides:
            override=overrides[key]
            # A native replacement must not inherit the old host's probe.
            entry['execution']=dict(entry.get('execution') or {},command=override['command']) if 'command' in override else None
            entry['probe']=override.get('probe')
            entry['files']=[]
            entry['required_files']=[]
            entry['host_support']={'systems':override['systems'],'architectures':override.get('architectures',[]),'verification':'explicit local configuration; runtime not checked'}
            entry['system_binary']=None
            entry['configuration_source']=str(Path(os.environ['GREA_PROVIDERS']).expanduser().resolve())
        return entry
    return [resolve(key) for key in sorted(by_id)]

def check_host(entry):
    support=entry.get('host_support',{})
    if support.get('systems') and platform.system() not in support['systems']:
        raise GreaError('UNSUPPORTED_HOST','Registered adapter is not configured for this host.',details={'tool_id':entry['id'],'host':platform.system(),'support':support},next_action='Read docs/工具集成与平台支持.md; configure the same provider explicitly for this host.')
    if support.get('architectures') and platform.machine().lower() not in support['architectures']:
        raise GreaError('UNSUPPORTED_ARCH','Bundled adapter does not match this CPU.',details={'tool_id':entry['id'],'architecture':platform.machine()},next_action='Install a matching native build and configure its canonical provider ID.')

def expand(value):return value.replace('{grea}',str(package_root())).replace('{tools}',str(package_root())).replace('{home}',str(Path.home())).replace('{python}',sys.executable)

def tool(tool_id):
    for entry in load():
        if entry['id']==tool_id:return entry
    raise GreaError('UNKNOWN_TOOL','No such tool ID.',details={'tool_id':tool_id},next_action='Use list_tools or describe_tool; do not guess aliases.')

def command(entry,probe=False):
    check_host(entry)
    missing=[expand(p) for p in entry.get('required_files',[]) or [] if not Path(expand(p)).is_file()]
    if missing:raise GreaError('PROVIDER_UNAVAILABLE','Optional provider files are not installed.',details={'tool_id':entry['id'],'missing':missing},next_action='Read THIRD_PARTY.md and configure a licensed local provider; public source does not bundle dependencies.')
    raw=entry.get('probe') if probe else (entry.get('execution') or {}).get('command')
    if not raw:raise GreaError('UNSUPPORTED_OPERATION','This entry is inventory-only or has no generic CLI adapter.',details={'tool_id':entry['id']},next_action='Read its usage and use the documented Editor/provider interface.')
    argv=[expand(x) for x in raw]
    if argv[0]=='python3':argv[0]=sys.executable
    found=shutil.which(argv[0])
    if not found:raise GreaError('PROVIDER_UNAVAILABLE','Registered executable is unavailable.',details={'tool_id':entry['id'],'executable':argv[0]},next_action='Restore the registered dependency; do not silently substitute a provider.')
    argv[0]=found
    return argv

def presence(entry):
    try:
        argv=command(entry,probe=not bool(entry.get('execution')))
        if entry.get('system_binary'):
            directory=os.environ.get('GREA_SYSTEM_BIN')
            brew=shutil.which('brew') if directory is None else None
            if directory is None and brew and Path(brew).parent.name=='bin':directory=str(Path(brew).parent)
            if directory is None:return {'state':'manual','level':'presence','runtime':'not_checked','reason':'Set GREA_SYSTEM_BIN to check the wrapper target without executing Homebrew.'}
            target=Path(directory)/entry['system_binary']
            available=target.is_file() and os.access(target,os.X_OK)
            return {'state':'detected' if available else 'unavailable','level':'presence','runtime':'not_checked','executable':str(target),'wrapper':argv[0]}
        # Interpreter availability alone does not establish that its script/dll exists.
        missing=[x for x in argv[1:] if Path(x).is_absolute() and x.endswith(('.py','.dll','.mjs','.js')) and not Path(x).is_file()]
        if missing:return {'state':'unavailable','level':'presence','missing':missing,'runtime':'not_checked'}
        return {'state':'detected','level':'presence','executable':argv[0],'runtime':'not_checked'}
    except GreaError as e:
        if e.code in ('UNSUPPORTED_HOST','UNSUPPORTED_ARCH'):return {'state':'unsupported','level':'host','runtime':'not_checked','reason':e.code}
        if e.code=='PROVIDER_UNAVAILABLE' and e.details.get('missing'):return {'state':'unavailable','level':'presence','runtime':'not_checked','missing':e.details['missing'],'reason':e.code}
        paths=[Path(expand(p)) for p in entry.get('files',[]) or []]
        if paths:return {'state':'detected' if all(p.exists() for p in paths) else 'unavailable','level':'presence','runtime':'not_checked','paths':[str(p) for p in paths]}
        return {'state':'unavailable' if e.code=='PROVIDER_UNAVAILABLE' else 'manual','level':'presence','runtime':'not_checked','reason':e.code}

def inventory(category=None):
    return [dict(x,availability=presence(x)) for x in load() if category is None or x.get('category')==category]

def legacy_command(tool_id):return command(tool(tool_id))
