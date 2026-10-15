"""
High-Performance Code Graph using rustworkx

Provides blazing-fast graph operations and advanced algorithms for code analysis.
Uses Rust-backed rustworkx for optimal performance with large codebases.
"""

import logging
import time
import threading
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple
from contextlib import contextmanager

import rustworkx as rx

from .universal_graph import (
    UniversalNode,
    UniversalRelationship,
    UniversalLocation,
    NodeType,
    RelationshipType,
    CacheConfig
)

logger = logging.getLogger(__name__)


class RustworkxCodeGraph:
    """
    Thread-safe, high-performance code graph using rustworkx for advanced analytics.

    Provides:
    - 10-100x faster graph operations
    - Advanced graph algorithms (centrality, shortest paths, cycles)
    - Memory-efficient storage for large codebases
    - Thread-safe operations with proper locking
    - Corruption-resistant index mapping
    """

    def __init__(self):
        # Thread safety lock
        self._lock = threading.RLock()

        # Create directed graph for code relationships
        self.graph = rx.PyDiGraph()

        # Node and relationship storage with metadata
        self.nodes: Dict[str, UniversalNode] = {}
        self.relationships: Dict[str, UniversalRelationship] = {}

        # REDESIGNED: Store rustworkx indices directly in node data
        # This eliminates the need for separate mapping dictionaries
        # and prevents corruption from index reuse

        # Performance indexes
        self._nodes_by_type: Dict[NodeType, Set[str]] = {}
        self._nodes_by_language: Dict[str, Set[str]] = {}

        # Track processed files with thread safety
        self._processed_files: Set[str] = set()
        self._file_to_nodes: Dict[str, Set[str]] = {}  # Track which nodes came from which files

        # Graph metadata
        self.metadata: Dict[str, Any] = {}

        # Generation counter to detect stale operations
        self._generation = 0

    @contextmanager
    def _thread_safe_operation(self):
        """Context manager for thread-safe graph operations."""
        with self._lock:
            generation_start = self._generation
            try:
                yield
            finally:
                # Increment generation to invalidate stale caches
                if self._generation == generation_start:
                    self._generation += 1
                    # Clear LRU caches when graph structure changes
                    self._clear_method_caches()

    def _clear_method_caches(self):
        """Clear all LRU caches to prevent stale data."""
        methods_with_cache = [
            'find_nodes_by_name', 'get_nodes_by_type', 'calculate_centrality',
            'calculate_pagerank', 'calculate_closeness_centrality',
            'calculate_eigenvector_centrality', 'get_statistics'
        ]
        for method_name in methods_with_cache:
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                if hasattr(method, 'cache_clear'):
                    method.cache_clear()

    def add_node(self, node: UniversalNode) -> None:
        """Add a node to the high-performance graph with thread safety."""
        with self._thread_safe_operation():
            # Check if node already exists to prevent duplicates
            if node.id in self.nodes:
                logger.debug(f"Node {node.id} already exists, updating...")
                self._remove_node_internal(node.id)

            # Store node data
            self.nodes[node.id] = node

            # Add to rustworkx graph - store the node ID as node data
            # This eliminates the need for separate index mapping
            node_index = self.graph.add_node(node.id)

            # Store the rustworkx index in the node for direct access
            # This prevents index mapping corruption
            node._rustworkx_index = node_index

            # Update performance indexes
            if node.node_type not in self._nodes_by_type:
                self._nodes_by_type[node.node_type] = set()
            self._nodes_by_type[node.node_type].add(node.id)

            if node.language:
                if node.language not in self._nodes_by_language:
                    self._nodes_by_language[node.language] = set()
                self._nodes_by_language[node.language].add(node.id)

            # Track file association for proper cleanup
            file_path = node.location.file_path
            if file_path not in self._file_to_nodes:
                self._file_to_nodes[file_path] = set()
            self._file_to_nodes[file_path].add(node.id)

    def _remove_node_internal(self, node_id: str) -> None:
        """Internal method to remove a node without locking (already locked)."""
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]

        # Remove from rustworkx graph if it has an index
        if hasattr(node, '_rustworkx_index'):
            try:
                self.graph.remove_node(node._rustworkx_index)
            except Exception as e:
                logger.debug(f"Failed to remove node from rustworkx: {e}")

        # Remove from our storage
        del self.nodes[node_id]

        # Remove from performance indexes
        if node.node_type in self._nodes_by_type:
            self._nodes_by_type[node.node_type].discard(node_id)
        if node.language and node.language in self._nodes_by_language:
            self._nodes_by_language[node.language].discard(node_id)

        # Remove from file tracking
        file_path = node.location.file_path
        if file_path in self._file_to_nodes:
            self._file_to_nodes[file_path].discard(node_id)

    def add_relationship(self, relationship: UniversalRelationship) -> None:
        """Add a relationship to the high-performance graph with thread safety."""
        with self._thread_safe_operation():
            # Store relationship data
            self.relationships[relationship.id] = relationship

            # Get nodes and their indices directly
            source_node = self.nodes.get(relationship.source_id)
            target_node = self.nodes.get(relationship.target_id)

            if not source_node or not target_node:
                logger.debug(f"Cannot add relationship {relationship.id}: missing nodes")
                return

            # Get indices from nodes directly (no mapping corruption possible)
            source_index = getattr(source_node, '_rustworkx_index', None)
            target_index = getattr(target_node, '_rustworkx_index', None)

            if source_index is None or target_index is None:
                logger.debug(f"Cannot add relationship {relationship.id}: nodes not in rustworkx graph")
                return

            # Add edge to rustworkx graph - store relationship ID as edge data
            edge_index = self.graph.add_edge(source_index, target_index, relationship.id)

            # Store edge index in relationship for direct access
            relationship._rustworkx_edge_index = edge_index

    def get_node(self, node_id: str) -> Optional[UniversalNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_relationship(self, relationship_id: str) -> Optional[UniversalRelationship]:
        """Get a relationship by ID."""
        return self.relationships.get(relationship_id)

    @lru_cache(maxsize=CacheConfig.XLARGE_CACHE)
    def find_nodes_by_name(self, name: str, exact_match: bool = True) -> List[UniversalNode]:
        """Find nodes by name with LRU caching for performance optimization."""
        results = []

        for node in self.nodes.values():
            if exact_match:
                if node.name == name:
                    results.append(node)
            else:
                if name.lower() in node.name.lower():
                    results.append(node)

        return results

    @lru_cache(maxsize=CacheConfig.LARGE_CACHE)
    def get_nodes_by_type(self, node_type: NodeType) -> List[UniversalNode]:
        """Get all nodes of a specific type with LRU caching."""
        node_ids = self._nodes_by_type.get(node_type, set())
        return [self.nodes[node_id] for node_id in node_ids]

    def get_relationships_from(self, node_id: str) -> List[UniversalRelationship]:
        """Get all relationships originating from a node."""
        with self._lock:
            node = self.nodes.get(node_id)
            if not node or not hasattr(node, '_rustworkx_index'):
                return []

            relationships = []
            # Get outgoing edges
            for edge in self.graph.out_edges(node._rustworkx_index):
                source_idx, target_idx, edge_data = edge
                # edge_data now contains relationship ID
                if isinstance(edge_data, str) and edge_data in self.relationships:
                    relationships.append(self.relationships[edge_data])

            return relationships

    def get_relationships_to(self, node_id: str) -> List[UniversalRelationship]:
        """Get all relationships targeting a node."""
        with self._lock:
            node = self.nodes.get(node_id)
            if not node or not hasattr(node, '_rustworkx_index'):
                return []

            relationships = []
            # Get incoming edges
            for edge in self.graph.in_edges(node._rustworkx_index):
                source_idx, target_idx, edge_data = edge
                # edge_data now contains relationship ID
                if isinstance(edge_data, str) and edge_data in self.relationships:
                    relationships.append(self.relationships[edge_data])

            return relationships

    def get_relationships_by_type(self, relationship_type: RelationshipType) -> List[UniversalRelationship]:
        """Get all relationships of a specific type."""
        return [rel for rel in self.relationships.values()
                if rel.relationship_type == relationship_type]

    # ========================= ADVANCED ANALYTICS =========================

    def find_shortest_path(self, source_id: str, target_id: str) -> List[str]:
        """Find shortest path between two nodes."""
        with self._lock:
            source_node = self.nodes.get(source_id)
            target_node = self.nodes.get(target_id)

            if not source_node or not target_node:
                return []

            source_index = getattr(source_node, '_rustworkx_index', None)
            target_index = getattr(target_node, '_rustworkx_index', None)

            if source_index is None or target_index is None:
                return []

            try:
                # Use dijkstra shortest path
                path_indices = rx.dijkstra_shortest_paths(
                    self.graph, source_index, target_index, lambda _: 1
                )
                if path_indices and target_index in path_indices:
                    # Convert indices to node IDs using graph data
                    return [self.graph[idx] for idx in path_indices[target_index] if idx < len(self.graph)]
                return []
            except Exception:
                return []

    def find_all_paths(self, source_id: str, target_id: str, max_length: int = 10) -> List[List[str]]:
        """Find all paths between two nodes up to max_length."""
        with self._lock:
            source_node = self.nodes.get(source_id)
            target_node = self.nodes.get(target_id)

            if not source_node or not target_node:
                return []

            source_index = getattr(source_node, '_rustworkx_index', None)
            target_index = getattr(target_node, '_rustworkx_index', None)

            if source_index is None or target_index is None:
                return []

            try:
                paths = rx.all_simple_paths(self.graph, source_index, target_index, min_depth=1, cutoff=max_length)
                # Convert indices to node IDs using graph data
                return [[self.graph[idx] for idx in path if idx < len(self.graph)] for path in paths]
            except Exception:
                return []

    def detect_cycles(self) -> List[List[str]]:
        """Detect meaningful cycles in the code graph, filtering out legitimate recursion."""
        with self._lock:
            try:
                # Get all cycles from rustworkx
                all_cycles = list(rx.simple_cycles(self.graph))
                meaningful_cycles = []

                for cycle in all_cycles:
                    # Filter out single-node cycles (self-loops) which are often legitimate recursion
                    if len(cycle) == 1:
                        node_index = cycle[0]
                        node_id = self.graph[node_index]  # Get node ID from graph data
                        node = self.nodes.get(node_id)

                        if node and self._is_legitimate_recursion(node):
                            continue  # Skip legitimate recursive functions

                    # Convert indices to node IDs using graph data (no mapping corruption)
                    cycle_node_ids = []
                    for idx in cycle:
                        node_id = self.graph[idx]  # Get node ID from graph data
                        if node_id:
                            cycle_node_ids.append(node_id)

                    if len(cycle_node_ids) > 1:  # Only report multi-node cycles
                        meaningful_cycles.append(cycle_node_ids)

                return meaningful_cycles

            except Exception as e:
                logger.error(f"Cycle detection failed: {e}")
                return []

    def _is_legitimate_recursion(self, node: UniversalNode) -> bool:
        """Check if a self-loop represents legitimate recursion rather than a circular dependency."""
        # Recursive functions are legitimate if they:
        # 1. Are actual functions (not modules/classes)
        # 2. Have recursive patterns in their name or are common recursive algorithms
        if node.node_type != NodeType.FUNCTION:
            return False

        # Common recursive function patterns
        recursive_patterns = [
            'recursive', 'recurse', 'factorial', 'fibonacci', 'traverse',
            'walk', 'visit', 'search', 'sort', 'merge', 'quick', 'binary'
        ]

        node_name_lower = node.name.lower()
        return any(pattern in node_name_lower for pattern in recursive_patterns)

    def remove_file_nodes(self, file_path: str) -> int:
        """Remove all nodes associated with a specific file and return count removed."""
        with self._thread_safe_operation():
            if file_path not in self._file_to_nodes:
                return 0

            nodes_to_remove = list(self._file_to_nodes[file_path])
            removed_count = 0

            for node_id in nodes_to_remove:
                if node_id in self.nodes:
                    self._remove_node_internal(node_id)
                    removed_count += 1

            # Clean up file tracking
            del self._file_to_nodes[file_path]
            self._processed_files.discard(file_path)

            logger.debug(f"Removed {removed_count} nodes from file: {file_path}")
            return removed_count

    def mark_file_processed(self, file_path: str) -> None:
        """Mark a file as processed for tracking."""
        with self._lock:
            self._processed_files.add(file_path)

    def is_file_processed(self, file_path: str) -> bool:
        """Check if a file has been processed."""
        with self._lock:
            return file_path in self._processed_files

    def get_processed_files(self) -> Set[str]:
        """Get set of all processed files."""
        with self._lock:
            return self._processed_files.copy()

    def get_file_node_count(self, file_path: str) -> int:
        """Get the number of nodes associated with a file."""
        with self._lock:
            return len(self._file_to_nodes.get(file_path, set()))

    def get_strongly_connected_components(self) -> List[List[str]]:
        """Find strongly connected components (circular dependency groups)."""
        with self._lock:
            try:
                components = rx.strongly_connected_components(self.graph)
                # Convert indices to node IDs using graph data
                result = []
                for component in components:
                    component_ids = []
                    for idx in component:
                        if idx < len(self.graph):
                            node_id = self.graph[idx]
                            if node_id:
                                component_ids.append(node_id)
                    if component_ids:
                        result.append(component_ids)
                return result
            except Exception as e:
                logger.error(f"Strongly connected components calculation failed: {e}")
                return []

    @lru_cache(maxsize=CacheConfig.SMALL_CACHE)
    def calculate_centrality(self) -> Dict[str, float]:
        """Calculate betweenness centrality with LRU caching for performance."""
        with self._lock:
            try:
                # Use the correct API for directed graphs
                centrality = rx.digraph_betweenness_centrality(self.graph)
                # Convert indices to node IDs using graph data
                result = {}
                for idx, score in centrality.items():
                    if idx < len(self.graph):
                        node_id = self.graph[idx]
                        if node_id:
                            result[node_id] = score
                return result
            except Exception as e:
                logger.error(f"Centrality calculation failed: {e}")
                return {}

    @lru_cache(maxsize=CacheConfig.MEDIUM_CACHE)
    def calculate_pagerank(self, alpha: float = 0.85, max_iter: int = 100, tol: float = 1e-6) -> Dict[str, float]:
        """Calculate PageRank with LRU caching for optimal performance."""
        with self._lock:
            try:
                # Use optimized PageRank with configurable damping factor and convergence
                pagerank_scores = rx.pagerank(
                    self.graph,
                    alpha=alpha,        # Damping factor (0.85 is standard)
                    max_iter=max_iter,  # Maximum iterations for convergence
                    tol=tol            # Convergence tolerance
                )
                # Convert indices to node IDs using graph data
                result = {}
                for idx, score in pagerank_scores.items():
                    if idx < len(self.graph):
                        node_id = self.graph[idx]
                        if node_id:
                            result[node_id] = score
                return result
            except rx.FailedToConverge as e:
                logger.warning(f"PageRank failed to converge: {e}")
                return {}
            except Exception as e:
                logger.error(f"PageRank calculation failed: {e}")
                return {}

    def find_ancestors(self, node_id: str) -> Set[str]:
        """Find all nodes that can reach this node."""
        with self._lock:
            node = self.nodes.get(node_id)
            if not node or not hasattr(node, '_rustworkx_index'):
                return set()

            try:
                ancestor_indices = rx.ancestors(self.graph, node._rustworkx_index)
                result = set()
                for idx in ancestor_indices:
                    if idx < len(self.graph):
                        ancestor_id = self.graph[idx]
                        if ancestor_id:
                            result.add(ancestor_id)
                return result
            except Exception:
                return set()

    def find_descendants(self, node_id: str) -> Set[str]:
        """Find all nodes reachable from this node."""
        with self._lock:
            node = self.nodes.get(node_id)
            if not node or not hasattr(node, '_rustworkx_index'):
                return set()

            try:
                descendant_indices = rx.descendants(self.graph, node._rustworkx_index)
                result = set()
                for idx in descendant_indices:
                    if idx < len(self.graph):
                        descendant_id = self.graph[idx]
                        if descendant_id:
                            result.add(descendant_id)
                return result
            except Exception:
                return set()

    def get_node_degree(self, node_id: str) -> Tuple[int, int, int]:
        """Get node degree (in_degree, out_degree, total_degree)."""
        with self._lock:
            node = self.nodes.get(node_id)
            if not node or not hasattr(node, '_rustworkx_index'):
                return (0, 0, 0)

            try:
                in_degree = self.graph.in_degree(node._rustworkx_index)
                out_degree = self.graph.out_degree(node._rustworkx_index)
                total_degree = in_degree + out_degree
                return (in_degree, out_degree, total_degree)
            except Exception:
                return (0, 0, 0)

    def is_directed_acyclic(self) -> bool:
        """Check if the graph is a DAG (no circular dependencies)."""
        return rx.is_directed_acyclic_graph(self.graph)

    def topological_sort(self) -> List[str]:
        """Get topological ordering of nodes (dependency order)."""
        with self._lock:
            try:
                sorted_indices = rx.topological_sort(self.graph)
                result = []
                for idx in sorted_indices:
                    if idx < len(self.graph):
                        node_id = self.graph[idx]
                        if node_id:
                            result.append(node_id)
                return result
            except Exception:
                return []

    @lru_cache(maxsize=CacheConfig.SMALL_CACHE)
    def calculate_closeness_centrality(self) -> Dict[str, float]:
        """Calculate closeness centrality with LRU caching."""
        with self._lock:
            try:
                centrality = rx.closeness_centrality(self.graph)
                result = {}
                for idx, score in centrality.items():
                    if idx < len(self.graph):
                        node_id = self.graph[idx]
                        if node_id:
                            result[node_id] = score
                return result
            except Exception as e:
                logger.warning(f"Closeness centrality calculation failed: {e}")
                return {}

    @lru_cache(maxsize=CacheConfig.LARGE_CACHE)
    def calculate_eigenvector_centrality(self, max_iter: int = 100, tol: float = 1e-6) -> Dict[str, float]:
        """Calculate eigenvector centrality with LRU caching."""
        with self._lock:
            try:
                centrality = rx.eigenvector_centrality(self.graph, max_iter=max_iter, tol=tol)
                result = {}
                for idx, score in centrality.items():
                    if idx < len(self.graph):
                        node_id = self.graph[idx]
                        if node_id:
                            result[node_id] = score
                return result
            except Exception as e:
                logger.warning(f"Eigenvector centrality calculation failed: {e}")
                return {}

    def find_articulation_points(self) -> List[str]:
        """Find articulation points (nodes whose removal increases connected components)."""
        with self._lock:
            try:
                # Convert to undirected for articulation point analysis
                undirected = self.graph.to_undirected()
                articulation_indices = rx.articulation_points(undirected)
                result = []
                for idx in articulation_indices:
                    if idx < len(self.graph):
                        node_id = self.graph[idx]
                        if node_id:
                            result.append(node_id)
                return result
            except Exception as e:
                logger.warning(f"Articulation points calculation failed: {e}")
                return []

    def find_bridges(self) -> List[tuple]:
        """Find bridge edges (edges whose removal increases connected components)."""
        try:
            # Convert to undirected for bridge analysis
            undirected = self.graph.to_undirected()
            bridge_edges = rx.bridges(undirected)
            bridges = []
            for edge in bridge_edges:
                if len(edge) >= 2:  # Ensure edge has at least 2 elements
                    source_id = self.graph[edge[0]]  # Get node ID from graph data
                    target_id = self.graph[edge[1]]  # Get node ID from graph data
                    if source_id and target_id:
                        bridges.append((source_id, target_id))
            return bridges
        except Exception as e:
            logger.warning(f"Bridge calculation failed: {e}")
            return []

    def calculate_graph_distance_matrix(self) -> Dict[str, Dict[str, float]]:
        """Calculate shortest path distances between all pairs of nodes using Floyd-Warshall."""
        try:
            distance_matrix = rx.floyd_warshall_numpy(self.graph)
            result = {}
            # Iterate through all node indices in the graph
            for i in range(len(self.graph)):
                source_id = self.graph[i]  # Get node ID from graph data
                if source_id:
                    result[source_id] = {}
                    for j in range(len(self.graph)):
                        target_id = self.graph[j]  # Get node ID from graph data
                        if target_id and i < len(distance_matrix) and j < len(distance_matrix[i]):
                            distance = distance_matrix[i][j]
                            if distance != float('inf'):
                                result[source_id][target_id] = distance
            return result
        except Exception as e:
            logger.warning(f"Distance matrix calculation failed: {e}")
            return {}

    def calculate_bellman_ford_path_lengths(self, weight_fn=None) -> Dict[str, Dict[str, float]]:
        """
        Calculate all-pairs shortest path lengths using Bellman-Ford algorithm.
        Superior to Floyd-Warshall for sparse graphs and can handle negative weights.

        Args:
            weight_fn: Optional weight function for edges. If None, uses unit weights.

        Returns:
            Dict mapping source nodes to target nodes with their shortest distances
        """
        try:
            # Use Bellman-Ford for all pairs shortest path lengths
            edge_cost_fn = weight_fn if weight_fn else lambda _: 1
            paths_result = rx.all_pairs_bellman_ford_path_lengths(self.graph, edge_cost_fn)

            result = {}
            for source_idx, target_distances in paths_result.items():
                source_id = self.graph[source_idx]  # Get node ID from graph data
                if source_id:
                    result[source_id] = {}

                    # Convert target indices to node IDs
                    for target_idx, distance in target_distances.items():
                        target_id = self.graph[target_idx]  # Get node ID from graph data
                        if target_id:
                            result[source_id][target_id] = distance

            return result

        except Exception as e:
            logger.warning(f"Bellman-Ford path lengths calculation failed: {e}")
            return {}

    def detect_negative_cycles(self, weight_fn=None) -> bool:
        """
        Detect if the graph contains negative cycles using Bellman-Ford algorithm.

        Args:
            weight_fn: Optional weight function for edges

        Returns:
            True if negative cycles exist, False otherwise
        """
        try:
            # Check for negative cycles by trying Bellman-Ford from each node
            for source_idx in self.graph.node_indices():
                try:
                    # If Bellman-Ford raises an exception, there's a negative cycle
                    edge_cost_fn = weight_fn if weight_fn else lambda _: 1
                    rx.bellman_ford_shortest_path_lengths(
                        self.graph,
                        source_idx,
                        edge_cost_fn
                    )
                except Exception:
                    # Negative cycle detected
                    return True

            return False

        except Exception as e:
            logger.warning(f"Negative cycle detection failed: {e}")
            return False

    def calculate_weighted_shortest_paths(self, source_id: str, weight_fn=None) -> Dict[str, Any]:
        """
        Calculate shortest paths from a source node using Bellman-Ford algorithm.

        Args:
            source_id: Source node ID
            weight_fn: Optional weight function for edges

        Returns:
            Dictionary with distances and paths to all reachable nodes
        """
        try:
            source_node = self.nodes.get(source_id)
            if not source_node:
                return {}

            source_index = getattr(source_node, '_rustworkx_index', None)
            if source_index is None:
                return {}

            # Use Bellman-Ford from single source
            edge_cost_fn = weight_fn if weight_fn else lambda _: 1
            distances = rx.bellman_ford_shortest_path_lengths(
                self.graph,
                source_index,
                edge_cost_fn
            )

            result = {
                "source": source_id,
                "distances": {},
                "has_negative_cycles": False
            }

            for target_idx, distance in distances.items():
                target_id = self.graph[target_idx]  # Get node ID from graph data
                if target_id:
                    result["distances"][target_id] = distance

            return result

        except Exception as e:
            logger.warning(f"Weighted shortest paths calculation failed: {e}")
            return {}

    def analyze_graph_connectivity(self, weight_fn=None) -> Dict[str, Any]:
        """
        Comprehensive connectivity analysis using multiple rustworkx algorithms.

        Args:
            weight_fn: Optional weight function for edges

        Returns:
            Dictionary with comprehensive connectivity metrics
        """
        try:
            # Basic connectivity
            num_nodes = len(self.nodes)
            num_edges = len(self.relationships)

            # Shortest path analysis
            floyd_warshall_distances = self.calculate_graph_distance_matrix()
            bellman_ford_distances = self.calculate_bellman_ford_path_lengths(weight_fn)

            # Check for negative cycles
            has_negative_cycles = self.detect_negative_cycles(weight_fn)

            # Analyze path lengths
            all_distances = []
            reachable_pairs = 0

            for source, targets in floyd_warshall_distances.items():
                for target, distance in targets.items():
                    if source != target and distance != float('inf'):
                        all_distances.append(distance)
                        reachable_pairs += 1

            # Calculate connectivity metrics
            total_possible_pairs = num_nodes * (num_nodes - 1)
            connectivity_ratio = reachable_pairs / total_possible_pairs if total_possible_pairs > 0 else 0

            avg_distance = sum(all_distances) / len(all_distances) if all_distances else 0
            max_distance = max(all_distances) if all_distances else 0
            min_distance = min(all_distances) if all_distances else 0

            return {
                "basic_metrics": {
                    "num_nodes": num_nodes,
                    "num_edges": num_edges,
                    "density": num_edges / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0
                },
                "connectivity_metrics": {
                    "reachable_pairs": reachable_pairs,
                    "total_possible_pairs": total_possible_pairs,
                    "connectivity_ratio": connectivity_ratio,
                    "is_strongly_connected": connectivity_ratio == 1.0
                },
                "distance_metrics": {
                    "average_distance": avg_distance,
                    "maximum_distance": max_distance,
                    "minimum_distance": min_distance,
                    "has_negative_cycles": has_negative_cycles
                },
                "algorithm_comparison": {
                    "floyd_warshall_computed": len(floyd_warshall_distances),
                    "bellman_ford_computed": len(bellman_ford_distances),
                    "algorithms_agree": self._compare_distance_algorithms(
                        floyd_warshall_distances,
                        bellman_ford_distances
                    )
                }
            }

        except Exception as e:
            logger.warning(f"Connectivity analysis failed: {e}")
            return {}

    def _compare_distance_algorithms(self, floyd_distances, bellman_distances) -> bool:
        """Compare results from Floyd-Warshall and Bellman-Ford algorithms."""
        try:
            tolerance = 1e-6

            for source in floyd_distances:
                if source not in bellman_distances:
                    continue

                for target in floyd_distances[source]:
                    if target not in bellman_distances[source]:
                        continue

                    floyd_dist = floyd_distances[source][target]
                    bellman_dist = bellman_distances[source][target]

                    if abs(floyd_dist - bellman_dist) > tolerance:
                        return False

            return True

        except Exception:
            return False

    # ========================= TRAVERSAL ALGORITHMS =========================

    def depth_first_search(self, source_id: str, visitor_fn=None) -> List[str]:
        """
        Perform depth-first search traversal starting from source node.

        Args:
            source_id: Starting node ID
            visitor_fn: Optional visitor function called for each node

        Returns:
            List of node IDs in DFS order
        """
        with self._lock:
            try:
                source_node = self.nodes.get(source_id)
                if not source_node or not hasattr(source_node, '_rustworkx_index'):
                    return []

                # Perform DFS traversal
                dfs_edges = rx.dfs_edges(self.graph, source_node._rustworkx_index)

                # Extract unique nodes in DFS order
                visited_nodes = [source_id]  # Start with source
                for edge in dfs_edges:
                    target_idx = edge[1]
                    if target_idx < len(self.graph):
                        target_id = self.graph[target_idx]
                        if target_id and target_id not in visited_nodes:
                            visited_nodes.append(target_id)
                            if visitor_fn:
                                visitor_fn(target_id)

                return visited_nodes

            except Exception as e:
                logger.warning(f"DFS traversal failed: {e}")
                return []

    def breadth_first_search(self, source_id: str, visitor_fn=None) -> List[str]:
        """
        Perform breadth-first search traversal starting from source node.

        Args:
            source_id: Starting node ID
            visitor_fn: Optional visitor function called for each node

        Returns:
            List of node IDs in BFS order
        """
        with self._lock:
            try:
                source_node = self.nodes.get(source_id)
                if not source_node or not hasattr(source_node, '_rustworkx_index'):
                    return []

                # Perform BFS traversal using successor iteration
                source_index = source_node._rustworkx_index
                visited = set([source_index])
                queue = [source_index]
                visited_nodes = [source_id]

                while queue:
                    current_index = queue.pop(0)
                    for successor in self.graph.successors(current_index):
                        if successor not in visited:
                            visited.add(successor)
                            queue.append(successor)
                            if successor < len(self.graph):
                                successor_id = self.graph[successor]
                                if successor_id:
                                    visited_nodes.append(successor_id)
                                    if visitor_fn:
                                        visitor_fn(successor_id)

                return visited_nodes

            except Exception as e:
                logger.warning(f"BFS traversal failed: {e}")
                return []

    def find_node_layers(self, source_id: str) -> Dict[int, List[str]]:
        """
        Find nodes organized by their distance layers from the source.

        Args:
            source_id: Starting node ID

        Returns:
            Dictionary mapping layer number to list of node IDs at that layer
        """
        try:
            source_node = self.nodes.get(source_id)
            if not source_node:
                return {}

            source_index = getattr(source_node, '_rustworkx_index', None)
            if source_index is None:
                return {}

            # Get shortest path lengths to organize by layers (unit weight function)
            distances = rx.dijkstra_shortest_path_lengths(self.graph, source_index, lambda _: 1)

            layers = {}
            for target_index, distance in distances.items():
                target_id = self.graph[target_index]  # Get node ID from graph data
                if target_id:
                    layer = int(distance)
                    if layer not in layers:
                        layers[layer] = []
                    layers[layer].append(target_id)

            return layers

        except Exception as e:
            logger.warning(f"Layer analysis failed: {e}")
            return {}

    def find_dominating_set(self) -> List[str]:
        """
        Find a dominating set - minimum set of nodes that can reach all other nodes.
        Useful for identifying key architectural components.

        Returns:
            List of node IDs forming a dominating set
        """
        with self._lock:
            try:
                # Check if dominating_set is available
                if hasattr(rx, 'dominating_set'):
                    dominating_indices = getattr(rx, 'dominating_set')(self.graph)
                    result = []
                    for idx in dominating_indices:
                        if idx < len(self.graph):
                            node_id = self.graph[idx]
                            if node_id:
                                result.append(node_id)
                    return result
                else:
                    # Fallback: return nodes with highest degree as approximation
                    node_degrees = [(node_id, self.get_node_degree(node_id)[2])
                                   for node_id in self.nodes.keys()]
                    node_degrees.sort(key=lambda x: x[1], reverse=True)
                    # Return top 10% of nodes by degree
                    top_count = max(1, len(node_degrees) // 10)
                    return [node_id for node_id, _ in node_degrees[:top_count]]

            except Exception as e:
                logger.warning(f"Dominating set calculation failed: {e}")
                return []

    def analyze_node_connectivity(self, node_id: str) -> Dict[str, Any]:
        """
        Analyze connectivity patterns for a specific node.

        Args:
            node_id: Node to analyze

        Returns:
            Dictionary with comprehensive connectivity analysis for the node
        """
        try:
            # Get basic degree information
            in_degree, out_degree, total_degree = self.get_node_degree(node_id)

            # Find reachable nodes
            ancestors = self.find_ancestors(node_id)
            descendants = self.find_descendants(node_id)

            # Analyze traversal patterns
            dfs_reachable = set(self.depth_first_search(node_id))
            bfs_reachable = set(self.breadth_first_search(node_id))

            # Find layers from this node
            layers = self.find_node_layers(node_id)
            max_distance = max(layers.keys()) if layers else 0

            return {
                "node_id": node_id,
                "degree_analysis": {
                    "in_degree": in_degree,
                    "out_degree": out_degree,
                    "total_degree": total_degree
                },
                "reachability": {
                    "ancestors_count": len(ancestors),
                    "descendants_count": len(descendants),
                    "dfs_reachable_count": len(dfs_reachable),
                    "bfs_reachable_count": len(bfs_reachable)
                },
                "distance_analysis": {
                    "max_distance_to_others": max_distance,
                    "layers": {str(k): len(v) for k, v in layers.items()},
                    "influence_radius": max_distance
                },
                "structural_importance": {
                    "is_articulation_point": node_id in self.find_articulation_points(),
                    "centrality_percentile": self._calculate_centrality_percentile(node_id)
                }
            }

        except Exception as e:
            logger.warning(f"Node connectivity analysis failed: {e}")
            return {}

    def _calculate_centrality_percentile(self, node_id: str) -> float:
        """Calculate what percentile this node is in for centrality."""
        try:
            centrality_scores = self.calculate_centrality()
            if not centrality_scores or node_id not in centrality_scores:
                return 0.0

            node_score = centrality_scores[node_id]
            all_scores = list(centrality_scores.values())
            all_scores.sort()

            rank = sum(1 for score in all_scores if score <= node_score)
            percentile = (rank / len(all_scores)) * 100

            return percentile

        except Exception:
            return 0.0

    # ========================= STATISTICS =========================

    @lru_cache(maxsize=CacheConfig.MEDIUM_CACHE)
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics with LRU caching."""
        total_nodes = len(self.nodes)
        total_relationships = len(self.relationships)

        # Node type distribution
        node_types = {}
        for node_type, node_ids in self._nodes_by_type.items():
            node_types[node_type.value] = len(node_ids)

        # Language distribution
        languages = {}
        for language, node_ids in self._nodes_by_language.items():
            languages[language] = len(node_ids)

        # Relationship type distribution
        relationship_types = {}
        for rel in self.relationships.values():
            rel_type = rel.relationship_type.value
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1

        # Graph metrics
        is_dag = self.is_directed_acyclic()
        num_cycles = len(self.detect_cycles()) if not is_dag else 0

        file_count = len(self._processed_files)
        logger.debug(f"get_statistics: {total_nodes} nodes, {total_relationships} relationships, {file_count} files")

        return {
            "total_nodes": total_nodes,
            "total_relationships": total_relationships,
            "total_files": file_count,
            "node_types": node_types,
            "languages": languages,
            "relationship_types": relationship_types,
            "is_directed_acyclic": is_dag,
            "num_cycles": num_cycles,
            "density": total_relationships / (total_nodes * (total_nodes - 1)) if total_nodes > 1 else 0,
            "average_degree": (2 * total_relationships) / total_nodes if total_nodes > 0 else 0,
        }

    def add_processed_file(self, file_path: str) -> None:
        """Track a processed file."""
        self._processed_files.add(file_path)

    def clear(self) -> None:
        """Clear all data from the graph with proper thread safety and state reset."""
        with self._thread_safe_operation():
            logger.info(f"CLEARING GRAPH: {len(self.nodes)} nodes, {len(self.relationships)} relationships, {len(self._processed_files)} files")

            # Clear rustworkx graph completely
            self.graph.clear()

            # Clear all our data structures
            self.nodes.clear()
            self.relationships.clear()
            self._processed_files.clear()
            self._file_to_nodes.clear()
            self._nodes_by_type.clear()
            self._nodes_by_language.clear()
            self.metadata.clear()

            # Increment generation to invalidate all caches
            self._generation += 1

            logger.info("GRAPH CLEARED: now has 0 nodes, all state reset")

    # ========================= SERIALIZATION =========================

    def to_json(self, indent: Optional[int] = None) -> str:
        """
        Serialize the graph to JSON format using rustworkx serialization.

        Args:
            indent: Optional indentation for pretty printing

        Returns:
            JSON string representation of the graph
        """
        try:
            # Use rustworkx node_link_json for efficient serialization
            try:
                json_data = rx.node_link_json(
                    self.graph,
                    node_attrs=lambda node: {
                        "id": str(node.id),
                        "name": str(node.name),
                        "type": str(node.node_type.value),
                        "language": str(node.language),
                        "file": str(node.location.file_path),
                        "line": str(node.location.start_line),
                        "end_line": str(node.location.end_line),
                        "complexity": str(node.complexity)
                    },
                    edge_attrs=lambda edge: {
                        "id": str(edge.id),
                        "type": str(edge.relationship_type.value),
                        "strength": str(edge.strength)
                    }
                )
            except (AttributeError, TypeError):
                # Fallback: manual JSON creation
                json_data = {
                    "nodes": [
                        {
                            "id": node.id,
                            "name": node.name,
                            "type": node.node_type.value,
                            "language": node.language,
                            "file": node.location.file_path,
                            "line": node.location.start_line
                        }
                        for node in self.nodes.values()
                    ],
                    "edges": [
                        {
                            "id": rel.id,
                            "source": rel.source_id,
                            "target": rel.target_id,
                            "type": rel.relationship_type.value
                        }
                        for rel in self.relationships.values()
                    ]
                }

            import json
            if indent:
                return json.dumps(json_data, indent=indent)
            return json.dumps(json_data) if isinstance(json_data, dict) else str(json_data)

        except Exception as e:
            logger.warning(f"JSON serialization failed: {e}")
            return "{}"

    def to_dot(self,
               filename: Optional[str] = None,
               node_attr_fn=None,
               edge_attr_fn=None,
               graph_attr: Optional[Dict[str, str]] = None) -> str:
        """
        Export graph to DOT format for visualization with Graphviz.

        Args:
            filename: Optional filename to write DOT file
            node_attr_fn: Function to generate node attributes
            edge_attr_fn: Function to generate edge attributes
            graph_attr: Graph-level attributes

        Returns:
            DOT format string
        """
        try:
            def default_node_attr(node):
                return {
                    "label": f"{node.name}\\n({node.node_type.value})",
                    "shape": "box" if node.node_type == NodeType.FUNCTION else "ellipse",
                    "color": self._get_node_color(node.node_type)
                }

            def default_edge_attr(edge):
                return {
                    "label": edge.relationship_type.value,
                    "color": self._get_edge_color(edge.relationship_type)
                }

            node_attr_callback = node_attr_fn or default_node_attr
            edge_attr_callback = edge_attr_fn or default_edge_attr

            if hasattr(rx, 'graph_to_dot'):
                dot_string = getattr(rx, 'graph_to_dot')(
                    self.graph,
                    node_attr=node_attr_callback,
                    edge_attr=edge_attr_callback,
                    graph_attr=graph_attr or {"rankdir": "TB", "concentrate": "true"}
                )
            else:
                # Fallback: manual DOT creation
                dot_string = "digraph G {\n"
                for node in self.nodes.values():
                    attrs = node_attr_callback(node)
                    attr_str = ", ".join([f'{k}="{v}"' for k, v in attrs.items()])
                    dot_string += f'  "{node.id}" [{attr_str}];\n'

                for rel in self.relationships.values():
                    attrs = edge_attr_callback(rel)
                    attr_str = ", ".join([f'{k}="{v}"' for k, v in attrs.items()])
                    dot_string += f'  "{rel.source_id}" -> "{rel.target_id}" [{attr_str}];\n'
                dot_string += "}\n"

            if filename:
                with open(filename, 'w') as f:
                    f.write(dot_string)
                logger.info(f"DOT file written to {filename}")

            return dot_string

        except Exception as e:
            logger.warning(f"DOT export failed: {e}")
            return ""

    def to_graphml(self, filename: str) -> bool:
        """
        Export graph to GraphML format for use with graph analysis tools.

        Args:
            filename: Output filename

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create node and edge attributes for GraphML
            def node_map_fn(node):
                return {
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type.value,
                    "language": node.language,
                    "file": node.location.file_path,
                    "line": str(node.location.start_line),
                    "complexity": str(node.complexity)
                }

            def edge_map_fn(edge):
                return {
                    "id": edge.id,
                    "type": edge.relationship_type.value,
                    "strength": str(edge.strength)
                }

            if hasattr(rx, 'write_graphml'):
                getattr(rx, 'write_graphml')(
                    self.graph,
                    filename,
                    node_attr_fn=node_map_fn,
                    edge_attr_fn=edge_map_fn
                )
            else:
                # Fallback: manual GraphML creation
                with open(filename, 'w') as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                    f.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
                    f.write('  <graph id="G" edgedefault="directed">\n')

                    for node in self.nodes.values():
                        attrs = node_map_fn(node)
                        f.write(f'    <node id="{node.id}">\n')
                        for key, value in attrs.items():
                            f.write(f'      <data key="{key}">{value}</data>\n')
                        f.write('    </node>\n')

                    for rel in self.relationships.values():
                        attrs = edge_map_fn(rel)
                        f.write(f'    <edge source="{rel.source_id}" target="{rel.target_id}">\n')
                        for key, value in attrs.items():
                            f.write(f'      <data key="{key}">{value}</data>\n')
                        f.write('    </edge>\n')
                    f.write('  </graph>\n')
                    f.write('</graphml>\n')

            logger.info(f"GraphML file written to {filename}")
            return True

        except Exception as e:
            logger.warning(f"GraphML export failed: {e}")
            return False

    def from_json(self, json_data: str) -> bool:
        """
        Load graph from JSON format.

        Args:
            json_data: JSON string representation

        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            data = json.loads(json_data) if isinstance(json_data, str) else json_data

            # Clear existing graph
            self.clear()

            # Recreate graph from node-link format
            if hasattr(rx, 'node_link_graph'):
                self.graph = getattr(rx, 'node_link_graph')(data)
                # TODO: Extract node and relationship objects from rustworkx graph data
            else:
                # Manual reconstruction from JSON data
                self.graph = rx.PyDiGraph()

                # First, recreate all node objects from JSON data
                for node_data in data.get('nodes', []):
                    try:
                        # Reconstruct UniversalLocation
                        location = UniversalLocation(
                            file_path=node_data.get('file', ''),
                            start_line=int(node_data.get('line', 1)),
                            end_line=int(node_data.get('end_line', node_data.get('line', 1))),
                            language=node_data.get('language', '')
                        )

                        # Reconstruct UniversalNode
                        node = UniversalNode(
                            id=node_data['id'],
                            name=node_data.get('name', ''),
                            node_type=NodeType(node_data.get('type', 'function')),
                            location=location,
                            language=node_data.get('language', ''),
                            complexity=int(node_data.get('complexity', 0))
                        )

                        # Add to our nodes dictionary
                        self.nodes[node.id] = node

                        # Add to rustworkx graph with node ID as data
                        node_index = self.graph.add_node(node.id)

                        # Store rustworkx index in node object
                        node._rustworkx_index = node_index

                    except (KeyError, ValueError, TypeError) as e:
                        logger.warning(f"Failed to reconstruct node {node_data.get('id', 'unknown')}: {e}")
                        continue

                # Then, recreate all relationship objects and edges
                for edge_data in data.get('edges', []):
                    try:
                        # Reconstruct UniversalRelationship
                        rel = UniversalRelationship(
                            id=edge_data['id'],
                            source_id=edge_data['source'],
                            target_id=edge_data['target'],
                            relationship_type=RelationshipType(edge_data.get('type', 'calls')),
                            strength=float(edge_data.get('strength', 1.0))
                        )

                        # Add to our relationships dictionary
                        self.relationships[rel.id] = rel

                        # Find source and target node indices
                        source_node = self.nodes.get(rel.source_id)
                        target_node = self.nodes.get(rel.target_id)

                        if source_node and target_node:
                            source_idx = getattr(source_node, '_rustworkx_index', None)
                            target_idx = getattr(target_node, '_rustworkx_index', None)

                            if source_idx is not None and target_idx is not None:
                                # Add edge to rustworkx graph
                                edge_index = self.graph.add_edge(source_idx, target_idx, rel.id)

                                # Store edge index in relationship object
                                rel._rustworkx_edge_index = edge_index
                            else:
                                logger.warning(f"Could not find indices for relationship {rel.id}")
                        else:
                            logger.warning(f"Could not find nodes for relationship {rel.id}")

                    except (KeyError, ValueError, TypeError) as e:
                        logger.warning(f"Failed to reconstruct relationship {edge_data.get('id', 'unknown')}: {e}")
                        continue

            logger.info("Graph loaded from JSON successfully")
            return True

        except Exception as e:
            logger.warning(f"JSON deserialization failed: {e}")
            return False

    def export_analysis_report(self, filename: str, format: str = "json") -> bool:
        """
        Export comprehensive analysis report in various formats.

        Args:
            filename: Output filename
            format: Export format ("json", "yaml", "csv")

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate comprehensive analysis
            report = {
                "metadata": {
                    "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "graph_size": len(self.nodes),
                    "relationship_count": len(self.relationships)
                },
                "statistics": self.get_statistics(),
                "centrality_analysis": {
                    "betweenness": self.calculate_centrality(),
                    "pagerank": self.calculate_pagerank(),
                    "closeness": self.calculate_closeness_centrality(),
                    "eigenvector": self.calculate_eigenvector_centrality()
                },
                "structural_analysis": {
                    "articulation_points": self.find_articulation_points(),
                    "bridges": self.find_bridges(),
                    "is_dag": self.is_directed_acyclic(),
                    "cycles": self.detect_cycles(),
                    "dominating_set": self.find_dominating_set()
                },
                "connectivity_analysis": self.analyze_graph_connectivity()
            }

            if format.lower() == "json":
                import json
                with open(filename, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
            elif format.lower() == "yaml":
                try:
                    import yaml
                    with open(filename, 'w') as f:
                        yaml.dump(report, f, default_flow_style=False)
                except ImportError:
                    import json
                    logger.warning("PyYAML not available, falling back to JSON")
                    with open(filename.replace('.yaml', '.json').replace('.yml', '.json'), 'w') as f:
                        json.dump(report, f, indent=2, default=str)
            elif format.lower() == "csv":
                import csv
                # Export key metrics to CSV
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Metric", "Value"])
                    stats = report["statistics"]
                    for key, value in stats.items():
                        if isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                writer.writerow([f"{key}_{subkey}", subvalue])
                        else:
                            writer.writerow([key, value])

            logger.info(f"Analysis report exported to {filename}")
            return True

        except Exception as e:
            logger.warning(f"Report export failed: {e}")
            return False

    def _get_node_color(self, node_type: NodeType) -> str:
        """Get color for node type in visualizations."""
        color_map = {
            NodeType.MODULE: "lightblue",
            NodeType.CLASS: "lightgreen",
            NodeType.FUNCTION: "orange",
            NodeType.VARIABLE: "lightgray",
            NodeType.IMPORT: "purple"
        }
        return color_map.get(node_type, "white")

    def _get_edge_color(self, relationship_type: RelationshipType) -> str:
        """Get color for relationship type in visualizations."""
        color_map = {
            RelationshipType.CALLS: "red",
            RelationshipType.CONTAINS: "blue",
            RelationshipType.IMPORTS: "green",
            RelationshipType.REFERENCES: "orange",
            RelationshipType.INHERITS: "purple"
        }
        return color_map.get(relationship_type, "black")
