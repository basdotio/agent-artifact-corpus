"""CSS visibility portion of DomService.is_element_visible_according_to_all_parents.

MIT browser-use; iframe transforms/viewport threshold intentionally omitted.
"""


def is_visible(snapshot):
    if not snapshot or not snapshot.bounds:
        return False
    styles = snapshot.computed_styles or {}
    if styles.get('display', '').lower() == 'none' or styles.get('visibility', '').lower() in {'hidden', 'collapse'}:
        return False
    try:
        if float(styles.get('opacity', '1')) <= 0:
            return False
    except (ValueError, TypeError):
        pass
    return snapshot.bounds.width > 0 and snapshot.bounds.height > 0
