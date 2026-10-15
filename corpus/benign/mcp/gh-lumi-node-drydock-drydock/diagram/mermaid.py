"""Mermaid diagram generation from architectural graphs.

Functions return Mermaid source strings (no fences) that visualize dependency
structure, package coupling, seams, and components. All output is deterministic,
escapes special characters, and safely handles edge cases (empty graphs, cycles,
truncation).
"""

from __future__ import annotations

import hashlib

import re
from collections import defaultdict
from typing import Any

from ..arch.graph import DependencyGraph, ModuleMetrics
from ..arch.seams import Seam
from ..core.models import FileId
from ..core.registry import AnalysisContext


def layer_diagram(graph: DependencyGraph, *, max_nodes: int = 60) -> str:
    """Dependency levels as subgraph blocks, with arrows flowing downward.

    Each topological depth becomes a subgraph. Edges point from lower levels
    (higher depth values) to higher levels (lower depth values), showing data
    flow. This is the "how is this built" picture, emphasizing stability order.

    Returns a Mermaid source string (graph TD).
    """
    if not graph.modules:
        return _empty_diagram("No modules found")

    layers = graph.layers()
    if not layers:
        return _empty_diagram("No layers detected")

    # Bounded like every other diagram here. An unbounded layer diagram of a
    # 274-module project is 1,000+ lines and legible to nobody; the most
    # connected modules carry the structure, and the omission is stated rather
    # than silently applied.
    degree = {
        fid: len(graph.forward.get(fid, ())) + len(graph.reverse.get(fid, ()))
        for fid in graph.modules
    }
    ranked = sorted(graph.modules, key=lambda f: (-degree.get(f, 0), f))
    keep = set(ranked[:max_nodes])
    omitted = len(graph.modules) - len(keep)

    lines: list[str] = ["graph TD"]

    # Create subgraphs for each layer, with module counts
    for depth in sorted(layers.keys(), reverse=True):
        modules = layers[depth]
        count = len(modules)
        subgraph_id = f"layer{depth}"
        label = f"Depth {depth} ({count} modules)"
        lines.append(_subgraph(subgraph_id, label, "    "))

        shown = [f for f in sorted(modules) if f in keep]
        if not shown:
            lines.pop()          # nothing survived the cap; drop the subgraph
            continue
        for fid in shown:
            node_id = _sanitize_id(fid)
            node_label = _truncate_label(_short_path(fid), 40)
            lines.append(_node(node_id, node_label, "        "))
        if len(shown) < count:
            lines.append(f'        layer{depth}_more["+{count - len(shown)} more"]')

        lines.append("    end")

    # Draw edges between layers (only load-time edges, moving downward)
    seen_edges = set()
    for edge in sorted(graph.load_time_edges(), key=lambda e: (e.source, e.target)):
        # Both ends must have survived the cap, or the edge points at a node
        # Mermaid would silently invent.
        if edge.source not in keep or edge.target not in keep:
            continue
        src_id = _sanitize_id(edge.source)
        tgt_id = _sanitize_id(edge.target)
        edge_key = (src_id, tgt_id)
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            lines.append(f"    {src_id} --> {tgt_id}")

    if omitted > 0:
        lines.append(
            f'    omitted["{omitted} of {len(graph.modules)} modules omitted; '
            f'showing the most connected"]'
        )

    return "\n".join(lines)


def package_diagram(graph: DependencyGraph, *, max_nodes: int = 40) -> str:
    """Package-level coupling diagram with stability metrics.

    One node per directory (package). Edges represent cross-package dependencies
    from load-time imports. Node labels show afferent coupling (Ca) and
    instability (I = Ce/(Ca+Ce)), so readers see at a glance which packages
    are stable hubs and which are volatile consumers.

    High-degree nodes are prioritized; if truncated, a note indicates how many
    packages were omitted.

    Returns a Mermaid source string (graph LR).
    """
    if not graph.modules:
        return _empty_diagram("No modules found")

    pkg_metrics = graph.package_metrics()
    if not pkg_metrics:
        return _empty_diagram("No packages found")

    # Select top nodes by total coupling (Ca + Ce)
    ranked = sorted(
        pkg_metrics.items(),
        key=lambda x: (x[1].ca + x[1].ce, x[0]),
        reverse=True,
    )

    selected = ranked[: min(max_nodes, len(ranked))]
    selected_ids = {pkg_id for pkg_id, _ in selected}
    truncated = len(ranked) - len(selected)

    lines: list[str] = ["graph LR"]

    # Add nodes with metrics as labels
    for pkg_id, metrics in selected:
        node_id = _sanitize_id(pkg_id or "root")
        instability = round(metrics.instability, 2)
        pkg_label = pkg_id or "(root)"
        node_label = f"{pkg_label}\nCa:{metrics.ca} I:{instability}"
        lines.append(_node(node_id, node_label, "    "))

    # Add cross-package edges from selected nodes
    seen_edges = set()
    for edge in sorted(graph.load_time_edges(), key=lambda e: (e.source, e.target)):
        src_pkg = graph.package_of(edge.source)
        tgt_pkg = graph.package_of(edge.target)

        # Only show edges if source or target is in selected (or both)
        if src_pkg == tgt_pkg:
            continue  # Skip internal edges
        # BOTH ends must be declared. With `and`, an edge whose target was
        # capped out was still emitted, and Mermaid silently invents an
        # unlabelled node for it -- so a truncated diagram grew phantom boxes
        # instead of honestly showing less.
        if src_pkg not in selected_ids or tgt_pkg not in selected_ids:
            continue

        src_id = _sanitize_id(src_pkg or "root")
        tgt_id = _sanitize_id(tgt_pkg or "root")
        edge_key = (src_id, tgt_id)
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            lines.append(f"    {src_id} --> {tgt_id}")

    if truncated > 0:
        trunc_note = f"... and {truncated} more packages (total {len(ranked)})"
        lines.append(_node("note", trunc_note, "    "))

    return "\n".join(lines)


def seam_diagram(ctx: AnalysisContext, graph: DependencyGraph, seam: Seam,
                 *, max_escape_edges: int = 60) -> str:
    """Contract, implementers, and consumers with escaping dependencies.

    The central node is the contract. Implementers are drawn below it as the
    extractable unit. Consumers are shown separately (outside the unit).
    Escaping dependencies (members that depend outside the unit) are annotated.

    The diagram visualizes what would be extracted if you cut here: the contract,
    its implementers, and everything they bring along (escapes). The cohesion
    score and verdict are in the title.

    Returns a Mermaid source string (graph TD).
    """
    if not seam.implementers:
        return _empty_diagram("No implementers for this contract")

    lines: list[str] = ["graph TD"]

    # Title with verdict and cohesion
    title_text = f"Seam: {seam.verdict} (cohesion: {seam.cohesion:.2f})"
    lines.append(_node("title", title_text, "    "))

    # Contract node at top
    contract_id = _sanitize_id(seam.contract)
    contract_label = _truncate_label(_short_path(seam.contract), 30)
    types_str = ", ".join(seam.contract_types[: min(3, len(seam.contract_types))])
    if len(seam.contract_types) > 3:
        types_str += f", +{len(seam.contract_types) - 3}"
    contract_full = f"{contract_label}\\n({types_str})"
    lines.append(_node(contract_id, contract_full, "    "))

    # Implementers in subgraph (the extractable unit)
    impl_ids = []
    if seam.implementers:
        lines.append('    subgraph impl["Implementers (extractable unit)"]')
        for fid in sorted(seam.implementers):
            node_id = _sanitize_id(fid)
            impl_ids.append(node_id)
            node_label = _truncate_label(_short_path(fid), 30)
            lines.append(_node(node_id, node_label, "        "))
        lines.append("    end")

        # Implementers depend on the contract, so the arrow points AT the
        # contract -- the same direction as every other edge in every other
        # diagram here. Drawing it the other way asserted that the contract
        # depends on its own implementations, which is not merely backwards
        # but the precise inversion a plugin architecture exists to avoid.
        for impl_id in impl_ids:
            lines.append(f"    {impl_id} --> {contract_id}")

    # Consumers (outside the unit, depend on contract)
    if seam.consumers:
        lines.append('    subgraph cons["Consumers (depend on contract)"]')
        for fid in sorted(seam.consumers):
            node_id = _sanitize_id(fid)
            node_label = _truncate_label(_short_path(fid), 30)
            lines.append(_node(node_id, node_label, "        "))
        lines.append("    end")

        # Connect consumers to contract
        for fid in sorted(seam.consumers):
            node_id = _sanitize_id(fid)
            lines.append(f"    {node_id} --> {contract_id}")

    # Escaping dependencies: draw from unit to each escape
    if seam.escapes:
        lines.append('    subgraph esc["Escaping dependencies"]')
        escape_set = set(seam.escapes)
        escape_ids = []
        for fid in sorted(seam.escapes):
            node_id = _sanitize_id(fid)
            escape_ids.append(node_id)
            node_label = _truncate_label(_short_path(fid), 30)
            lines.append(_node(node_id, node_label, "        "))
        lines.append("    end")

        # Only edges that actually exist. Drawing the cartesian product of
        # implementers x escapes produced 432 edges for a seam that has 21 real
        # ones, and every fabricated edge asserted a dependency the code does
        # not have. A diagram that invents relationships is worse than none --
        # this one is meant to be read as evidence.
        unit = {seam.contract, *seam.implementers}
        drawn = 0
        for member in sorted(unit):
            for target in sorted(graph.forward.get(member, ())):
                if target not in escape_set:
                    continue
                if drawn >= max_escape_edges:
                    break
                lines.append(
                    f"    {_sanitize_id(member)} -.-> {_sanitize_id(target)}"
                )
                drawn += 1
        real_total = sum(
            1 for m in unit for t in graph.forward.get(m, ()) if t in escape_set
        )
        if real_total > drawn:
            lines.append(
                f'    escape_more["+{real_total - drawn} further escaping '
                f'dependencies not drawn"]'
            )

    return "\n".join(lines)


def component_diagram(
    graph: DependencyGraph, files: set[FileId], *, title: str = ""
) -> str:
    """An arbitrary set of files and their internal dependencies.

    Shows only edges where both source and target are in the file set. This
    lets you zoom into a component and see its internal structure without
    external noise.

    If `title` is provided, it becomes the graph title. If the file set is
    large, nodes are ranked by degree (most connected first) and truncated
    at max_nodes with a truncation note.

    Returns a Mermaid source string (graph TD).
    """
    if not files:
        return _empty_diagram("No files in component")

    # Rank files by degree (in/out edges within the component)
    degree: dict[FileId, int] = defaultdict(int)
    for edge in graph.edges:
        if edge.source in files:
            degree[edge.source] += 1
        if edge.target in files:
            degree[edge.target] += 1

    ranked = sorted(files, key=lambda f: (-degree[f], f))
    max_nodes = 40
    selected = set(ranked[: min(max_nodes, len(ranked))])
    truncated = len(ranked) - len(selected)

    lines: list[str] = ["graph TD"]

    if title:
        safe_title = _escape_label(title)
        lines.append(_node("title", safe_title, "    "))

    # Add selected nodes
    for fid in sorted(selected):
        node_id = _sanitize_id(fid)
        node_label = _truncate_label(_short_path(fid), 30)
        lines.append(_node(node_id, node_label, "    "))

    # Add edges (both source and target must be selected)
    seen_edges = set()
    for edge in sorted(graph.edges, key=lambda e: (e.source, e.target)):
        if edge.source not in selected or edge.target not in selected:
            continue
        src_id = _sanitize_id(edge.source)
        tgt_id = _sanitize_id(edge.target)
        edge_key = (src_id, tgt_id)
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            lines.append(f"    {src_id} --> {tgt_id}")

    if truncated > 0:
        trunc_note = f"... and {truncated} more files (showing {len(selected)})"
        lines.append(_node("note", trunc_note, "    "))

    return "\n".join(lines)


# -- Helpers ------------------------------------------------------------------


def _sanitize_id(path: str) -> str:
    """Turn a file path into a unique, valid Mermaid node id.

    Mermaid ids must match ``^[A-Za-z][A-Za-z0-9_]*$``, and real paths contain
    slashes, dots, dashes and spaces -- all of which collapse to the same
    character when replaced naively. ``a/b.py``, ``a-b.py``, ``a.b.py`` and
    ``a_b.py`` all became ``a_b_py``, so four distinct modules rendered as one
    node with their edges merged. Nothing failed; the diagram was simply a
    picture of a codebase that does not exist.

    A short digest of the original path is therefore appended. Ids are never
    shown to a reader -- labels carry the real name -- so the cost is nil and
    the guarantee is absolute: distinct paths always get distinct ids, and the
    same path always gets the same id.
    """
    safe = re.sub(r"[^A-Za-z0-9_]", "_", path).strip("_") or "node"
    if not safe[0].isalpha():
        safe = "n" + safe
    digest = hashlib.sha1(path.encode("utf-8", "surrogatepass")).hexdigest()[:6]
    return f"{safe}_{digest}"


#: Mermaid has no backslash escape. Inside a quoted label the only way to
#: express these characters is an HTML entity; a backslash-escaped quote is a
#: parse error, not a quoted quote.
_LABEL_ENTITIES = {
    "#": "#35;",
    '"': "#quot;",
    "<": "#lt;",
    ">": "#gt;",
    "{": "#123;",
    "}": "#125;",
}


def _node(node_id: str, label: str, indent: str = "    ") -> str:
    """Emit a node declaration, escaping the label exactly once.

    Every node in every diagram goes through here. Escaping at the call sites
    instead meant thirteen places had to remember, one of them did not, and a
    single directory named `quote"dir` produced a chart that failed to render.
    """
    return f'{indent}{node_id}["{_escape_label(label)}"]'


def _subgraph(sub_id: str, label: str, indent: str = "    ") -> str:
    return f'{indent}subgraph {sub_id}["{_escape_label(label)}"]'


def _escape_label(text: str) -> str:
    """Make `text` safe inside a Mermaid quoted label.

    Uses HTML entities, because Mermaid does not support backslash escaping.
    Emitting ``\"`` for a quote -- the obvious thing, and what this did
    originally -- makes the whole diagram fail to parse, so a single directory
    named ``quote"dir`` was enough to produce an unrenderable chart. Verified
    against mermaid-cli 11.16: the backslash form errors, the entity form
    renders.

    ``#`` is escaped first, since it begins every other entity.
    """
    out = text.replace("#", _LABEL_ENTITIES["#"])
    for char, entity in _LABEL_ENTITIES.items():
        if char == "#":
            continue
        out = out.replace(char, entity)
    # Newlines would end the statement; Mermaid renders <br/> as a line break.
    return out.replace("\r\n", "<br/>").replace("\n", "<br/>").replace("\r", "<br/>")


def _truncate_label(text: str, max_len: int) -> str:
    """Shorten a label for display. Does NOT escape -- see `_node`.

    Escaping used to happen here, which meant every caller that built a label
    some other way silently skipped it. `package_diagram` did exactly that and
    produced a diagram that would not parse.
    """
    if len(text) <= max_len:
        return text
    return text[: max(1, max_len - 1)] + "…"


def _short_path(fid: FileId) -> str:
    """Extract a readable short name from a file ID.

    For deep paths like "drydock/arch/graph.py", returns "arch/graph.py".
    """
    parts = fid.split("/")
    if len(parts) > 2:
        return "/".join(parts[-2:])
    return fid


def _empty_diagram(reason: str) -> str:
    """Return a minimal valid Mermaid diagram when there's nothing to show."""
    lines = [
        "graph TD",
        f"    empty[\"{_escape_label(reason)}\"]",
    ]
    return "\n".join(lines)
