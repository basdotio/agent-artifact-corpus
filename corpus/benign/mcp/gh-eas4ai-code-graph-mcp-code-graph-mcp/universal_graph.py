"""
Universal Graph Data Structures

Language-agnostic data structures for representing code across multiple programming languages.
Provides a unified interface for AST nodes, relationships, and metadata.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

# Standardized cache sizes for consistent memory usage
class CacheConfig:
    """Centralized cache size configuration for consistent memory management."""
    SMALL_CACHE = 1000      # For infrequent operations
    MEDIUM_CACHE = 10000    # For moderate frequency operations
    LARGE_CACHE = 50000     # For high frequency operations
    XLARGE_CACHE = 100000   # For very high frequency operations


class NodeType(Enum):
    """Universal node types that work across all programming languages."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    EXCEPTION = "exception"
    INTERFACE = "interface"
    ENUM = "enum"
    NAMESPACE = "namespace"
    IMPORT = "import"
    LITERAL = "literal"
    CALL = "call"
    REFERENCE = "reference"


class RelationshipType(Enum):
    """Universal relationship types between code elements."""

    CONTAINS = "contains"
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    CALLS = "calls"
    IMPORTS = "imports"
    REFERENCES = "references"
    DEPENDS_ON = "depends_on"
    OVERRIDES = "overrides"
    EXTENDS = "extends"
    USES = "uses"


@dataclass
class UniversalLocation:
    """Universal location information for code elements."""

    file_path: str
    start_line: int
    end_line: int
    start_column: int = 0
    end_column: int = 0
    language: str = ""

    def __post_init__(self):
        """Validate location data after initialization."""
        if not self.file_path:
            raise ValueError("file_path cannot be empty")
        if self.start_line < 1:
            raise ValueError(f"start_line must be >= 1, got {self.start_line}")
        if self.end_line < self.start_line:
            raise ValueError(f"end_line ({self.end_line}) cannot be less than start_line ({self.start_line})")
        if self.start_column < 0:
            raise ValueError(f"start_column must be >= 0, got {self.start_column}")
        if self.end_column < 0:
            raise ValueError(f"end_column must be >= 0, got {self.end_column}")


@dataclass
class UniversalNode:
    """Universal representation of a code element."""

    id: str
    name: str
    node_type: NodeType
    location: UniversalLocation

    # Content and documentation
    content: str = ""
    docstring: Optional[str] = None

    # Code quality metrics
    complexity: int = 0
    line_count: int = 0

    # Language-specific metadata
    language: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Visibility and access
    visibility: str = "public"  # public, private, protected, internal
    is_static: bool = False
    is_abstract: bool = False
    is_async: bool = False

    # Type information
    return_type: Optional[str] = None
    parameter_types: List[str] = field(default_factory=list)


@dataclass
class UniversalRelationship:
    """Universal representation of relationships between code elements."""

    id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType

    # Relationship metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    strength: float = 1.0  # Relationship strength (0.0 to 1.0)

    # Location where relationship is defined
    location: Optional[UniversalLocation] = None


class UniversalGraph:
    """Universal code graph supporting multiple programming languages."""

    def __init__(self):
        self.nodes: Dict[str, UniversalNode] = {}
        self.relationships: Dict[str, UniversalRelationship] = {}

        # Indexed lookups for performance
        self._nodes_by_type: Dict[NodeType, Set[str]] = {}
        self._nodes_by_language: Dict[str, Set[str]] = {}
        self._relationships_from: Dict[str, Set[str]] = {}
        self._relationships_to: Dict[str, Set[str]] = {}

        # Graph metadata
        self.metadata: Dict[str, Any] = {}

    def add_node(self, node: UniversalNode) -> None:
        """Add a node to the graph with indexing."""
        self.nodes[node.id] = node

        # Update indexes
        if node.node_type not in self._nodes_by_type:
            self._nodes_by_type[node.node_type] = set()
        self._nodes_by_type[node.node_type].add(node.id)

        if node.language:
            if node.language not in self._nodes_by_language:
                self._nodes_by_language[node.language] = set()
            self._nodes_by_language[node.language].add(node.id)

    def add_relationship(self, relationship: UniversalRelationship) -> None:
        """Add a relationship to the graph with indexing."""
        self.relationships[relationship.id] = relationship

        # Update indexes
        if relationship.source_id not in self._relationships_from:
            self._relationships_from[relationship.source_id] = set()
        self._relationships_from[relationship.source_id].add(relationship.id)

        if relationship.target_id not in self._relationships_to:
            self._relationships_to[relationship.target_id] = set()
        self._relationships_to[relationship.target_id].add(relationship.id)

    def get_node(self, node_id: str) -> Optional[UniversalNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[UniversalNode]:
        """Get all nodes of a specific type."""
        node_ids = self._nodes_by_type.get(node_type, set())
        return [self.nodes[node_id] for node_id in node_ids if node_id in self.nodes]

    def get_nodes_by_language(self, language: str) -> List[UniversalNode]:
        """Get all nodes for a specific language."""
        node_ids = self._nodes_by_language.get(language, set())
        return [self.nodes[node_id] for node_id in node_ids if node_id in self.nodes]

    def get_relationships_from(self, node_id: str) -> List[UniversalRelationship]:
        """Get all relationships originating from a node."""
        rel_ids = self._relationships_from.get(node_id, set())
        return [self.relationships[rel_id] for rel_id in rel_ids if rel_id in self.relationships]

    def get_relationships_to(self, node_id: str) -> List[UniversalRelationship]:
        """Get all relationships pointing to a node."""
        rel_ids = self._relationships_to.get(node_id, set())
        return [self.relationships[rel_id] for rel_id in rel_ids if rel_id in self.relationships]

    def get_relationships_by_type(self, relationship_type: RelationshipType) -> List[UniversalRelationship]:
        """Get all relationships of a specific type."""
        return [
            rel for rel in self.relationships.values()
            if rel.relationship_type == relationship_type
        ]

    def find_nodes_by_name(self, name: str, exact_match: bool = True) -> List[UniversalNode]:
        """Find nodes by name with optional fuzzy matching."""
        if exact_match:
            return [node for node in self.nodes.values() if node.name == name]
        else:
            name_lower = name.lower()
            return [
                node for node in self.nodes.values()
                if name_lower in node.name.lower()
            ]

    def get_connected_nodes(self, node_id: str, relationship_types: Optional[List[RelationshipType]] = None) -> List[UniversalNode]:
        """Get all nodes connected to the given node."""
        connected_ids = set()

        # Get outgoing relationships
        for rel in self.get_relationships_from(node_id):
            if not relationship_types or rel.relationship_type in relationship_types:
                connected_ids.add(rel.target_id)

        # Get incoming relationships
        for rel in self.get_relationships_to(node_id):
            if not relationship_types or rel.relationship_type in relationship_types:
                connected_ids.add(rel.source_id)

        return [self.nodes[node_id] for node_id in connected_ids if node_id in self.nodes]

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics."""
        stats = {
            "total_nodes": len(self.nodes),
            "total_relationships": len(self.relationships),
            "nodes_by_type": {},
            "nodes_by_language": {},
            "relationships_by_type": {},
            "complexity_stats": {
                "total_complexity": 0,
                "average_complexity": 0.0,
                "max_complexity": 0,
                "high_complexity_functions": 0
            }
        }

        # Count nodes by type
        for node_type, node_ids in self._nodes_by_type.items():
            stats["nodes_by_type"][node_type.value] = len(node_ids)

        # Count nodes by language
        for language, node_ids in self._nodes_by_language.items():
            stats["nodes_by_language"][language] = len(node_ids)

        # Count relationships by type
        for rel in self.relationships.values():
            rel_type = rel.relationship_type.value
            stats["relationships_by_type"][rel_type] = stats["relationships_by_type"].get(rel_type, 0) + 1

        # Calculate complexity statistics
        complexities = [node.complexity for node in self.nodes.values() if node.complexity > 0]
        if complexities:
            stats["complexity_stats"]["total_complexity"] = sum(complexities)
            stats["complexity_stats"]["average_complexity"] = sum(complexities) / len(complexities)
            stats["complexity_stats"]["max_complexity"] = max(complexities)
            stats["complexity_stats"]["high_complexity_functions"] = len([c for c in complexities if c > 10])

        return stats

    def export_graph_data(self) -> Dict[str, Any]:
        """Export complete graph data for serialization."""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type.value,
                    "language": node.language,
                    "location": {
                        "file": node.location.file_path,
                        "start_line": node.location.start_line,
                        "end_line": node.location.end_line,
                        "start_column": node.location.start_column,
                        "end_column": node.location.end_column
                    },
                    "complexity": node.complexity,
                    "line_count": node.line_count,
                    "docstring": node.docstring,
                    "visibility": node.visibility,
                    "is_static": node.is_static,
                    "is_abstract": node.is_abstract,
                    "is_async": node.is_async,
                    "return_type": node.return_type,
                    "parameter_types": node.parameter_types,
                    "metadata": node.metadata
                }
                for node in self.nodes.values()
            ],
            "relationships": [
                {
                    "id": rel.id,
                    "source_id": rel.source_id,
                    "target_id": rel.target_id,
                    "type": rel.relationship_type.value,
                    "strength": rel.strength,
                    "location": {
                        "file": rel.location.file_path,
                        "start_line": rel.location.start_line,
                        "end_line": rel.location.end_line
                    } if rel.location else None,
                    "metadata": rel.metadata
                }
                for rel in self.relationships.values()
            ],
            "statistics": self.get_statistics(),
            "metadata": self.metadata
        }

