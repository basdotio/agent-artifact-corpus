"""Omni glue: CDP trees -> vendored reader -> compact, value-free observation."""
from html import escape
import re
from urllib.parse import urljoin, urlsplit

from ._vendor.browser_use_dom.clickable_elements import ClickableElementDetector
from ._vendor.browser_use_dom.enhanced_snapshot import build_snapshot_lookup
from ._vendor.browser_use_dom.markdown_extractor import convert_html_to_markdown
from ._vendor.browser_use_dom.paint_order import PaintOrderRemover
from ._vendor.browser_use_dom.views import (
    EnhancedAXNode, EnhancedAXProperty, EnhancedDOMTreeNode, SimplifiedNode,
)
from ._vendor.browser_use_dom.visibility import is_visible

NODE_LIMIT = 50000
PAINT_LIMIT = 3000
REF_LIMIT = 96
CONTENT_LIMIT = 1000000
IDENTITY_ATTRS = ('role', 'type', 'href', 'id', 'name', 'formaction', 'contenteditable')
AX_STATES = {'disabled', 'checked', 'expanded', 'pressed', 'selected', 'required',
             'readonly', 'multiselectable', 'focusable', 'editable', 'settable', 'hidden'}
SKIP = {'script', 'style', 'head', 'noscript', 'template', 'iframe', 'frame',
        'input', 'textarea', 'select', 'option'}
HTML_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr', 'ul', 'ol', 'li',
             'table', 'thead', 'tbody', 'tr', 'td', 'th', 'pre', 'code', 'blockquote',
             'strong', 'em', 'div', 'section', 'article', 'main', 'span'}


def norm(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def editable(node):
    return (node.tag_name in {'input', 'textarea', 'select'} or
            node.attributes.get('contenteditable', 'false').lower() not in {'false', 'inherit'})


def compact_tree(dom, ax, snapshot):
    """Use DOM backend IDs as the only join key. Never reconstruct a selector."""
    layouts = build_snapshot_lookup(snapshot)
    ax_lookup = {}
    for raw in ax.get('nodes', []):
        backend = raw.get('backendDOMNodeId')
        if backend is not None and not raw.get('ignored'):
            # Never retain AX value/description or value-bearing arbitrary properties.
            ax_name = raw.get('name', {})
            name_from_value = any(source.get('attribute') == 'value' for source in ax_name.get('sources', []))
            ax_lookup[backend] = EnhancedAXNode(
                role=raw.get('role', {}).get('value', ''),
                name='' if name_from_value else ax_name.get('value', ''),
                properties=[EnhancedAXProperty(p['name'], p.get('value', {}).get('value'))
                            for p in raw.get('properties', []) if p['name'] in AX_STATES],
            )
    nodes, visible, blocked = [], {}, {}
    coverage = {'content_truncated': False, 'links_omitted': 0, 'controls_omitted': 0,
                'unsupported_frames': 0, 'unsupported_closed_shadow_roots': 0,
                'processing_limited': False, 'paint_filter_limited': False,
                'ref_binding_limit': REF_LIMIT, 'ref_bindings_failed': 0}
    pending = [(dom, None, False, False)]
    while pending and len(nodes) < NODE_LIMIT:
        raw, parent, ancestor_hidden, ancestor_editable = pending.pop()
        attrs = dict(zip(raw.get('attributes', [])[::2], raw.get('attributes', [])[1::2]))
        # DOM attributes can contain secrets; drop values and unrelated data immediately.
        attrs = {k: v for k, v in attrs.items() if k in {
            *IDENTITY_ATTRS, 'class', 'aria-label', 'placeholder', 'title', 'disabled',
            'hidden', 'inert', 'tabindex', 'for', 'download', 'onclick', 'onmousedown',
            'onmouseup', 'onkeydown', 'onkeyup', 'aria-disabled',
        }}
        # Event source code is not needed by upstream's presence-based detector.
        attrs = {k: '' if k.startswith('on') else v for k, v in attrs.items()}
        backend = raw['backendNodeId']
        node = EnhancedDOMTreeNode(backend, raw['nodeType'], raw['nodeName'], attrs,
                                   parent_node=parent, snapshot_node=layouts.get(backend),
                                   ax_node=ax_lookup.get(backend), editable_ancestor=ancestor_editable)
        if parent:
            parent.children.append(node)
        nodes.append(node)
        styles = node.snapshot_node.computed_styles if node.snapshot_node else {}
        css_hidden = (styles.get('display') == 'none' or
                      styles.get('visibility') in {'hidden', 'collapse'} or
                      styles.get('opacity') == '0')
        hidden = ancestor_hidden or css_hidden or 'hidden' in attrs or 'inert' in attrs
        field = ancestor_editable or editable(node)
        blocked[backend] = hidden or field
        visible[backend] = not hidden and is_visible(node.snapshot_node)
        if raw['nodeType'] == 3 and not hidden and not field:
            node.node_value = raw.get('nodeValue', '')
        if node.tag_name in {'iframe', 'frame'}:
            coverage['unsupported_frames'] += 1
            continue
        children = list(raw.get('children', []))
        for shadow in raw.get('shadowRoots', []):
            if shadow.get('shadowRootType') == 'open':
                children.append(shadow)
            elif shadow.get('shadowRootType') == 'closed':
                coverage['unsupported_closed_shadow_roots'] += 1
            # Browser user-agent roots are not authored open Shadow DOM.
        pending.extend((child, node, hidden, field) for child in reversed(children))
    coverage['processing_limited'] = bool(pending)

    # Use the upstream paint-order grouping/rectangle union, but bound its input.
    paintable = [SimplifiedNode(n) for n in nodes if visible[n.backend_node_id]
                 and n.snapshot_node.paint_order is not None]
    coverage['paint_filter_limited'] = len(paintable) > PAINT_LIMIT
    paintable = paintable[:PAINT_LIMIT]
    if nodes:
        root = SimplifiedNode(nodes[0], paintable)
        PaintOrderRemover(root).calculate_paint_order()
    for item in paintable:
        if item.ignored_by_paint_order:
            visible[item.original_node.backend_node_id] = False
    return nodes, visible, blocked, coverage


def render_observation(dom, ax, snapshot, metadata, tab_id):
    nodes, visible, blocked, coverage = compact_tree(dom, ax, snapshot)
    texts = {}
    for node in reversed(nodes):
        if blocked[node.backend_node_id] or node.tag_name in SKIP:
            texts[node.backend_node_id] = ''
        elif node.node_type == 3:
            texts[node.backend_node_id] = norm(node.node_value)[:513] if visible[node.backend_node_id] else ''
        else:
            texts[node.backend_node_id] = norm(' '.join(texts[c.backend_node_id] for c in node.children))[:513]

    candidates = []
    for node in nodes:
        if node.node_type != 1 or node.editable_ancestor or not visible[node.backend_node_id] or node.tag_name in {'iframe', 'frame'}:
            continue
        if node.snapshot_node and node.snapshot_node.is_clickable:
            node.has_js_click_listener = True  # CDP's batch isClickable includes listener evidence.
        if not ClickableElementDetector.is_interactive(node):
            continue
        attrs, ax_node = node.attributes, node.ax_node
        is_link = node.tag_name in {'a', 'area'} and 'href' in attrs or (ax_node and ax_node.role == 'link') or attrs.get('role') == 'link'
        kind = 'links' if is_link else 'controls'
        # AX accessible names, not AX field values. Editable contents are never a fallback.
        label = norm(ax_node.name if ax_node else '')
        if editable(node):
            label = norm(attrs.get('aria-label')) or (label if node.tag_name in {'input', 'textarea', 'select'} else '')
        label = label or norm(attrs.get('placeholder')) or norm(attrs.get('title')) or texts[node.backend_node_id]
        if len(label) > 512:
            coverage[kind + '_omitted'] += 1
            continue
        expected = {'_tag': node.tag_name, **{k: attrs.get(k) for k in IDENTITY_ATTRS}}
        if is_link:
            href = urljoin(metadata['baseURI'], attrs['href']) if 'href' in attrs else None
            if href:
                try:
                    parsed = urlsplit(href)
                    if parsed.scheme not in {'http', 'https'} or parsed.username is not None or parsed.password is not None:
                        href = None  # Never expose javascript/data payloads or URL credentials.
                except ValueError:
                    href = None
            item = {'text': label, 'href': href,
                    'download_hint': 'download' in attrs or bool(re.search(r'\.(pdf|zip|docx?|xlsx?|pptx?|csv|epub)(?:[?#]|$)', href or '', re.I))}
        else:
            role = attrs.get('role') or (ax_node.role if ax_node and ax_node.role not in {'generic', 'none'} else '') or 'button'
            states = {p.name: p.value for p in ax_node.properties if p.name in AX_STATES - {'focusable', 'editable', 'settable', 'hidden'}} if ax_node else {}
            disabled = 'disabled' in attrs or bool(states.pop('disabled', False)) or attrs.get('aria-disabled') == 'true'
            item = {'role': role, 'name': label, 'disabled': disabled, **states}
            if node.tag_name == 'input' or 'type' in attrs:
                item['type'] = attrs.get('type', 'text')
        candidates.append((node.backend_node_id, expected, kind, item))

    regions = [n for n in nodes if n.node_type == 1 and visible[n.backend_node_id]
               and (n.tag_name == 'main' or n.attributes.get('role') == 'main')]
    if not regions:
        regions = [n for n in nodes if n.tag_name == 'article' and visible[n.backend_node_id]][:1]
    if not regions:
        regions = [n for n in nodes if n.tag_name == 'body'][:1]
    region_ids = {n.backend_node_id for n in regions}
    for node in nodes:
        if node.tag_name == 'dialog' or node.attributes.get('role') in {'dialog', 'alertdialog'}:
            parent = node.parent_node
            while parent and parent.backend_node_id not in region_ids:
                parent = parent.parent_node
            if parent is None:
                regions.append(node)
                region_ids.add(node.backend_node_id)
    chunks, length = [], 0
    stack = [(n, False) for n in reversed(regions)]
    while stack:
        node, closing = stack.pop()
        tag = node.tag_name
        if closing:
            fragment = f'</{tag}>'
        elif blocked[node.backend_node_id] or tag in SKIP:
            continue
        elif tag in {'nav', 'header', 'footer', 'aside'} and node.backend_node_id not in region_ids:
            continue
        elif node.node_type == 3:
            if not visible[node.backend_node_id]:
                continue
            fragment = escape(node.node_value)
        else:
            output_tag = tag if tag in HTML_TAGS else 'span'
            fragment = f'<{output_tag}>' if node.node_type == 1 else ''
            if node.node_type == 1 and output_tag not in {'br', 'hr'}:
                # Close with the safe output tag; never emit page attributes/URLs.
                stack.append((EnhancedDOMTreeNode(0, 1, output_tag), True))
            stack.extend((child, False) for child in reversed(node.children))
        length += len(fragment)
        if length > CONTENT_LIMIT:
            coverage['content_truncated'] = True
            break
        chunks.append(fragment)
    content, _, _ = convert_html_to_markdown(''.join(chunks))
    result = {'tab_id': tab_id, 'url': metadata['url'], 'title': metadata['title'],
              'content': content, 'links': [], 'controls': [], 'coverage': coverage,
              'truncated': coverage['content_truncated'] or coverage['processing_limited'] or
              bool(coverage['links_omitted'] or coverage['controls_omitted'])}
    return result, candidates
