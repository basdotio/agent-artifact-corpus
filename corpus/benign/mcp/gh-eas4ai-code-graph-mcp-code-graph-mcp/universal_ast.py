"""
Universal AST Analyzer

High-level analyzer that provides cross-language analysis capabilities.
Builds on the universal graph to provide code intelligence features.
"""

import logging
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Set, Union

from .universal_graph import (
    NodeType,
    RelationshipType,
    UniversalNode,
)
from .universal_parser import UniversalParser

logger = logging.getLogger(__name__)


class UniversalASTAnalyzer:
    """High-level analyzer providing cross-language analysis capabilities."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.parser = UniversalParser()
        self.graph = self.parser.graph
        self._analysis_cache: Dict[str, Any] = {}

    def analyze_project(self, recursive: bool = True) -> Dict[str, Any]:
        """Analyze entire project and return comprehensive statistics."""
        logger.info("Analyzing project: %s", self.project_root)

        # Parse all files
        parsed_files = self.parser.parse_directory(self.project_root, recursive)

        # Get basic statistics
        stats = self.graph.get_statistics()

        # Add additional analysis
        stats.update({
            "parsed_files": parsed_files,
            "code_smells": self.detect_code_smells(),
            "complexity_analysis": self.analyze_complexity(),
            "dependency_analysis": self.analyze_dependencies(),
            "quality_metrics": self.calculate_quality_metrics(),
            "language_distribution": self.get_language_distribution(),
        })

        logger.info("Analysis complete: %d nodes, %d relationships",
                   stats["total_nodes"], stats["total_relationships"])

        return stats

    def detect_code_smells(self) -> Dict[str, List[Dict[str, Any]]]:
        """Detect various code smells across all languages."""
        smells = {
            "long_functions": [],
            "complex_functions": [],
            "duplicate_logic": [],
            "large_classes": [],
            "god_classes": [],
            "dead_code": [],
            "naming_issues": [],
        }

        # Analyze functions
        functions = self.graph.get_nodes_by_type(NodeType.FUNCTION)
        for func in functions:
            # Long functions (>50 lines)
            if func.line_count > 50:
                smells["long_functions"].append({
                    "name": func.name,
                    "location": f"{func.location.file_path}:{func.location.start_line}",
                    "line_count": func.line_count,
                    "language": func.language,
                    "severity": "high" if func.line_count > 100 else "medium"
                })

            # Complex functions (high cyclomatic complexity)
            if func.complexity > 15:
                smells["complex_functions"].append({
                    "name": func.name,
                    "location": f"{func.location.file_path}:{func.location.start_line}",
                    "complexity": func.complexity,
                    "language": func.language,
                    "severity": "high" if func.complexity > 20 else "medium"
                })

            # Naming issues (single letter names, etc.)
            if len(func.name) <= 2 and func.name not in ["id", "x", "y", "i", "j", "k"]:
                smells["naming_issues"].append({
                    "name": func.name,
                    "location": f"{func.location.file_path}:{func.location.start_line}",
                    "issue": "Very short function name",
                    "language": func.language,
                    "severity": "low"
                })

        # Analyze classes
        classes = self.graph.get_nodes_by_type(NodeType.CLASS)
        for cls in classes:
            # Get methods in this class
            class_methods = [
                rel.target_id for rel in self.graph.get_relationships_from(cls.id)
                if rel.relationship_type == RelationshipType.CONTAINS
            ]
            method_count = len(class_methods)

            # Large classes (many methods)
            if method_count > 20:
                smells["large_classes"].append({
                    "name": cls.name,
                    "location": f"{cls.location.file_path}:{cls.location.start_line}",
                    "method_count": method_count,
                    "language": cls.language,
                    "severity": "high" if method_count > 30 else "medium"
                })

            # God classes (too many responsibilities)
            if method_count > 30 and cls.line_count > 500:
                smells["god_classes"].append({
                    "name": cls.name,
                    "location": f"{cls.location.file_path}:{cls.location.start_line}",
                    "method_count": method_count,
                    "line_count": cls.line_count,
                    "language": cls.language,
                    "severity": "critical"
                })

        # Find duplicate logic patterns
        smells["duplicate_logic"] = self._find_duplicate_patterns(functions)

        # Find potentially dead code
        smells["dead_code"] = self._find_dead_code()

        return smells

    @lru_cache(maxsize=10000)
    def analyze_complexity(self, threshold: int = 10) -> Dict[str, Any]:
        """Analyze code complexity across the project with LRU caching."""
        functions = self.graph.get_nodes_by_type(NodeType.FUNCTION)

        if not functions:
            return {
                "total_functions": 0,
                "average_complexity": 0.0,
                "max_complexity": 0,
                "high_complexity_functions": [],
                "complexity_distribution": {},
            }

        complexities = [func.complexity for func in functions if func.complexity > 0]

        if not complexities:
            return {
                "total_functions": len(functions),
                "average_complexity": 0.0,
                "max_complexity": 0,
                "high_complexity_functions": [],
                "complexity_distribution": {},
            }

        # Calculate distribution
        distribution = defaultdict(int)
        for complexity in complexities:
            if complexity <= 5:
                distribution["simple"] += 1
            elif complexity <= 10:
                distribution["moderate"] += 1
            elif complexity <= 20:
                distribution["complex"] += 1
            else:
                distribution["very_complex"] += 1

        # Find high complexity functions
        high_complexity = [
            {
                "name": func.name,
                "complexity": func.complexity,
                "location": f"{func.location.file_path}:{func.location.start_line}",
                "language": func.language,
                "risk_level": "critical" if func.complexity > 25 else "high"
            }
            for func in functions
            if func.complexity >= threshold
        ]

        high_complexity.sort(key=lambda x: x["complexity"], reverse=True)

        return {
            "total_functions": len(functions),
            "average_complexity": sum(complexities) / len(complexities),
            "max_complexity": max(complexities),
            "high_complexity_functions": high_complexity,
            "complexity_distribution": dict(distribution),
            "functions_above_threshold": len(high_complexity)
        }

    def analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze dependencies and coupling between modules."""
        import_relationships = self.graph.get_relationships_by_type(RelationshipType.IMPORTS)

        # Build dependency graph
        dependencies = defaultdict(set)
        reverse_dependencies = defaultdict(set)

        for rel in import_relationships:
            source_node = self.graph.get_node(rel.source_id)
            if source_node and source_node.node_type == NodeType.MODULE:
                target = rel.target_id.replace("module:", "")
                dependencies[source_node.name].add(target)
                reverse_dependencies[target].add(source_node.name)

        # Calculate metrics
        total_dependencies = sum(len(deps) for deps in dependencies.values())

        # Find highly coupled modules
        highly_coupled = [
            {
                "module": module,
                "dependency_count": len(deps),
                "dependencies": list(deps),
                "severity": "high" if len(deps) > 10 else "medium"
            }
            for module, deps in dependencies.items()
            if len(deps) > 5
        ]

        # Find modules with many dependents
        popular_modules = [
            {
                "module": module,
                "dependent_count": len(dependents),
                "dependents": list(dependents)
            }
            for module, dependents in reverse_dependencies.items()
            if len(dependents) > 3
        ]

        # Detect circular dependencies
        circular_deps = self._detect_circular_dependencies(dependencies)

        return {
            "total_modules": len(dependencies),
            "total_dependencies": total_dependencies,
            "average_dependencies_per_module": total_dependencies / len(dependencies) if dependencies else 0,
            "highly_coupled_modules": highly_coupled,
            "popular_modules": popular_modules,
            "circular_dependencies": circular_deps,
            "dependency_graph": {k: list(v) for k, v in dependencies.items()}
        }

    def calculate_quality_metrics(self) -> Dict[str, Any]:
        """Calculate overall code quality metrics."""
        functions = self.graph.get_nodes_by_type(NodeType.FUNCTION)
        modules = self.graph.get_nodes_by_type(NodeType.MODULE)

        if not functions:
            return {
                "maintainability_index": 0,
                "technical_debt_ratio": 0,
                "test_coverage_estimate": 0,
                "documentation_ratio": 0,
                "code_duplication_ratio": 0
            }

        # Calculate maintainability index (simplified)
        complexities = [func.complexity for func in functions if func.complexity > 0]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 1

        total_lines = sum(node.line_count for node in self.graph.nodes.values() if node.line_count > 0)

        # Maintainability index (0-100, higher is better)
        maintainability = max(0, 100 - (avg_complexity * 5) - (total_lines / 1000))

        # Technical debt ratio (estimated based on code smells)
        code_smells = self.detect_code_smells()
        total_smells = sum(len(smells) for smells in code_smells.values())
        debt_ratio = min(100, (total_smells / len(functions)) * 100) if functions else 0

        # Documentation ratio (functions with docstrings)
        documented_functions = len([f for f in functions if f.docstring])
        doc_ratio = (documented_functions / len(functions)) * 100 if functions else 0

        # Estimate test coverage based on file patterns
        test_files = [
            node for node in modules
            if any(pattern in node.name.lower() for pattern in ["test", "spec", "_test", ".test"])
        ]
        test_coverage_estimate = min(100, (len(test_files) / len(modules)) * 200) if modules else 0

        # Calculate duplication ratio based on duplicate patterns found
        code_smells = self.detect_code_smells()
        duplicate_patterns = code_smells.get("duplicate_logic", [])
        total_functions = len(self.graph.get_nodes_by_type(NodeType.FUNCTION))

        duplicate_function_count = sum(len(pattern["functions"]) for pattern in duplicate_patterns)
        duplication_ratio = (duplicate_function_count / total_functions * 100) if total_functions > 0 else 0

        return {
            "maintainability_index": round(maintainability, 2),
            "technical_debt_ratio": round(debt_ratio, 2),
            "test_coverage_estimate": round(test_coverage_estimate, 2),
            "documentation_ratio": round(doc_ratio, 2),
            "code_duplication_ratio": round(duplication_ratio, 2),
            "total_code_smells": total_smells,
            "quality_score": round(self._calculate_normalized_quality_score(
                maintainability, doc_ratio, test_coverage_estimate, debt_ratio, duplication_ratio
            ), 2)
        }

    def get_language_distribution(self) -> Dict[str, Any]:
        """Get distribution of languages in the project."""
        language_stats: Dict[str, Dict[str, Union[int, float]]] = defaultdict(lambda: {
            "files": 0,
            "nodes": 0,
            "functions": 0,
            "classes": 0,
            "lines": 0
        })

        for node in self.graph.nodes.values():
            if node.language:
                lang = node.language
                language_stats[lang]["nodes"] += 1
                language_stats[lang]["lines"] += node.line_count

                if node.node_type == NodeType.MODULE:
                    language_stats[lang]["files"] += 1
                elif node.node_type == NodeType.FUNCTION:
                    language_stats[lang]["functions"] += 1
                elif node.node_type == NodeType.CLASS:
                    language_stats[lang]["classes"] += 1

        # Calculate percentages
        total_files = sum(stats["files"] for stats in language_stats.values())
        total_lines = sum(stats["lines"] for stats in language_stats.values())

        for lang, stats in language_stats.items():
            stats["file_percentage"] = (stats["files"] / total_files * 100) if total_files else 0.0
            stats["line_percentage"] = (stats["lines"] / total_lines * 100) if total_lines else 0.0

        # Sort by number of lines (descending)
        sorted_languages = sorted(
            language_stats.items(),
            key=lambda x: x[1]["lines"],
            reverse=True
        )

        return {
            "languages": dict(sorted_languages),
            "primary_language": sorted_languages[0][0] if sorted_languages else None,
            "total_languages": len(language_stats),
            "polyglot_score": min(len(language_stats), 10) * 10  # 0-100 score
        }

    def _calculate_normalized_quality_score(self, maintainability: float, doc_ratio: float,
                                          test_coverage: float, debt_ratio: float,
                                          duplication_ratio: float) -> float:
        """Calculate a normalized quality score between 0 and 100."""
        # Normalize all inputs to 0-100 scale
        maintainability = max(0, min(100, maintainability))
        doc_ratio = max(0, min(100, doc_ratio))
        test_coverage = max(0, min(100, test_coverage))
        debt_ratio = max(0, min(100, debt_ratio))
        duplication_ratio = max(0, min(100, duplication_ratio))

        # Calculate weighted score (positive factors - negative factors)
        positive_score = (maintainability * 0.4 + doc_ratio * 0.2 + test_coverage * 0.3)
        negative_score = (debt_ratio * 0.3 + duplication_ratio * 0.2)

        # Final score between 0 and 100
        quality_score = positive_score - negative_score
        return max(0, min(100, quality_score))

    def find_similar_functions(self, function_name: str, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Find functions similar to the given function."""
        target_function = None
        for node in self.graph.nodes.values():
            if node.name == function_name and node.node_type == NodeType.FUNCTION:
                target_function = node
                break

        if not target_function:
            return []

        similar_functions = []
        functions = self.graph.get_nodes_by_type(NodeType.FUNCTION)

        for func in functions:
            if func.id == target_function.id:
                continue

            similarity = self._calculate_function_similarity(target_function, func)
            if similarity >= similarity_threshold:
                similar_functions.append({
                    "name": func.name,
                    "location": f"{func.location.file_path}:{func.location.start_line}",
                    "language": func.language,
                    "similarity": similarity,
                    "complexity": func.complexity
                })

        return sorted(similar_functions, key=lambda x: x["similarity"], reverse=True)

    def _find_duplicate_patterns(self, functions: List[UniversalNode]) -> List[Dict[str, Any]]:
        """Find potentially duplicate code patterns."""
        duplicates = []

        # Group functions by similar characteristics
        function_groups = defaultdict(list)

        for func in functions:
            # Group by complexity and line count (simplified)
            if func.complexity > 5 and func.line_count > 10:
                key = (func.complexity, func.line_count // 5 * 5)  # Round to nearest 5
                function_groups[key].append(func)

        # Find groups with multiple functions
        for key, group in function_groups.items():
            if len(group) > 1:
                duplicates.append({
                    "pattern": f"Functions with complexity {key[0]} and ~{key[1]} lines",
                    "count": len(group),
                    "functions": [
                        {
                            "name": func.name,
                            "location": f"{func.location.file_path}:{func.location.start_line}",
                            "language": func.language
                        }
                        for func in group
                    ],
                    "severity": "medium" if len(group) < 4 else "high"
                })

        return duplicates

    def _find_dead_code(self) -> List[Dict[str, Any]]:
        """Find potentially dead (unused) code."""
        dead_code = []

        # Find functions that are never called
        all_functions = {node.id: node for node in self.graph.get_nodes_by_type(NodeType.FUNCTION)}
        called_functions = set()

        # Find all function calls
        call_relationships = self.graph.get_relationships_by_type(RelationshipType.CALLS)
        for rel in call_relationships:
            called_functions.add(rel.target_id)

        # Functions that are defined but never called
        for func_id, func in all_functions.items():
            if func_id not in called_functions:
                # Skip entry points and special methods
                if not self._is_entry_point(func):
                    dead_code.append({
                        "name": func.name,
                        "type": "function",
                        "location": f"{func.location.file_path}:{func.location.start_line}",
                        "language": func.language,
                        "reason": "Never called",
                        "severity": "medium"
                    })

        return dead_code

    def _detect_circular_dependencies(self, dependencies: Dict[str, Set[str]]) -> List[Dict[str, Any]]:
        """Detect circular dependencies using DFS."""
        circular_deps = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                circular_deps.append({
                    "cycle": cycle,
                    "length": len(cycle) - 1,
                    "severity": "high" if len(cycle) <= 3 else "medium"
                })
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, set()):
                dfs(neighbor, path + [node])

            rec_stack.remove(node)

        for module in dependencies:
            if module not in visited:
                dfs(module, [])

        return circular_deps

    def _calculate_function_similarity(self, func1: UniversalNode, func2: UniversalNode) -> float:
        """Calculate similarity between two functions."""
        # Simple similarity based on multiple factors
        similarity_factors = []

        # Name similarity (Levenshtein distance)
        name_similarity = 1.0 - (self._levenshtein_distance(func1.name, func2.name) / max(len(func1.name), len(func2.name)))
        similarity_factors.append(name_similarity * 0.3)

        # Complexity similarity
        if func1.complexity > 0 and func2.complexity > 0:
            complexity_diff = abs(func1.complexity - func2.complexity)
            complexity_similarity = 1.0 / (1.0 + complexity_diff)
            similarity_factors.append(complexity_similarity * 0.2)

        # Line count similarity
        if func1.line_count > 0 and func2.line_count > 0:
            line_diff = abs(func1.line_count - func2.line_count)
            line_similarity = 1.0 / (1.0 + line_diff / 10.0)
            similarity_factors.append(line_similarity * 0.2)

        # Language similarity
        if func1.language == func2.language:
            similarity_factors.append(0.3)

        return sum(similarity_factors) if similarity_factors else 0.0

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _is_entry_point(self, func: UniversalNode) -> bool:
        """Check if a function is likely an entry point."""
        entry_point_patterns = [
            "main", "__main__", "init", "__init__", "setup", "run",
            "start", "begin", "execute", "handler", "callback"
        ]

        return any(
            pattern in func.name.lower()
            for pattern in entry_point_patterns
        )

    def export_analysis_report(self, output_path: Path) -> None:
        """Export comprehensive analysis report to a file."""
        analysis = self.analyze_project()

        report_content = f"""# Code Analysis Report

## Project Overview
- **Project Root**: {self.project_root}
- **Total Files Parsed**: {analysis['parsed_files']}
- **Total Languages**: {analysis['language_distribution']['total_languages']}
- **Primary Language**: {analysis['language_distribution']['primary_language']}

## Code Statistics
- **Total Nodes**: {analysis['total_nodes']:,}
- **Total Relationships**: {analysis['total_relationships']:,}
- **Functions**: {analysis['nodes_by_type'].get('function', 0):,}
- **Classes**: {analysis['nodes_by_type'].get('class', 0):,}

## Quality Metrics
- **Maintainability Index**: {analysis['quality_metrics']['maintainability_index']}/100
- **Technical Debt Ratio**: {analysis['quality_metrics']['technical_debt_ratio']}%
- **Documentation Ratio**: {analysis['quality_metrics']['documentation_ratio']}%
- **Quality Score**: {analysis['quality_metrics']['quality_score']}/100

## Code Smells Detected
- **Long Functions**: {len(analysis['code_smells']['long_functions'])}
- **Complex Functions**: {len(analysis['code_smells']['complex_functions'])}
- **Large Classes**: {len(analysis['code_smells']['large_classes'])}
- **Potential Duplicates**: {len(analysis['code_smells']['duplicate_logic'])}

## Complexity Analysis
- **Average Complexity**: {analysis['complexity_analysis']['average_complexity']:.2f}
- **Max Complexity**: {analysis['complexity_analysis']['max_complexity']}
- **High Complexity Functions**: {analysis['complexity_analysis']['functions_above_threshold']}

## Dependencies
- **Total Modules**: {analysis['dependency_analysis']['total_modules']}
- **Average Dependencies**: {analysis['dependency_analysis']['average_dependencies_per_module']:.2f}
- **Circular Dependencies**: {len(analysis['dependency_analysis']['circular_dependencies'])}
"""

        output_path.write_text(report_content, encoding='utf-8')
        logger.info("Analysis report exported to: %s", output_path)

