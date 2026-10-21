"""Only application dispatch: CLI/MCP use the same validation, handlers and outcomes."""
from grea.host.files import temporary_directory
import subprocess,json,tempfile
from grea.host.paths import Path
from jsonschema import Draft202012Validator
from . import __version__
from .contracts import CONTRACTS,ENVELOPE_SCHEMA,catalog
from .common import GreaError,envelope,digest,package_root,implementation_identity
from . import registry,artifacts,cases,workflows,runner,unity_projects,unity_generation

def doctor(tool_ids=None,probe=False,cancel=None):
    entries=[registry.tool(x) for x in tool_ids] if tool_ids else registry.load()
    if probe and not tool_ids:raise GreaError('EXPLICIT_SELECTION_REQUIRED','Version/help probes require explicit tool_ids.',next_action='Select only dependencies relevant to this task.')
    results=[]
    for entry in entries:
        if cancel is not None and cancel.is_set():raise GreaError('CANCELLED','Diagnostic selection cancelled.')
        item={'tool_id':entry['id'],**registry.presence(entry)}
        if entry.get('acquisition'):item['acquisition']=entry['acquisition']
        if probe:
            try:
                with temporary_directory(prefix='grea-doctor-') as temp:
                    receipt,_,failure=runner.execute(entry['id'],[],str(Path(temp)/'probe'),timeout_seconds=20,max_output_bytes=1048576,max_inline_bytes=8192,probe=True,cancel=cancel)
                    item.update(level='probe',exit_code=receipt['exit_code'],state='probe_passed' if receipt['status']=='ok' else 'probe_failed',output=receipt['stdout']+receipt['stderr'],output_truncated=receipt['inline_truncated'],capture_complete=receipt['capture_complete'],reason=receipt['reason'])
            except (GreaError,subprocess.TimeoutExpired,OSError) as e:item.update(state='probe_failed',reason=str(e))
        results.append(item)
    return {'checks':results,'runtime_connection':'not_checked','limitations':['Version/help/presence do not establish provider samples or a live Unity Editor.']}

_OMITTED = object()

def dispatch(operation,arguments=_OMITTED,cancel=None):
    arguments={} if arguments is _OMITTED else arguments
    try:
        if operation not in CONTRACTS:raise GreaError('UNKNOWN_OPERATION','Unknown grea operation.',next_action='Read the generated operation catalog.')
        errors=sorted(Draft202012Validator(CONTRACTS[operation][1]).iter_errors(arguments),key=lambda x:str(list(x.path)))
        if errors:raise GreaError('INVALID_ARGUMENTS',errors[0].message,details={'path':list(errors[0].path)})
        args=dict(arguments)
        for key,schema in CONTRACTS[operation][1]['properties'].items():
            if key not in args and 'default' in schema:args[key]=schema['default']
        # Typed adapters run in an isolated receipt directory. Resolve file inputs
        # against the caller's cwd before handing them to that subprocess.
        typed_paths={
            'audit_unity_dependencies':('assets','output'),
            'snapshot_unity_assets':('assets','output'),
            'compare_gameplay_traces':('before','after'),
            'inspect_numeric_texture':('source','candidate'),
        }
        for key in typed_paths.get(operation,()):
            if key in args:args[key]=str(Path(args[key]).expanduser().absolute())
        typed = None
        if operation=='audit_unity_dependencies':
            argv=['--assets',args['assets'],'--output',args['output']]
            for root in args['roots']:argv+=['--root',root]
            typed=('unity_dependency_audit',argv)
        elif operation=='snapshot_unity_assets':typed=('unity_asset_ledger',['snapshot','--assets',args['assets'],'--output',args['output']])
        elif operation=='compare_gameplay_traces':
            argv=[args['before'],args['after']]
            for field in args['fields']:argv+=['--field',field]
            typed=('compare_traces',argv)
        elif operation=='inspect_numeric_texture':
            argv=[args['source'],'--width',str(args['width']),'--height',str(args['height']),'--channels',str(args['channels']),'--dtype',args['dtype'],'--endian',args['endian']]
            if 'candidate' in args:argv+=['--candidate',args['candidate']]
            typed=('audit_numeric_texture',argv)
        if typed:
            request={k:args[k] for k in ('run_dir','timeout_seconds','max_output_bytes','max_inline_bytes') if k in args}
            request.update(tool_id=typed[0],arguments=typed[1])
            out=dispatch('run_tool',request,cancel);out['operation']=operation
            return out
        evidence=[];limits={};limitations=[];status='ok';error=None
        if operation=='session':
            skill_path=Path(args.get('skill_dir',package_root()/'plugin')).expanduser()
            skill_version=json.loads((skill_path/'version.json').read_text(encoding='utf-8'))
            required=skill_version.get('requiredOperations')
            if (skill_version.get('greaVersion')!=__version__ or not isinstance(required,list)
                    or not all(isinstance(name,str) and name in CONTRACTS for name in required)):
                raise GreaError('SKILL_VERSION_MISMATCH','Skill requires another grea version or unavailable operations.')
            entries=registry.inventory();result={'version':__version__,'implementation':implementation_identity(),'package_root':str(package_root()),'catalog_sha256':digest({'operations':catalog(),'providers':registry.load()}),'operations':[x['name'] for x in catalog()],'providers':[{k:v for k,v in x.items() if k in ('id','category','availability')} for x in entries],'live_unity_connection':'not_checked','skill':{'version':skill_version.get('version'),'greaVersion':skill_version['greaVersion'],'compatibility':'matched','scope':'explicit_install' if 'skill_dir' in args else 'bundled_source'}}
        elif operation=='list_tools':result={'tools':registry.inventory(**args),'catalog_sha256':digest(registry.load())}
        elif operation=='describe_tool':
            entry=registry.tool(**args);result={'tool':entry,'availability':registry.presence(entry)}
        elif operation=='doctor':
            result=doctor(**args,cancel=cancel)
            if any(x['state'] in ('probe_failed','unavailable','unsupported') for x in result['checks']):status='partial'
        elif operation=='inspect_target':
            result=artifacts.inspect_target(**args);limits={k:args[k] for k in ('max_files','max_bytes')};status='partial' if result['coverage']=='partial' else 'ok'
            evidence=[{'kind':'static_inventory','identity':result['target'],'coverage':result['coverage']}]
        elif operation in ('validate_unity_project','plan_unity_project'):
            handler = unity_projects.validate_project if operation=='validate_unity_project' else unity_projects.plan_project
            result = handler(**args, cancel=cancel)
            report = result if operation=='validate_unity_project' else result['report']
            status = 'partial' if report['findings'] else 'ok'
            limitations = report['limitations'] if operation=='plan_unity_project' else []
            limits = {key: args[key] for key in ('max_files','max_bytes')}
        elif operation in ('plan_unity_generation','generate_unity_project','recover_unity_generation'):
            handler = {'plan_unity_generation': unity_generation.plan_generation, 'generate_unity_project': unity_generation.generate_project,
                       'recover_unity_generation': unity_generation.recover_generation}[operation]
            result = handler(**args, cancel=cancel)
            if result.get('seedChanges') or result.get('humanFiles'): status='partial'
        elif operation=='plan_workflow':result=workflows.plan(**args)
        elif operation=='start_case_revision':
            from .case_revisions import start
            result=start(**args)
        elif operation=='run_tool':
            result,evidence,error=runner.execute(**args,cancel=cancel);status=result['status'];limits={k:args[k] for k in ('timeout_seconds','max_output_bytes','max_inline_bytes')}
            limitations=['Same-process-group cleanup does not cover detached provider daemons.','Raw tool success is not original gameplay or Unity acceptance.']
        else:
            handler={'init_case':cases.init_case,'add_evidence':cases.add_evidence,'record_verification':cases.record_verification,'case_status':cases.case_status}[operation]
            result=handler(**args)
            if operation=='case_status' and result['declared_acceptance']!='ready_for_review':status='partial'
        limitations+=result.get('limitations',[])
        out=envelope(operation,result,status=status,evidence=evidence,limitations=limitations,limits=limits,error=error)
    except GreaError as e:out=envelope(operation,status='error',error=e)
    except (OSError,ValueError,KeyError,TypeError) as e:out=envelope(operation,status='error',error=GreaError('INVALID_STATE',str(e),next_action='Inspect the selected files/registry; preserve evidence before repairing.'))
    except Exception as e:out=envelope(operation,status='error',error=GreaError('INTERNAL_ERROR','Unexpected internal failure.',details={'exception_type':type(e).__name__},next_action='Preserve inputs and report the operation/version; do not retry mutations blindly.'))
    Draft202012Validator(ENVELOPE_SCHEMA).validate(out)
    return out
