"""Compare predicted content across representations; never repair source values."""
from collections import Counter
import html
import re


def semantic_text(text):
    text = html.unescape(text)
    # Autolinks are content, not HTML tags.
    # OCR may wrap a URL with whitespace; retain that text instead of treating
    # the whole autolink as an HTML tag. This comparison never rewrites the URL.
    text = re.sub(r'<((?:https?://|mailto:)[^<>]+)>', r'\1', text)
    text = re.sub(r'!\[([^\]\n]*)\]\((?:<[^>\n]*>|[^\s()]*(?:\([^()]*\)[^\s()]*)*)(?:\s+"[^"]*")?\)', r'\1', text)
    text = re.sub(r'\[([^\]\n]*)\]\((<[^>]+>|[^\s()]*(?:\([^()]*\)[^\s()]*)*)(?:\s+"[^"]*")?\)',
                  lambda m: m[1] if m[1].replace(chr(92), '') == m[2].strip('<>')
                  else m[1] + ' ' + m[2].strip('<>'), text)
    text = re.sub(r'<(?:br\b[^>]*|/(?:td|th|tr|p|li))>', ' ', text, flags=re.I)
    text = html.unescape(re.sub(r'<[^>]+>', '', text))
    # Some Marker versions escape an underscore twice inside a link label.
    text = re.sub(r'\\+([`*_{}\[\]()#+.!|>-])', r'\1', text)
    return re.sub(r'(\*\*|__|~~)(.+?)\1', r'\2', text, flags=re.S)


def compact(text):
    return re.sub(r'\s+', '', semantic_text(text))


def numbers(text):
    text = semantic_text(text).replace('−', '-')
    return Counter(re.findall(r'(?<![\dA-Za-z.])[+-]?(?:\d+\.\d+|\d+)(?:[eE][+-]?\d+)?(?![\dA-Za-z.])', text))


def table_content_risks(body, page):
    """Compare table-local multisets; prose cannot hide a missing table value."""
    from table_signals import table_fragments, table_grids
    predicted = [b for b in page.get('blocks', []) if b['type'] == 'Table' and not b.get('ignored')]
    rendered = table_fragments(body)
    flags = []
    if len(predicted) != len(rendered):
        flags.append(f'位置证据与输出表格数量不同（{len(predicted)}→{len(rendered)}），须原图复核')
    pairs = zip(predicted, rendered) if len(predicted) == len(rendered) else [
        ({'text': ' '.join(b.get('text', '') for b in predicted)}, '\n'.join(rendered))]
    for index, (block, output) in enumerate(pairs, 1):
        evidence = block.get('html') or block.get('text', '')
        missing = numbers(evidence) - numbers(output)
        if missing:
            values = ', '.join(f'{v}×{n}' for v, n in list(missing.items())[:20])
            flags.append(f'第{index}个表格识别/处理证据中的数值在渲染输出中不足：{values}；不得据此自动补值')
        if block.get('html') and table_grids(block['html']) != table_grids(output):
            flags.append(f'第{index}个表格处理后与渲染后的单元格位置/内容不同，须原图核对合并单元格和错列')
    if predicted:
        flags.append('含表格：数值齐全与列数一致仍不能证明行列正确，跨页续表及合并表头须原图核验')
    return flags


def structure_risks(pages):
    """Only warn: printed numbering does not establish a universal heading tree."""
    findings, levels = [], {}
    for number, body in pages:
        flags = []
        for line in body.splitlines():
            match = re.match(r'^\s*(\d+)\.\s*(\d+)\.', line)
            if match and match[1] == match[2]:
                flags.append('有序列表重复编号候选（参考文献须与原页核对），不自动删除原编号')
            m = re.match(r'^(#{1,6})\s+(.+)$', line)
            if not m:
                continue
            kind = ('chinese_section' if re.match(r'[一二三四五六七八九十]+[、．]', m[2]) else
                    'chinese_subsection' if re.match(r'[（(][一二三四五六七八九十]+[）)]', m[2]) else None)
            if kind:
                levels.setdefault(kind, []).append((number, len(m[1])))
        if flags:
            findings.append({'pdf_page': number, 'risks': list(dict.fromkeys(flags))})
    for entries in levels.values():
        if len({level for _, level in entries}) > 1:
            for number in dict.fromkeys(n for n, _ in entries):
                findings.append({'pdf_page': number, 'risks': ['同类印刷章节编号对应不同Markdown标题层级，须核对原文章节结构']})
    return findings


def table_stage_risks(stages):
    findings = []
    for stage in stages:
        after_pages = {p['pdf_page']: p for p in stage['after_table_processing']}
        for before in stage['before_table_processing']:
            after = after_pages.get(before['pdf_page'], {'blocks': []})
            after_blocks = {b.get('id', str(i)): b for i, b in enumerate(after['blocks'])}
            for i, block in enumerate(before['blocks']):
                match = after_blocks.get(block.get('id', str(i)), {})
                missing = numbers(block.get('html') or block.get('text', '')) - numbers(match.get('html') or match.get('text', ''))
                if missing:
                    findings.append({'pdf_page': before['pdf_page'], 'risks': [
                        f'第{i+1}个表格处理前后数值计数减少：' + str(dict(missing)) + '；须回查识别与处理证据，不自动补值']})
    return findings


def output_integrity(before, after):
    if compact(before) == compact(after):
        return []
    return ['整理前后正文内容不一致；缺少数值：' + str(dict(numbers(before) - numbers(after)))]
