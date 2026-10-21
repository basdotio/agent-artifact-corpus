"""Adapted from browser-use dom/enhanced_snapshot.py; MIT, see LICENSE.

Only styles, bounds, clickability and paint order are retained. No field values.
CDP snapshot coordinates are kept in their native CSS-pixel coordinate space.
"""
from .views import DOMRect, EnhancedSnapshotNode

REQUIRED_COMPUTED_STYLES = [
    'display', 'visibility', 'opacity', 'overflow', 'overflow-x', 'overflow-y',
    'cursor', 'pointer-events', 'position', 'background-color',
]


def _parse_rare_boolean_data(rare_data_set: set[int], index: int) -> bool:
    return index in rare_data_set


def _parse_computed_styles(strings, style_indices):
    return {REQUIRED_COMPUTED_STYLES[i]: strings[index]
            for i, index in enumerate(style_indices)
            if i < len(REQUIRED_COMPUTED_STYLES) and 0 <= index < len(strings)}


def build_snapshot_lookup(snapshot):
    """Upstream's O(n) indexed join of backend node IDs and layout records."""
    lookup = {}
    strings = snapshot['strings']
    for document in snapshot['documents']:
        nodes, layout = document['nodes'], document['layout']
        layout_indices = {}
        for layout_index, node_index in enumerate(layout.get('nodeIndex', [])):
            layout_indices.setdefault(node_index, layout_index)
        clickable = set(nodes.get('isClickable', {}).get('index', []))
        for index, backend_id in enumerate(nodes.get('backendNodeId', [])):
            styles, bounds, paint_order = {}, None, None
            layout_index = layout_indices.get(index)
            if layout_index is not None:
                boxes = layout.get('bounds', [])
                if layout_index < len(boxes) and len(boxes[layout_index]) >= 4:
                    bounds = DOMRect(*boxes[layout_index][:4])
                style_rows = layout.get('styles', [])
                if layout_index < len(style_rows):
                    styles = _parse_computed_styles(strings, style_rows[layout_index])
                orders = layout.get('paintOrders', [])
                if layout_index < len(orders):
                    paint_order = orders[layout_index]
            lookup[backend_id] = EnhancedSnapshotNode(
                is_clickable=_parse_rare_boolean_data(clickable, index),
                cursor_style=styles.get('cursor'), bounds=bounds,
                computed_styles=styles, paint_order=paint_order,
            )
    return lookup
