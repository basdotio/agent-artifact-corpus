#!/usr/bin/env python3
"""Read-only local links, reachability, Skill frontmatter and recovery CLI contract checks for the grea plugin or a single Skill. No tool execution."""

import argparse
import ast
import json
import re
import sys
import unicodedata
from grea.host.paths import Path
from urllib.parse import unquote


SKILL_REL = Path('.agents/skills/game-build')
PLUGIN_REL = Path('plugin')
ROUTER = Path('skills/grea/SKILL.md')


def without_fences(text):
    return re.sub(r'^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$', '', text,
                  flags=re.MULTILINE | re.DOTALL)


def heading_ids(text):
    counts, result = {}, set()
    for line in without_fences(text).splitlines():
        match = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if not match:
            continue
        value = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', match[1]).lower()
        value = ''.join(c for c in value if c in '-_' or c.isspace()
                        or unicodedata.category(c)[0] in 'LN')
        value = value.replace(' ', '-')
        count = counts.get(value, 0)
        counts[value] = count + 1
        result.add(value if not count else f'{value}-{count}')
    return result


def within(path, root):
    return path == root or root in path.parents


def tool_root_for(workspace):
    for candidate in (workspace, workspace / 'grea'):
        if (candidate / 'registry.json').is_file() and (candidate / PLUGIN_REL / ROUTER).is_file():
            return candidate
    return workspace / 'tools'


def dispatcher_contract(workspace):
    """Inspect literal tables without importing or executing the dispatcher."""
    tool_root = tool_root_for(workspace)
    if (tool_root / PLUGIN_REL / ROUTER).is_file():
        entries = json.loads((tool_root / 'registry.json').read_text(encoding='utf-8'))['tools']
        result = {}
        for entry in entries:
            command = (entry.get('execution') or {}).get('command', [])
            if command:
                if '{grea}/launch_tool.py' in command:
                    index = command.index('{grea}/launch_tool.py')
                    result[entry['id']] = tool_root / 'src/grea/tools' / (command[index + 1] + '.py')
                    continue
                script = next((x for x in command if x.endswith('.py')), command[0])
                result[entry['id']] = Path(script.replace('{grea}', str(tool_root)).replace('{tools}', str(tool_root)).replace('{python}', sys.executable))
        return result
    source = tool_root / 'bin/recovery'
    tables = {}
    for node in ast.parse(source.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('local', 'skill'):
                    values = ast.literal_eval(node.value)
                    if not isinstance(values, set) or not all(isinstance(x, str) for x in values):
                        raise ValueError('dispatcher tables must be literal sets of tool IDs')
                    tables[target.id] = values
    if set(tables) != {'local', 'skill'}:
        raise ValueError('unsupported dispatcher schema: expected local and skill tables')
    return {name: workspace / 'tools' / folder / f'{name}.py'
            for group, folder in [('local', 'recovery'), ('skill', 'game-building/scripts')]
            for name in tables[group]}


def entries_for(skill):
    """A single Skill directory, or a plugin directory whose skills/*/SKILL.md are all entries."""
    if (skill / 'SKILL.md').is_file():
        return [Path('SKILL.md')]
    found = sorted(p.relative_to(skill) for p in (skill / 'skills').glob('*/SKILL.md')) if (skill / 'skills').is_dir() else []
    if not found:
        raise ValueError('directory must contain SKILL.md or skills/*/SKILL.md')
    return found


def frontmatter_errors(skill, entry):
    text = (skill / entry).read_text(encoding='utf-8')
    match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    meta = dict(line.split(': ', 1) for line in match[1].splitlines() if ': ' in line) if match else {}
    if entry == Path('SKILL.md') and not match:
        return []  # Legacy single-Skill fixtures predate frontmatter checks; plugin entries always require it.
    expected = entry.parent.name if entry.parent != Path('.') else meta.get('name')
    errors = []
    if not meta.get('name') or meta.get('name') != expected:
        errors.append({'code': 'skill_name_mismatch', 'file': str(entry)})
    if not meta.get('description') or len(meta['description']) > 1024:
        errors.append({'code': 'skill_description_invalid', 'file': str(entry)})
    return errors


def check(workspace, skill):
    workspace, skill = workspace.resolve(), skill.resolve()
    entries = entries_for(skill)
    for entry in entries:
        if not within((skill / entry).resolve(), skill):
            raise ValueError('SKILL.md must remain inside the selected skill directory')
    contract = dispatcher_contract(workspace)
    tool_root = tool_root_for(workspace)
    registry = json.loads((tool_root / 'registry.json').read_text(encoding='utf-8'))
    registered = [entry['id'] for entry in registry['tools']]
    errors, warnings, graph, used, count = [], [], {}, set(), 0
    if len(registered) != len(set(registered)):
        errors.append({'code': 'duplicate_registry_id'})
    virtual_skill = tool_root / PLUGIN_REL if (tool_root / PLUGIN_REL / ROUTER).exists() else workspace / SKILL_REL
    if (skill / 'SKILL.md').is_file() and not (virtual_skill / 'SKILL.md').is_file() and virtual_skill != workspace / SKILL_REL:
        virtual_skill = skill  # A standalone Skill candidate resolves its own links.
    for entry in entries:
        errors.extend(frontmatter_errors(skill, entry))
    docs = sorted(skill.rglob('*.md'))

    def actual(virtual):
        if within(virtual, virtual_skill):
            return skill / virtual.relative_to(virtual_skill)
        return virtual

    for doc in docs:
        relative = doc.relative_to(skill)
        if not within(doc.resolve(), skill):
            errors.append({'code': 'skill_symlink_escape', 'file': str(relative)})
            continue
        virtual_doc = virtual_skill / relative
        text = doc.read_text(encoding='utf-8')
        graph[relative] = set()
        for match in re.finditer(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', without_fences(text)):
            target = match[1].strip().strip('<>')
            if re.match(r'^[a-zA-Z][\w+.-]*:', target):
                continue
            path, _, anchor = target.partition('#')
            dest = (virtual_doc.parent / unquote(path)).resolve() if path else virtual_doc
            count += 1
            item = {'file': str(relative), 'target': target}
            if not within(dest, workspace):
                errors.append(dict(item, code='link_outside_workspace'))
                continue
            real = actual(dest)
            allowed_root = skill if within(dest, virtual_skill) else workspace
            if not within(real.resolve(), allowed_root):
                errors.append(dict(item, code='link_symlink_escape'))
                continue
            if not real.exists():
                if within(dest, workspace / 'projects'):
                    warnings.append(dict(item, code='historical_project_source_unavailable'))
                else:
                    errors.append(dict(item, code='missing_link_target'))
                continue
            if within(dest, virtual_skill) and real.suffix == '.md':
                graph[relative].add(dest.relative_to(virtual_skill))
            if anchor and real.suffix == '.md':
                if unquote(anchor) not in heading_ids(real.read_text(encoding='utf-8')):
                    errors.append(dict(item, code='missing_heading_anchor'))
        # Check explicit CLI mentions in prose and fenced examples, not arbitrary tool-like words.
        body = re.sub(r'^---\n.*?\n---\n', '', text, count=1, flags=re.DOTALL)  # frontmatter prose is not a CLI call
        for match in re.finditer(r'\brecovery\s+([a-z_][a-z0-9_-]*)\b', body):
            name = match[1]
            if name not in contract:
                errors.append({'code': 'unknown_recovery_id', 'file': str(relative), 'id': name})
                continue
            used.add(name)
            if not contract[name].is_file():
                errors.append({'code': 'missing_tool_implementation', 'file': str(relative), 'id': name})
    reached, pending = set(), list(entries)
    while pending:
        name = pending.pop()
        if name in reached:
            continue
        reached.add(name)
        pending.extend(graph.get(name, ()))
    for doc in docs:
        name = doc.relative_to(skill)
        if ('references' in name.parts or name.parts[0] == 'shared') and name not in reached:
            errors.append({'code': 'unreachable_reference', 'file': str(name)})
    return {'schema_version': 1, 'ok': not errors, 'errors': errors, 'warnings': warnings,
            'markdown_files': len(docs), 'local_links': count,
            'recovery_ids': sorted(used),
            'size': {'unicode_characters': sum(len(p.read_text(encoding='utf-8')) for p in docs
                                                if within(p.resolve(), skill)),
                     'entry_characters': max(len((skill / e).read_text(encoding='utf-8')) for e in entries)},
            'skills': [str(e.parent) if e.parent != Path('.') else '.' for e in entries],
            'boundary': 'Static inline Markdown links/heading anchors, routing reachability and explicit '
                        'recovery IDs only. No external URL, tool runtime or Agent behavior validation. '
                        'Git-excluded project source links may warn; counts are not tokens.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root', required=True, type=Path)
    parser.add_argument('--skill-dir', type=Path, help='Optional candidate plugin or single skill; resolve external links in workspace')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        root = tool_root_for(args.workspace_root)
        default_skill = root / PLUGIN_REL if (root / PLUGIN_REL / ROUTER).exists() else args.workspace_root / SKILL_REL
        result = check(args.workspace_root, args.skill_dir or default_skill)
    except (OSError, ValueError, SyntaxError, KeyError, TypeError) as error:
        print(json.dumps({'ok': False, 'input_error': str(error)}, ensure_ascii=False))
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{'PASS' if result['ok'] else 'FAIL'}: {result['markdown_files']} Markdown, "
              f"{result['local_links']} local links, {len(result['recovery_ids'])} recovery IDs")
        for item in result['errors'] + result['warnings']:
            print(json.dumps(item, ensure_ascii=False))
        print(result['boundary'])
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
