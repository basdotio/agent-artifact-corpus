"""
Component boundary detection via import graph analysis.

Detects clusters of files that naturally belong together based on import density,
identifies bridge files connecting multiple clusters, and finds orphan files.

Uses connected-components clustering followed by modularity-based subdivision
for components exceeding the size threshold.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping

from ..core.models import FileId, SourceFile
from ..core.output import to_jsonable
from ..core.paths import common_prefix
from ..core.registry import AnalysisContext, Option

__all__ = ["BoundariesAnalyzer"]


@dataclass(frozen=True, slots=True)
class _Cluster:
    """Internal cluster representation during analysis."""
    id: int
    files: frozenset[FileId]
    internal_edges: int
    external_deps: frozenset[FileId]
    external_dependents: frozenset[FileId]


class BoundariesAnalyzer:
    """Detects natural component boundaries in a codebase.

    Builds the import graph, finds connected components, then subdivides
    large components using greedy modularity maximization (label propagation).
    """

    name = "boundaries"
    summary = "Detect natural component clusters and boundaries"
    description = (
        "Analyzes the import graph to find clusters of tightly-connected files "
        "that form natural components. Reports internal vs. external dependencies, "
        "bridge files connecting clusters, orphan files, and extraction risk "
        "estimates. Uses connected-component detection followed by modularity-based "
        "subdivision for large components."
    )

    options = (
        Option(
            name="min_cluster",
            type=int,
            default=2,
            help="Minimum files per cluster (smaller components are discarded)",
        ),
        Option(
            name="max_cluster_split",
            type=int,
            default=15,
            help="Threshold: components larger than this are subdivided by modularity",
        ),
        Option(
            name="include_external",
            type=bool,
            default=False,
            help="Include third-party external imports in the graph",
        ),
    )

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        """Run boundary detection."""
        min_cluster: int = opts.get("min_cluster", 2)
        max_cluster_split: int = opts.get("max_cluster_split", 15)
        include_external: bool = opts.get("include_external", False)

        ctx.reporter.step("Building import graph")
        graph, resolution_stats = self._build_graph(
            ctx, include_external=include_external
        )

        ctx.reporter.step("Finding connected components")
        components = self._find_components(graph)

        ctx.reporter.step("Subdividing large components")
        clusters = self._subdivide_components(
            components, graph, max_cluster_split, min_cluster
        )

        ctx.reporter.step("Finding bridge files")
        bridges = self._find_bridges(graph, clusters)

        ctx.reporter.step("Finding orphan files")
        orphans = self._find_orphans(ctx, graph, clusters)

        # Invariant: a file inside a detected cluster is by definition not an
        # orphan. Violating this was the pre-0.2 bug -- orphan ids were built
        # in a different path space to the graph, so the two sets could not
        # intersect and every file was reported as an orphan.
        #
        # Enforced, not asserted: a bare `assert` disappears under `python -O`
        # and would crash the run on someone else's codebase. Correct the
        # output and say so loudly instead.
        clustered = frozenset().union(*(c.files for c in clusters)) if clusters else frozenset()
        overlap = clustered & frozenset(orphans)
        if overlap:
            ctx.reporter.warn(
                f"internal inconsistency: {len(overlap)} file(s) appeared as both "
                f"clustered and orphaned; removing them from the orphan list. "
                f"Please report this with the project layout: "
                f"{sorted(overlap)[:3]}"
            )
            orphans = [o for o in orphans if o not in overlap]

        return {
            "summary": {
                "total_files": len(ctx.source_files()),
                "files_in_graph": len(graph["all_files"]),
                "resolved_edges": resolution_stats["resolved"],
                "unresolved_imports": resolution_stats["unresolved"],
                "external_imports": resolution_stats["external"],
                "ambiguous_imports": resolution_stats["ambiguous"],
                "clusters_found": len(clusters),
                "bridge_files": len(bridges["top"]),
                "bridge_files_total": bridges["total"],
                "orphan_files": len(orphans),
            },
            "clusters": [self._cluster_to_dict(c) for c in clusters],
            "bridges": {
                "total": bridges["total"],
                "top": bridges["top"],
            },
            "orphans": orphans,
            "meta": ctx.meta(),
        }

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        """Render analysis result as markdown."""
        lines = [
            f"# Boundary Detection: {result['meta']['project']}",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
        ]

        s = result["summary"]
        lines.extend([
            f"| Total Files | {s['total_files']} |",
            f"| Files in Graph | {s['files_in_graph']} |",
            f"| Resolved Import Edges | {s['resolved_edges']} |",
            f"| Unresolved Imports | {s['unresolved_imports']} |",
            f"| External Imports | {s['external_imports']} |",
            f"| Ambiguous Imports | {s['ambiguous_imports']} |",
            f"| Clusters Found | {s['clusters_found']} |",
            f"| Bridge Files | {s['bridge_files']} (total: {s['bridge_files_total']}) |",
            f"| Orphan Files | {s['orphan_files']} |",
            "",
        ])

        if result["clusters"]:
            lines.extend(["## Component Clusters", ""])
            for cluster in result["clusters"]:
                prefix = cluster["common_prefix"] or f"cluster-{cluster['id']}"
                lines.append(f"### {prefix} ({cluster['file_count']} files)")
                lines.append("")
                lines.extend([
                    f"**Cohesion:** {cluster['cohesion']:.3f} | "
                    f"**Internal Edges:** {cluster['internal_edges']} | "
                    f"**External Deps:** {cluster['external_dep_count']} | "
                    f"**External Dependents:** {cluster['external_dependent_count']}",
                    "",
                    "**Extraction Risk:** " +
                    f"**{cluster['extraction_risk']}** - {cluster['extraction_reason']}",
                    "",
                ])

                lines.append("**Files:**")
                for f in cluster["files"][:20]:
                    lines.append(f"- `{f}`")
                if len(cluster["files"]) > 20:
                    lines.append(f"- ... and {len(cluster['files']) - 20} more")
                lines.append("")

        if result["bridges"]["top"]:
            lines.extend(["## Bridge Files", ""])
            lines.append(
                f"Files connecting multiple clusters (showing top {len(result['bridges']['top'])} "
                f"of {result['bridges']['total']} total):"
            )
            lines.extend(["", "| File | Connections | Imported By | Imports |",
                         "|------|-------------|-------------|---------|"])
            for b in result["bridges"]["top"]:
                dirs = ", ".join(b["connects_dirs"][:3])
                lines.append(
                    f"| `{b['file']}` | {dirs} | "
                    f"{b['imported_by_count']} | {b['imports_count']} |"
                )
            lines.append("")

        if result["orphans"]:
            lines.extend(["## Orphan Files", ""])
            lines.append("No import relationships (easy to extract or remove):")
            lines.append("")
            for f in result["orphans"][:20]:
                lines.append(f"- `{f}`")
            if len(result["orphans"]) > 20:
                lines.append(f"- ... and {len(result['orphans']) - 20} more")

        return "\n".join(lines)

    # -- implementation ------------------------------------------------

    def _build_graph(
        self, ctx: AnalysisContext, include_external: bool
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Build the import graph from resolved imports.

        Returns:
            (graph, resolution_stats) where graph is {
                'all_files': set of FileId,
                'forward': {FileId -> set of FileId},
                'reverse': {FileId -> set of FileId},
            }
        """
        forward: dict[FileId, set[FileId]] = defaultdict(set)
        reverse: dict[FileId, set[FileId]] = defaultdict(set)

        # Build all_files set first (before processing imports) to ensure
        # we can check membership when resolving targets.
        source_files = ctx.source_files()
        all_files: set[FileId] = {sf.id for sf in source_files}

        resolved = 0
        unresolved = 0
        external = 0
        ambiguous = 0

        for sf in source_files:
            imports = ctx.imports(sf)

            for imp in imports:
                res = ctx.index.resolve(imp, from_file=sf.id, lang=sf.lang)

                if res.ambiguous:
                    ambiguous += 1
                    continue

                if res.external and not include_external:
                    external += 1
                    continue

                if not res.targets:
                    unresolved += 1
                    continue

                resolved += 1
                for target in res.targets:
                    # Only keep intra-project edges
                    if target in all_files and target != sf.id:
                        forward[sf.id].add(target)
                        reverse[target].add(sf.id)

        return (
            {
                "all_files": all_files,
                "forward": dict(forward),
                "reverse": dict(reverse),
            },
            {
                "resolved": resolved,
                "unresolved": unresolved,
                "external": external,
                "ambiguous": ambiguous,
            },
        )

    def _find_components(
        self, graph: dict[str, Any]
    ) -> list[set[FileId]]:
        """Find connected components using BFS.

        Returns list of disjoint sets of FileIds, one per component.
        """
        forward = graph["forward"]
        reverse = graph["reverse"]
        all_files = graph["all_files"]

        # Build undirected adjacency
        adj: dict[FileId, set[FileId]] = defaultdict(set)
        for src, targets in forward.items():
            for tgt in targets:
                adj[src].add(tgt)
                adj[tgt].add(src)

        # BFS from each unvisited node
        visited: set[FileId] = set()
        components: list[set[FileId]] = []

        for start in sorted(all_files):  # Deterministic order
            if start in visited:
                continue

            component: set[FileId] = set()
            queue: list[FileId] = [start]

            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                component.add(node)

                for neighbor in sorted(adj.get(node, [])):
                    if neighbor not in visited:
                        queue.append(neighbor)

            if component:
                components.append(component)

        return components

    def _subdivide_components(
        self,
        components: list[set[FileId]],
        graph: dict[str, Any],
        max_size: int,
        min_cluster: int,
    ) -> list[_Cluster]:
        """Subdivide large components using greedy label propagation.

        For components under max_size, return as-is.
        For larger ones, use label propagation to find sub-clusters.
        """
        forward = graph["forward"]
        reverse = graph["reverse"]
        clusters: list[_Cluster] = []
        cluster_id = 0

        for component in components:
            if len(component) <= max_size:
                # Keep component as single cluster if >= min_cluster
                if len(component) >= min_cluster:
                    c = self._make_cluster(
                        cluster_id, component, forward, reverse
                    )
                    clusters.append(c)
                    cluster_id += 1
            else:
                # Use label propagation to subdivide
                sub = self._detect_communities(component, forward, reverse)
                for sub_cluster in sub:
                    if len(sub_cluster) >= min_cluster:
                        c = self._make_cluster(
                            cluster_id, sub_cluster, forward, reverse
                        )
                        clusters.append(c)
                        cluster_id += 1

        return clusters

    def _detect_communities(
        self, component: set[FileId], forward: dict, reverse: dict
    ) -> list[set[FileId]]:
        """Split one connected component into communities.

        Greedy agglomerative modularity maximisation (Clauset-Newman-Moore):
        every file starts alone, and the merge that raises modularity most is
        applied repeatedly until no merge improves it.

        Why not label propagation: the obvious "adopt your neighbours' majority
        label" loop collapses to a single label on any densely connected graph
        -- exactly the failure this analyzer exists to avoid. It reproduces the
        pre-0.2 behaviour (one giant cluster, no usable cut points) while
        claiming to do community detection.

        Inter-community edge counts are maintained INCREMENTALLY. Recomputing
        them by rescanning members on every pass is the natural way to write
        this and is cubic in the file count; it ran for minutes on a 5,000-file
        tree. Merging is now proportional to the number of community pairs that
        actually share an edge.

        Limits: modularity has a known resolution limit and will not surface
        communities much smaller than sqrt(edge count). Directory layout only
        breaks ties between equally-good merges, so structural coupling always
        wins over packaging.
        """
        nodes = sorted(component)
        if len(nodes) < 4:
            return [set(nodes)]

        # Undirected adjacency inside the component: an import is evidence of
        # coupling regardless of direction.
        adj: dict[FileId, set[FileId]] = {}
        for src in nodes:
            adj[src] = ((set(forward.get(src, ())) | set(reverse.get(src, ())))
                        & component) - {src}

        degree = {n: len(adj[n]) for n in nodes}
        two_m = sum(degree.values())
        if two_m == 0:
            return [{n} for n in nodes]

        members: dict[int, set[FileId]] = {i: {n} for i, n in enumerate(nodes)}
        comm_of: dict[FileId, int] = {n: i for i, n in enumerate(nodes)}
        deg_sum: dict[int, int] = {i: degree[n] for i, n in enumerate(nodes)}

        # Sparse inter-community edge counts, kept up to date across merges.
        between: dict[int, dict[int, int]] = {i: {} for i in range(len(nodes))}
        for n in nodes:
            a = comm_of[n]
            for nb in adj[n]:
                b = comm_of[nb]
                if a != b:
                    between[a][b] = between[a].get(b, 0) + 1
        # No halving here. `between` is a dict-of-dicts, so an edge between
        # communities a and b lands in between[a][b] AND between[b][a] as two
        # separate entries, each holding the count once. Halving (as if a
        # single symmetric counter had been double-incremented) drove every
        # single-edge pair to zero, no merge ever showed a positive gain, and
        # a 5,000-file graph came back as 5,000 singleton communities.

        while True:
            best_gain = 0.0
            best_pair: tuple[int, int] | None = None
            for a in sorted(between):
                da = deg_sum[a]
                for b, e_ab in sorted(between[a].items()):
                    if b <= a or not e_ab:
                        continue
                    gain = (e_ab / two_m) - 2.0 * (da / two_m) * (deg_sum[b] / two_m)
                    if gain > best_gain + 1e-12:
                        best_gain, best_pair = gain, (a, b)
                    elif best_pair is not None and abs(gain - best_gain) <= 1e-12:
                        if _dir_affinity(members[a], members[b]) > _dir_affinity(
                            members[best_pair[0]], members[best_pair[1]]
                        ):
                            best_pair = (a, b)

            if best_pair is None:
                break

            a, b = best_pair
            for n in members[b]:
                comm_of[n] = a
            members[a] |= members.pop(b)
            deg_sum[a] += deg_sum.pop(b)

            # fold b's edges into a
            for c, w in between.pop(b).items():
                if c == a:
                    continue
                between[a][c] = between[a].get(c, 0) + w
                between[c].pop(b, None)
                between[c][a] = between[c].get(a, 0) + w
            between[a].pop(b, None)

        return [set(m) for m in members.values()]

    def _make_cluster(
        self,
        cluster_id: int,
        files: set[FileId],
        forward: dict[FileId, set[FileId]],
        reverse: dict[FileId, set[FileId]],
    ) -> _Cluster:
        """Create a cluster object with computed statistics."""
        files_frozen = frozenset(files)

        internal_edges = 0
        external_deps: set[FileId] = set()
        external_dependents: set[FileId] = set()

        for src in files:
            for tgt in forward.get(src, []):
                if tgt in files:
                    internal_edges += 1
                else:
                    external_deps.add(tgt)

            for dep in reverse.get(src, []):
                if dep not in files:
                    external_dependents.add(dep)

        return _Cluster(
            id=cluster_id,
            files=files_frozen,
            internal_edges=internal_edges,
            external_deps=frozenset(external_deps),
            external_dependents=frozenset(external_dependents),
        )

    def _find_bridges(
        self, graph: dict[str, Any], clusters: list[_Cluster]
    ) -> dict[str, Any]:
        """Find bridge files connecting multiple clusters.

        A bridge file is one that connects files in different clusters.
        Returns dict with 'total' count and 'top' (truncated list).
        """
        forward = graph["forward"]
        reverse = graph["reverse"]

        # Build cluster membership
        cluster_map: dict[FileId, int] = {}
        for cluster in clusters:
            for fid in cluster.files:
                cluster_map[fid] = cluster.id

        bridges: list[dict[str, Any]] = []

        for fid in graph["all_files"]:
            # Find connected files (neighbors)
            neighbors: set[FileId] = set()
            neighbors.update(forward.get(fid, []))
            neighbors.update(reverse.get(fid, []))

            # Find cluster memberships
            clusters_connected = {cluster_map.get(n) for n in neighbors}
            clusters_connected.discard(None)  # Remove files in no cluster

            if len(clusters_connected) >= 2:
                # This file connects multiple clusters
                bridges.append({
                    "file": fid,
                    "connects_dirs": sorted({
                        common_prefix([n])
                        for n in neighbors
                        if common_prefix([n])
                    } or {"/".join(fid.split("/")[:-1]) or "root"}),
                    "imported_by_count": len(reverse.get(fid, [])),
                    "imports_count": len(forward.get(fid, [])),
                    "total_connections": len(neighbors),
                })

        # Sort by total connections
        bridges.sort(key=lambda b: b["total_connections"], reverse=True)

        return {
            "total": len(bridges),
            "top": bridges[:30],  # Truncate for output
        }

    def _find_orphans(
        self, ctx: AnalysisContext, graph: dict[str, Any], clusters: list[_Cluster]
    ) -> list[FileId]:
        """Find files with no import relationships.

        An orphan is a file with no resolved inbound or outbound edges
        and not part of any cluster.
        """
        forward = graph["forward"]
        reverse = graph["reverse"]

        # Files in clusters
        clustered = frozenset().union(*(c.files for c in clusters))

        # Files with any edges
        connected = set(forward.keys()) | set(reverse.keys())

        # Orphans: files with no edges and not in a cluster
        all_source_files = {sf.id for sf in ctx.source_files()}
        orphans = sorted(all_source_files - connected - clustered)

        return orphans

    def _cluster_to_dict(self, cluster: _Cluster) -> dict[str, Any]:
        """Convert cluster to JSON-serializable dict."""
        files = sorted(cluster.files)
        file_count = len(files)

        # Cohesion: internal edges normalized by cluster size
        # Formula: internal_edges / (file_count - 1) for a tree-like structure
        # Normalized to [0, 1] range
        max_edges = file_count * (file_count - 1) / 2  # Complete graph
        cohesion = (
            cluster.internal_edges / max_edges if max_edges > 0 else 0.0
        )

        # Extraction risk
        external_dep_count = len(cluster.external_deps)
        external_dependent_count = len(cluster.external_dependents)

        if external_dep_count == 0 and external_dependent_count == 0:
            extraction_risk = "low"
            reason = "No external dependencies or dependents"
        elif external_dep_count + external_dependent_count <= 2:
            extraction_risk = "low"
            reason = (
                f"{external_dep_count} external deps, "
                f"{external_dependent_count} external dependents"
            )
        elif external_dep_count + external_dependent_count <= 5:
            extraction_risk = "medium"
            reason = (
                f"{external_dep_count} external deps, "
                f"{external_dependent_count} external dependents"
            )
        else:
            extraction_risk = "high"
            reason = (
                f"{external_dep_count} external deps, "
                f"{external_dependent_count} external dependents - "
                "tightly integrated"
            )

        return {
            "id": cluster.id,
            "file_count": file_count,
            "files": files,
            "common_prefix": common_prefix(files),
            "internal_edges": cluster.internal_edges,
            "cohesion": cohesion,
            "external_dep_count": external_dep_count,
            "external_deps": sorted(cluster.external_deps),
            "external_dependent_count": external_dependent_count,
            "external_dependents": sorted(cluster.external_dependents),
            "extraction_risk": extraction_risk,
            "extraction_reason": reason,
        }


def _dir_affinity(a: set, b: set) -> int:
    """Length of the deepest directory prefix shared by two file groups.

    Only ever used to break ties between merges of equal modularity gain, so
    it nudges output toward the project's own packaging without letting
    directory layout override real structural coupling.
    """
    def prefix(group: set) -> tuple:
        parts = [tuple(f.split("/")[:-1]) for f in group]
        if not parts:
            return ()
        shared = []
        for level in zip(*parts):
            if len(set(level)) == 1:
                shared.append(level[0])
            else:
                break
        return tuple(shared)

    pa, pb = prefix(a), prefix(b)
    n = 0
    for x, y in zip(pa, pb):
        if x != y:
            break
        n += 1
    return n
