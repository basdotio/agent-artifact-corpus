"""HTML/Markdown table checks; consistent shape never certifies alignment."""
from html.parser import HTMLParser
import re
from content_signals import compact


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.errors = [], []
        self.depth = 0
        self.rows = self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.depth += 1
            if self.depth == 1:
                self.rows = []
            else:
                self.errors.append('嵌套HTML表格需人工核验')
        if self.depth != 1:
            return
        if tag == 'tr':
            if self.row is not None:
                self.errors.append('HTML表格行标签未闭合')
            self.row = []
            self.rows.append(self.row)
        elif tag in ('td', 'th'):
            if self.cell is not None or self.row is None:
                self.errors.append('HTML表格单元格标签结构异常')
            attrs = dict(attrs)
            try:
                rs, cs = int(attrs.get('rowspan', '1')), int(attrs.get('colspan', '1'))
            except ValueError:
                rs = cs = -1
            self.cell = [rs, cs, '']
            if self.row is not None:
                self.row.append(self.cell)
        elif tag == 'br' and self.cell is not None:
            self.cell[2] += ' '

    def handle_data(self, data):
        if self.cell is not None:
            self.cell[2] += data

    def handle_endtag(self, tag):
        if tag in ('td', 'th'):
            self.cell = None
        elif tag == 'tr':
            if self.cell is not None:
                self.errors.append('HTML表格单元格标签未闭合')
            self.row = self.cell = None
        elif tag == 'table':
            if self.depth == 1:
                if self.row is not None:
                    self.errors.append('HTML表格行标签未闭合')
                self.tables.append(self.rows)
                self.rows = self.row = self.cell = None
            self.depth = max(0, self.depth - 1)


def markdown_tables(body):
    body = re.sub(r'(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1[^\n]*$', '', body)
    groups, group = [], []
    for line in body.splitlines() + ['']:
        if line.lstrip().startswith('|'):
            group.append(line)
        elif group:
            if len(group) >= 2 and re.fullmatch(r'[\s|:\-]+', group[1]) and '-' in group[1]:
                groups.append('\n'.join(group))
            group = []
    return groups


def md_cells(line):
    line = re.sub(r'(`+)(.*?)\1', lambda m: m[0].replace('|', '\x00'), line.strip())
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|') and not line.endswith('\\|'):
        line = line[:-1]
    return [c.strip().replace('\x00', '|') for c in re.split(r'(?<!\\)\|', line)]


def table_fragments(body):
    matches = [(m.start(), m[0]) for m in re.finditer(r'<table\b[^>]*>.*?</table>', body, re.I | re.S)]
    outside = re.sub(r'<table\b[^>]*>.*?</table>', lambda m: ' ' * len(m[0]), body, flags=re.I | re.S)
    matches += [(outside.index(t), t) for t in markdown_tables(outside)]
    return [text for _, text in sorted(matches)]


def html_grid(rows):
    occupied, widths, errors = {}, [], []
    for ri, row in enumerate(rows):
        cursor = 0
        for rs, cs, value in row:
            if not (1 <= rs <= 1000 and 1 <= cs <= 1000):
                errors.append('合并属性特殊或无效')
                continue
            if rs * cs > 10000:
                errors.append('合并范围过大')
                continue
            while (ri, cursor) in occupied:
                cursor += 1
            if ri + rs > len(rows):
                errors.append('rowspan超出实际行数')
            for r in range(ri, min(ri + rs, len(rows))):
                for c in range(cursor, cursor + cs):
                    if (r, c) in occupied:
                        errors.append('合并单元格范围重叠')
                    occupied[r, c] = compact(value) if (r, c) == (ri, cursor) else ''
            cursor += cs
        cols = [c for r, c in occupied if r == ri]
        widths.append(max(cols) + 1 if cols else 0)
    width = max(widths, default=0)
    grid = [[occupied.get((r, c), '') for c in range(width)] for r in range(len(rows))]
    if len(set(widths)) > 1:
        errors.append(f'计入rowspan/colspan后列数不一致（{sorted(set(widths))}）')
    return grid, errors


def table_grids(body):
    grids = []
    for fragment in table_fragments(body):
        if fragment.lstrip().lower().startswith('<table'):
            parser = Tables(); parser.feed(fragment)
            grids += [html_grid(rows)[0] for rows in parser.tables]
        else:
            lines = fragment.splitlines()
            grids.append([[compact(c) for c in md_cells(line)] for line in [lines[0]] + lines[2:]])
    return grids


def table_shape_risks(body):
    parser = Tables(); parser.feed(body)
    flags = list(parser.errors)
    if parser.depth:
        flags.append('HTML表格未闭合，可能截断')
    for index, rows in enumerate(parser.tables, 1):
        _, errors = html_grid(rows)
        flags += [f'第{index}个HTML表格{e}，需原图复核' for e in errors]
    for index, table in enumerate(markdown_tables(re.sub(r'<table\b.*?</table>', '', body, flags=re.I | re.S)), 1):
        widths = [len(md_cells(line)) for line in table.splitlines()]
        if any(not re.fullmatch(r':?-{3,}:?', c.strip()) for c in md_cells(table.splitlines()[1])):
            flags.append(f'第{index}个Markdown表格分隔行无效，需核对渲染')
        if len(set(widths)) > 1:
            flags.append(f'第{index}个Markdown表格列数不一致（{sorted(set(widths))}），需原图复核')
    return list(dict.fromkeys(flags))
