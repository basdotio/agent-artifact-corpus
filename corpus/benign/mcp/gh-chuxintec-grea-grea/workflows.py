"""Unity-specific routing; a plan does not stand in for execution evidence."""
from .common import package_root

WORKFLOWS = {
 'recover': {'title':'完整恢复/首次重建','baseline':'同版本、同状态的原版资源与实际运行','dimensions':['rules','runtime','visual'], 'steps':[('03-恢复-原版运行与内容取证.md',['unpack_xapk','video_manifest','video_sheet']),('04-资源-提取与引用恢复.md',['assetripper','unity_dependency_audit']),('05-Unity-工程重建与恢复.md',['ilspy','cpp2il','il2cppdumper','ghidra']),('01-流程-游戏恢复开发.md',['unity_asset_ledger']),('08-验收-测试与结果交付.md',[])], 'boundary':'静态提取可以独立继续；缺原生运行证据时不关闭动态一致性。'},
 'fix': {'title':'局部一致性修复','baseline':'相关原版依据与受影响入口','dimensions':['rules','runtime'], 'steps':[('01-流程-开发前检查与迭代.md',[]),('05-Unity-界面还原与输入交互.md',[]),('06-玩法-规则与随机一致性.md',['compare_traces']),('05-Unity-动画特效与事件时序.md',['compare_events']),('08-验收-测试与结果交付.md',[])], 'boundary':'按具体缺口选专题，不重新完整解包或无条件做性能基准。'},
 'port': {'title':'跨引擎转原生 Unity/清理源引擎残留','baseline':'原版规则语义与可观察结果；原生可维护门','dimensions':['rules','runtime','visual','native'], 'steps':[('05-Unity-原生转换规范.md',[]),('05-Unity-跨引擎移植与行为一致性.md',['compare_events']),('05-Unity-UI框架迁移.md',[]),('06-玩法-规则与随机一致性.md',['compare_traces']),('08-验收-测试与结果交付.md',[])], 'boundary':'不在 Unity 中复刻源引擎运行时；转换器一次性运行，生产不依赖它；守卫、原版对照与原生可维护三门分别报告。'},
 'reskin': {'title':'授权换皮','baseline':'最新批准设计与已授权玩法/交互不变量','dimensions':['runtime','visual'], 'steps':[('07-美术-游戏换皮与资源制作.md',['image_alpha_audit']),('05-Unity-界面还原与输入交互.md',[]),('05-Unity-动画特效与事件时序.md',[]),('08-验收-测试与结果交付.md',[])], 'boundary':'已批准素材直接复用；指定制作工具依当前会话能力，不自动收费生图或审批。'},
 'refactor': {'title':'结构重构/UI迁移','baseline':'当前工程行为、GUID/fileID、动态加载键','dimensions':['identity','runtime'], 'steps':[('05-Unity-工程结构与开发规范.md',['unity_asset_ledger']),('05-Unity-重构与资源迁移.md',['unity_dependency_audit']),('05-Unity-UI框架迁移.md',[]),('08-验收-测试与结果交付.md',[])], 'boundary':'UI框架迁移仅在本次要求时进行；不凭未引用列表删除资产。'},
 'performance': {'title':'性能优化','baseline':'同设备、场景、输入、随机和负载的前后结果','dimensions':['performance','rules','runtime'], 'steps':[('05-Unity-性能分析与优化验证.md',[]),('08-验收-测试与结果交付.md',[])], 'boundary':'不通过改变随机、限帧或画质制造收益；不冒称已验证目标渠道。'},
 'deliver': {'title':'构建/预览/发布','baseline':'源码/资产/构建ID与目标平台','dimensions':['identity','platform'], 'steps':[('09-交付-游戏构建与版本发布.md',['verify_payload_tree']),('08-验收-测试与结果交付.md',[])], 'boundary':'默认Mac；只进入本次已授权的预览、安装或发布环节。'},
 'maintain': {'title':'工具/技能/复盘维护','baseline':'调用契约、文档、兼容入口与必要测试','dimensions':['identity'], 'steps':[('02-工具-选择与调用.md',['check_grea_skill']),('10-维护-开发复盘与规范更新.md',[])], 'boundary':'不启动无关游戏、收费服务或Git推送。'},
}

SOURCE_MAPPINGS = {'cocos': '05-Unity-源引擎映射-Cocos.md'}
SOURCE_ENGINES = ('unknown', 'unity', 'cocos', 'laya', 'other')
for intent in ('assess', 'evidence'):
    WORKFLOWS[intent] = {
        'title': '只读成本评估' if intent == 'assess' else '来源取证',
        'baseline': '显式来源身份、已观察行为与未知范围',
        'dimensions': ['identity'],
        'steps': [('03-恢复-原版运行与内容取证.md', ['video_manifest', 'video_sheet'])],
        'boundary': '不进入游戏实现；提取不证明服务器或完整玩法。',
    }


def reference(name):
    plugin = package_root() / 'plugin'
    found = sorted(path for path in [plugin / 'shared' / name, *(plugin / 'skills').glob('*/references/' + name)] if path.is_file())
    if len(found) != 1:
        raise KeyError('reference not uniquely resolvable: ' + name)
    return found[0]


def required_dimensions(mode, source_engine='unknown'):
    if source_engine == 'unknown' and mode in ('recover', 'port'):
        return ['identity']
    dimensions = list(WORKFLOWS[mode]['dimensions'])
    if source_engine in ('cocos', 'laya', 'other') and mode in ('recover', 'port', 'fix', 'refactor', 'performance'):
        if 'native' not in dimensions:
            dimensions.append('native')
    return dimensions


def plan(mode, source_engine='unknown', engine_version=None, source_format=None,
         target_platform=None, acceptance_profile='scoped'):
    value = WORKFLOWS[mode]
    source_tools = []
    if source_format in ('apk', 'xapk'):
        source_tools = ['unpack_xapk']
    elif source_format == 'wxapkg':
        source_tools = ['unpack_wxapkg']
    stages = []
    unknown = source_engine == 'unknown' and mode in ('recover', 'port')
    steps = WORKFLOWS['evidence']['steps'] if unknown else value['steps']
    for name, tools in steps:
        tools = list(tools)
        phase = 'verification'
        if name == '03-恢复-原版运行与内容取证.md':
            tools = source_tools + ['video_manifest', 'video_sheet']
            phase = 'source_evidence'
        elif name == '04-资源-提取与引用恢复.md':
            tools = ['assetripper'] if source_engine == 'unity' else (['cocos_assets', 'cocos_modules'] if source_engine == 'cocos' else [])
            phase = 'source_evidence'
        elif name == '05-Unity-工程重建与恢复.md':
            if source_engine != 'unity':
                continue
            if source_format == 'mono':
                tools = ['ilspy']
            elif source_format == 'il2cpp':
                tools = ['cpp2il', 'il2cppdumper', 'ghidra']
            phase = 'implementation'
        elif name in ('01-流程-游戏恢复开发.md', '05-Unity-UI框架迁移.md'):
            phase = 'implementation'
        stages.append(dict(reference=str(reference(name)), tool_ids=tools, phase=phase, executed=False))
    if source_engine in ('cocos', 'laya', 'other') and mode in ('recover', 'fix'):
        extra = [('05-Unity-原生转换规范.md', []), ('05-Unity-跨引擎移植与行为一致性.md', ['laya_contract_audit'] if source_engine == 'laya' else [])]
        stages = [dict(reference=str(reference(name)), tool_ids=tools, phase='implementation', executed=False) for name, tools in extra] + stages
    if source_engine in SOURCE_MAPPINGS and mode in ('recover', 'fix', 'port'):
        stages.insert(1, dict(reference=str(reference(SOURCE_MAPPINGS[source_engine])), tool_ids=[], phase='implementation', executed=False))
    preferred = {'unity_dependency_audit': 'audit_unity_dependencies', 'unity_asset_ledger': 'snapshot_unity_assets', 'compare_traces': 'compare_gameplay_traces', 'audit_numeric_texture': 'inspect_numeric_texture'}
    for step in stages:
        step['grea_operations'] = [preferred[tool] for tool in step['tool_ids'] if tool in preferred]
    return dict(mode=mode, title=value['title'], baseline=value['baseline'],
                required_dimensions=required_dimensions(mode, source_engine), steps=stages,
                boundary=value['boundary'], source_engine=source_engine, executed=False,
                next_decision='identify_source_engine' if unknown else 'select_supported_format_and_scope',
                task=dict(intent=mode, source_engine=source_engine, engine_version=engine_version,
                          source_format=source_format, target_platform=target_platform,
                          acceptance_profile=acceptance_profile),
                limitations=['Source identity is caller-declared; parser support must be checked against its adapter catalog.'])
