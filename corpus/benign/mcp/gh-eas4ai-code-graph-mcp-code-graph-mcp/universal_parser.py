"""
Universal Multi-Language Parser

Uses ast-grep as the backend to parse 25+ programming languages into a universal AST format.
Provides language-agnostic parsing with consistent node types and relationships.
"""

import logging
import fnmatch
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from ast_grep_py import SgRoot  # type: ignore[import-untyped]
except ImportError:
    SgRoot = None

from .universal_graph import (
    NodeType,
    RelationshipType,
    UniversalLocation,
    UniversalNode,
    UniversalRelationship,
)
from .rustworkx_graph import RustworkxCodeGraph

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LanguageConfig:
    """Configuration for a specific programming language."""

    name: str
    extensions: tuple
    ast_grep_id: str
    comment_patterns: tuple
    string_patterns: tuple

    # Language-specific parsing rules
    function_patterns: tuple
    class_patterns: tuple
    variable_patterns: tuple
    import_patterns: tuple


class LanguageRegistry:
    """Registry of supported programming languages with their configurations."""

    LANGUAGES = {
        "javascript": LanguageConfig(
            name="JavaScript",
            extensions=(".js", ".mjs", ".jsx"),
            ast_grep_id="javascript",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"', "'", "`"),
            function_patterns=("function", "=>", "async function"),
            class_patterns=("class",),
            variable_patterns=("var", "let", "const"),
            import_patterns=("import", "require", "export")
        ),
        "typescript": LanguageConfig(
            name="TypeScript",
            extensions=(".ts", ".tsx", ".d.ts"),
            ast_grep_id="typescript",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"', "'", "`"),
            function_patterns=("function", "=>", "async function"),
            class_patterns=("class", "interface", "type"),
            variable_patterns=("var", "let", "const"),
            import_patterns=("import", "export", "declare")
        ),
        "python": LanguageConfig(
            name="Python",
            extensions=(".py", ".pyi", ".pyw"),
            ast_grep_id="python",
            comment_patterns=("#", '"""', "'''"),
            string_patterns=('"', "'", '"""', "'''"),
            function_patterns=("def", "async def", "lambda"),
            class_patterns=("class",),
            variable_patterns=("=", ":"),
            import_patterns=("import", "from", "import")
        ),
        "java": LanguageConfig(
            name="Java",
            extensions=(".java",),
            ast_grep_id="java",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"',),
            function_patterns=("public", "private", "protected", "static"),
            class_patterns=("class", "interface", "enum"),
            variable_patterns=("int", "String", "boolean", "double", "float"),
            import_patterns=("import", "package")
        ),
        "rust": LanguageConfig(
            name="Rust",
            extensions=(".rs",),
            ast_grep_id="rust",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"', "'"),
            function_patterns=("fn", "async fn"),
            class_patterns=("struct", "enum", "trait", "impl"),
            variable_patterns=("let", "const", "static"),
            import_patterns=("use", "mod", "extern")
        ),
        "go": LanguageConfig(
            name="Go",
            extensions=(".go",),
            ast_grep_id="go",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"', "`"),
            function_patterns=("func",),
            class_patterns=("type", "struct", "interface"),
            variable_patterns=("var", ":="),
            import_patterns=("import", "package")
        ),
        "cpp": LanguageConfig(
            name="C++",
            extensions=(".cpp", ".cc", ".cxx", ".hpp", ".h"),
            ast_grep_id="cpp",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"', "'"),
            function_patterns=("int", "void", "auto", "template"),
            class_patterns=("class", "struct", "namespace"),
            variable_patterns=("int", "double", "float", "char", "auto"),
            import_patterns=("#include", "using", "namespace")
        ),
        "c": LanguageConfig(
            name="C",
            extensions=(".c", ".h"),
            ast_grep_id="c",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"', "'"),
            function_patterns=("int", "void", "char", "float", "double"),
            class_patterns=("struct", "enum", "union"),
            variable_patterns=("int", "char", "float", "double", "static"),
            import_patterns=("#include", "#define")
        ),
        "csharp": LanguageConfig(
            name="C#",
            extensions=(".cs",),
            ast_grep_id="csharp",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"', "'"),
            function_patterns=("public", "private", "protected", "static"),
            class_patterns=("class", "interface", "struct", "enum"),
            variable_patterns=("int", "string", "bool", "double", "var"),
            import_patterns=("using", "namespace")
        ),
        "php": LanguageConfig(
            name="PHP",
            extensions=(".php",),
            ast_grep_id="php",
            comment_patterns=("//", "/*", "*/", "#"),
            string_patterns=('"', "'"),
            function_patterns=("function", "public function", "private function"),
            class_patterns=("class", "interface", "trait"),
            variable_patterns=("$",),
            import_patterns=("require", "include", "use")
        ),
        "ruby": LanguageConfig(
            name="Ruby",
            extensions=(".rb",),
            ast_grep_id="ruby",
            comment_patterns=("#",),
            string_patterns=('"', "'"),
            function_patterns=("def", "class", "module"),
            class_patterns=("class", "module"),
            variable_patterns=("@", "@@", "$"),
            import_patterns=("require", "load", "include")
        ),
        "swift": LanguageConfig(
            name="Swift",
            extensions=(".swift",),
            ast_grep_id="swift",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"',),
            function_patterns=("func", "init"),
            class_patterns=("class", "struct", "enum", "protocol"),
            variable_patterns=("var", "let"),
            import_patterns=("import",)
        ),
        "kotlin": LanguageConfig(
            name="Kotlin",
            extensions=(".kt", ".kts"),
            ast_grep_id="kotlin",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"', "'"),
            function_patterns=("fun", "suspend fun"),
            class_patterns=("class", "interface", "object", "enum"),
            variable_patterns=("val", "var"),
            import_patterns=("import", "package")
        ),
        "scala": LanguageConfig(
            name="Scala",
            extensions=(".scala",),
            ast_grep_id="scala",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"', "'"),
            function_patterns=("def", "val", "var"),
            class_patterns=("class", "object", "trait", "case class"),
            variable_patterns=("val", "var"),
            import_patterns=("import", "package")
        ),
        "dart": LanguageConfig(
            name="Dart",
            extensions=(".dart",),
            ast_grep_id="dart",
            comment_patterns=("//", "/*", "*/"),
            string_patterns=('"', "'"),
            function_patterns=("void", "int", "String", "double"),
            class_patterns=("class", "abstract class", "mixin"),
            variable_patterns=("var", "final", "const"),
            import_patterns=("import", "export", "library")
        ),
        "lua": LanguageConfig(
            name="Lua",
            extensions=(".lua",),
            ast_grep_id="lua",
            comment_patterns=("--", "--[[", "]]"),
            string_patterns=('"', "'"),
            function_patterns=("function", "local function"),
            class_patterns=("{}",),
            variable_patterns=("local",),
            import_patterns=("require", "dofile", "loadfile")
        ),
        "haskell": LanguageConfig(
            name="Haskell",
            extensions=(".hs", ".lhs"),
            ast_grep_id="haskell",
            comment_patterns=("--", "{-", "-}"),
            string_patterns=('"',),
            function_patterns=("::",),
            class_patterns=("data", "newtype", "class", "instance"),
            variable_patterns=("let", "where"),
            import_patterns=("import", "module")
        ),
        "elixir": LanguageConfig(
            name="Elixir",
            extensions=(".ex", ".exs"),
            ast_grep_id="elixir",
            comment_patterns=("#",),
            string_patterns=('"', "'"),
            function_patterns=("def", "defp", "defmacro"),
            class_patterns=("defmodule", "defprotocol", "defstruct"),
            variable_patterns=("@",),
            import_patterns=("import", "alias", "require")
        ),
        "erlang": LanguageConfig(
            name="Erlang",
            extensions=(".erl", ".hrl"),
            ast_grep_id="erlang",
            comment_patterns=("%",),
            string_patterns=('"',),
            function_patterns=("-export", "-spec"),
            class_patterns=("-module", "-record"),
            variable_patterns=("-define",),
            import_patterns=("-import", "-include")
        ),
        "r": LanguageConfig(
            name="R",
            extensions=(".r", ".R"),
            ast_grep_id="r",
            comment_patterns=("#",),
            string_patterns=('"', "'"),
            function_patterns=("function", "<-"),
            class_patterns=("setClass", "setMethod"),
            variable_patterns=("<-", "="),
            import_patterns=("library", "require", "source")
        ),
        "matlab": LanguageConfig(
            name="MATLAB",
            extensions=(".m",),
            ast_grep_id="matlab",
            comment_patterns=("%",),
            string_patterns=('"', "'"),
            function_patterns=("function",),
            class_patterns=("classdef",),
            variable_patterns=("=",),
            import_patterns=("import",)
        ),
        "perl": LanguageConfig(
            name="Perl",
            extensions=(".pl", ".pm"),
            ast_grep_id="perl",
            comment_patterns=("#",),
            string_patterns=('"', "'"),
            function_patterns=("sub",),
            class_patterns=("package",),
            variable_patterns=("$", "@", "%"),
            import_patterns=("use", "require")
        ),
        "sql": LanguageConfig(
            name="SQL",
            extensions=(".sql",),
            ast_grep_id="sql",
            comment_patterns=("--", "/*", "*/"),
            string_patterns=('"', "'"),
            function_patterns=("CREATE FUNCTION", "CREATE PROCEDURE"),
            class_patterns=("CREATE TABLE", "CREATE VIEW"),
            variable_patterns=("DECLARE",),
            import_patterns=("USE", "IMPORT")
        ),
        "html": LanguageConfig(
            name="HTML",
            extensions=(".html", ".htm"),
            ast_grep_id="html",
            comment_patterns=("<!--", "-->"),
            string_patterns=('"', "'"),
            function_patterns=("<script>",),
            class_patterns=("class=",),
            variable_patterns=("id=",),
            import_patterns=("<link", "<script")
        ),
        "css": LanguageConfig(
            name="CSS",
            extensions=(".css",),
            ast_grep_id="css",
            comment_patterns=("/*", "*/"),
            string_patterns=('"', "'"),
            function_patterns=("@function",),
            class_patterns=(".",),
            variable_patterns=("--",),
            import_patterns=("@import", "@use")
        )
    }

    @lru_cache(maxsize=50000)
    def get_language_by_extension(self, file_path: Path) -> Optional[LanguageConfig]:
        """Get language configuration by file extension with LRU caching."""
        suffix = file_path.suffix.lower()
        for lang_config in self.LANGUAGES.values():
            if suffix in lang_config.extensions:
                return lang_config
        return None

    @lru_cache(maxsize=10000)
    def get_language_by_name(self, name: str) -> Optional[LanguageConfig]:
        """Get language configuration by name with LRU caching."""
        return self.LANGUAGES.get(name.lower())

    def get_all_languages(self) -> List[LanguageConfig]:
        """Get all supported language configurations."""
        return list(self.LANGUAGES.values())

    @lru_cache(maxsize=1)
    def get_supported_extensions(self) -> Set[str]:
        """Get all supported file extensions."""
        extensions = set()
        for lang_config in self.LANGUAGES.values():
            extensions.update(lang_config.extensions)
        return extensions


class UniversalParser:
    """Universal parser supporting 25+ programming languages via ast-grep."""

    def __init__(self):
        self.registry = LanguageRegistry()
        self.graph = RustworkxCodeGraph()

        # Check if ast-grep is available
        if SgRoot is None:
            logger.warning("ast-grep-py not available. Multi-language parsing disabled.")
            self._ast_grep_available = False
        else:
            self._ast_grep_available = True
            logger.info("ast-grep available. Supporting %d languages.", len(self.registry.LANGUAGES))

    @lru_cache(maxsize=50000)
    def is_supported_file(self, file_path: Path) -> bool:
        """Check if a file is supported for parsing."""
        return file_path.suffix.lower() in self.registry.get_supported_extensions()

    @lru_cache(maxsize=50000)
    def detect_language(self, file_path: Path) -> Optional[LanguageConfig]:
        """Detect the programming language of a file."""
        return self.registry.get_language_by_extension(file_path)

    def parse_file(self, file_path: Path) -> bool:
        """Parse a single file and add nodes to the graph."""
        if not self._ast_grep_available:
            logger.warning("ast-grep not available, skipping %s", file_path)
            return False

        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            return False

        language_config = self.detect_language(file_path)
        if not language_config:
            logger.debug("Unsupported file type: %s", file_path)
            return False

        try:
            # Read file content with proper encoding detection
            content = self._read_file_with_encoding_detection(file_path)

            # Parse with ast-grep
            if SgRoot is None:
                logger.error("ast-grep-py not available")
                return False
            sg_root = SgRoot(content, language_config.ast_grep_id)

            # Create file node
            file_node = self._create_file_node(file_path, language_config, content)
            self.graph.add_node(file_node)

            # Track processed file
            self.graph.add_processed_file(str(file_path))
            logger.debug(f"Added file to tracking: {file_path} (total: {len(self.graph._processed_files)})")

            # Parse language-specific constructs
            self._parse_functions(sg_root, file_path, language_config)
            self._parse_classes(sg_root, file_path, language_config)
            self._parse_variables(sg_root, file_path, language_config)
            self._parse_imports(sg_root, file_path, language_config)

            # Parse relationships - this is where the code graph gets its power
            self._parse_function_calls(sg_root, file_path, language_config)
            self._parse_variable_references(sg_root, file_path, language_config)
            self._parse_method_invocations(sg_root, file_path, language_config)

            logger.debug("Successfully parsed %s (%s)", file_path, language_config.name)
            return True

        except Exception as e:
            logger.error("Error parsing %s: %s", file_path, e)
            return False

    def _create_file_node(self, file_path: Path, language_config: LanguageConfig, content: str) -> UniversalNode:
        """Create a file node."""
        line_count = len(content.splitlines())

        return UniversalNode(
            id=f"file:{file_path}",
            name=file_path.name,
            node_type=NodeType.MODULE,
            location=UniversalLocation(
                file_path=str(file_path),
                start_line=1,
                end_line=line_count,
                language=language_config.name
            ),
            content=content,
            line_count=line_count,
            language=language_config.name,
            metadata={
                "file_size": len(content),
                "extension": file_path.suffix,
                "ast_grep_id": language_config.ast_grep_id
            }
        )

    def _parse_functions(self, sg_root: Any, file_path: Path, language_config: LanguageConfig) -> None:
        """Parse function definitions."""
        # This is a simplified implementation - real implementation would use ast-grep patterns
        # For now, we'll use text-based pattern matching as a fallback
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                for pattern in language_config.function_patterns:
                    if pattern in line and not line.strip().startswith(language_config.comment_patterns[0]):
                        func_name = self._extract_function_name(line, pattern, language_config)
                        if func_name:
                            func_node = UniversalNode(
                                id=f"function:{file_path}:{func_name}:{i}",
                                name=func_name,
                                node_type=NodeType.FUNCTION,
                                location=UniversalLocation(
                                    file_path=str(file_path),
                                    start_line=i,
                                    end_line=i,
                                    language=language_config.name
                                ),
                                language=language_config.name,
                                complexity=1,  # Basic complexity
                                metadata={"pattern": pattern}
                            )
                            self.graph.add_node(func_node)

                            # Add contains relationship
                            rel = UniversalRelationship(
                                id=f"contains:file:{file_path}:function:{func_name}:{i}",
                                source_id=f"file:{file_path}",
                                target_id=func_node.id,
                                relationship_type=RelationshipType.CONTAINS
                            )
                            self.graph.add_relationship(rel)

        except Exception as e:
            logger.debug("Error parsing functions in %s: %s", file_path, e)

    def _parse_classes(self, sg_root: Any, file_path: Path, language_config: LanguageConfig) -> None:
        """Parse class definitions."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                for pattern in language_config.class_patterns:
                    if pattern in line and not line.strip().startswith(language_config.comment_patterns[0]):
                        class_name = self._extract_class_name(line, pattern, language_config)
                        if class_name:
                            class_node = UniversalNode(
                                id=f"class:{file_path}:{class_name}:{i}",
                                name=class_name,
                                node_type=NodeType.CLASS,
                                location=UniversalLocation(
                                    file_path=str(file_path),
                                    start_line=i,
                                    end_line=i,
                                    language=language_config.name
                                ),
                                language=language_config.name,
                                metadata={"pattern": pattern}
                            )
                            self.graph.add_node(class_node)

                            # Add contains relationship
                            rel = UniversalRelationship(
                                id=f"contains:file:{file_path}:class:{class_name}:{i}",
                                source_id=f"file:{file_path}",
                                target_id=class_node.id,
                                relationship_type=RelationshipType.CONTAINS
                            )
                            self.graph.add_relationship(rel)

        except Exception as e:
            logger.debug("Error parsing classes in %s: %s", file_path, e)

    def _parse_variables(self, sg_root: Any, file_path: Path, language_config: LanguageConfig) -> None:
        """Parse variable definitions."""
        # Simplified implementation for variable parsing
        pass

    def _parse_imports(self, sg_root: Any, file_path: Path, language_config: LanguageConfig) -> None:
        """Parse import statements."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                for pattern in language_config.import_patterns:
                    if line.strip().startswith(pattern):
                        import_target = self._extract_import_target(line, pattern, language_config)
                        if import_target:
                            import_node = UniversalNode(
                                id=f"import:{file_path}:{import_target}:{i}",
                                name=import_target,
                                node_type=NodeType.IMPORT,
                                location=UniversalLocation(
                                    file_path=str(file_path),
                                    start_line=i,
                                    end_line=i,
                                    language=language_config.name
                                ),
                                language=language_config.name,
                                metadata={"pattern": pattern}
                            )
                            self.graph.add_node(import_node)

                            # Add import relationship
                            rel = UniversalRelationship(
                                id=f"imports:file:{file_path}:module:{import_target}:{i}",
                                source_id=f"file:{file_path}",
                                target_id=f"module:{import_target}",
                                relationship_type=RelationshipType.IMPORTS
                            )
                            self.graph.add_relationship(rel)

        except Exception as e:
            logger.debug("Error parsing imports in %s: %s", file_path, e)

    @lru_cache(maxsize=100000)
    def _extract_function_name(self, line: str, pattern: str, language_config: LanguageConfig) -> Optional[str]:
        """Extract function name from a line with LRU caching."""
        # Simplified name extraction - real implementation would be more sophisticated
        parts = line.strip().split()
        try:
            if pattern == "def" and len(parts) >= 2:
                return parts[1].split("(")[0]
            elif pattern == "function" and len(parts) >= 2:
                return parts[1].split("(")[0]
            elif pattern == "func" and len(parts) >= 2:
                return parts[1].split("(")[0]
        except (IndexError, AttributeError):
            pass
        return None

    @lru_cache(maxsize=50000)
    def _extract_class_name(self, line: str, pattern: str, language_config: LanguageConfig) -> Optional[str]:
        """Extract class name from a line with LRU caching."""
        parts = line.strip().split()
        try:
            if pattern == "class" and len(parts) >= 2:
                return parts[1].split("(")[0].split(":")[0].split("{")[0]
            elif pattern == "struct" and len(parts) >= 2:
                return parts[1].split("{")[0]
        except (IndexError, AttributeError):
            pass
        return None

    @lru_cache(maxsize=100000)
    def _extract_import_target(self, line: str, pattern: str, language_config: LanguageConfig) -> Optional[str]:
        """Extract import target from a line with LRU caching."""
        try:
            if pattern == "import":
                # Handle different import styles
                if "from" in line:
                    # from X import Y
                    parts = line.split("from")
                    if len(parts) >= 2:
                        return parts[1].split("import")[0].strip()
                else:
                    # import X
                    return line.replace("import", "").strip().split()[0]
            elif pattern == "require":
                # require('module') or require "module"
                import re
                match = re.search(r'require\s*\(?["\']([^"\']+)["\']', line)
                if match:
                    return match.group(1)
        except (IndexError, AttributeError):
            pass
        return None

    def _parse_function_calls(self, sg_root: Any, file_path: Path, language_config: LanguageConfig) -> None:
        """Parse function calls to create CALLS relationships."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()

            # Get all function nodes for this file to establish calling context
            file_functions = self._get_file_functions(file_path)

            # Parse each line for function calls
            for i, line in enumerate(lines, 1):
                if not self._should_process_line(line, language_config):
                    continue

                calling_function = self._find_calling_function(i, file_functions)
                if calling_function:
                    self._process_function_calls_in_line(line, i, calling_function, language_config)

        except Exception as e:
            logger.debug("Error parsing function calls in %s: %s", file_path, e)

    def _get_file_functions(self, file_path: Path) -> Dict[int, UniversalNode]:
        """Get all function nodes for a specific file."""
        file_functions = {}
        for node in self.graph.nodes.values():
            if (node.location.file_path == str(file_path) and
                node.node_type == NodeType.FUNCTION):
                # Map line numbers to function nodes for context
                file_functions[node.location.start_line] = node
        return file_functions

    def _should_process_line(self, line: str, language_config: LanguageConfig) -> bool:
        """Check if a line should be processed for function calls."""
        line_stripped = line.strip()

        # Skip empty lines and comments
        if not line_stripped or line_stripped.startswith(language_config.comment_patterns):
            return False

        # Skip function/class definitions - these are not function calls
        definition_keywords = ['def ', 'function ', 'func ', 'fn ', 'class ', 'struct ', 'interface ', 'public ', 'private ', 'static ']
        if any(keyword in line_stripped for keyword in definition_keywords):
            return False

        return True

    def _find_calling_function(self, line_number: int, file_functions: Dict[int, UniversalNode]) -> Optional[UniversalNode]:
        """Find the function that contains the given line number."""
        # Sort functions by line number to find the correct containing function
        sorted_functions = sorted(file_functions.items(), key=lambda x: x[0])

        containing_function = None
        for i, (func_line, func_node) in enumerate(sorted_functions):
            if func_line <= line_number:
                # Check if this function contains the line
                if func_node.location.end_line and line_number <= func_node.location.end_line:
                    containing_function = func_node
                elif not func_node.location.end_line:
                    # If no end_line, check if there's a next function
                    if i + 1 < len(sorted_functions):
                        next_func_line = sorted_functions[i + 1][0]
                        if line_number < next_func_line:
                            containing_function = func_node
                    else:
                        # Last function in file, assume it contains remaining lines
                        containing_function = func_node
            else:
                # We've passed the line, stop searching
                break

        return containing_function

    def _process_function_calls_in_line(self, line: str, line_number: int, calling_function: UniversalNode, language_config: LanguageConfig) -> None:
        """Process function calls found in a single line."""
        function_calls = self._extract_function_calls(line, language_config)

        for called_function in function_calls:
            target_nodes = self.graph.find_nodes_by_name(called_function, exact_match=True)

            for target_node in target_nodes:
                if target_node.node_type == NodeType.FUNCTION:
                    self._create_function_call_relationship(calling_function, target_node, line_number, line)

    def _create_function_call_relationship(self, calling_function: UniversalNode, target_node: UniversalNode, line_number: int, line: str) -> None:
        """Create a CALLS relationship between two functions."""
        # Prevent false self-loops - only allow if it's a genuine recursive call
        if calling_function.id == target_node.id:
            # Check if this is a genuine recursive call by looking at the context
            function_name = calling_function.name
            line_stripped = line.strip()

            # Skip if this looks like a false positive:
            # 1. Function name appears at the start (likely a definition)
            # 2. Line contains definition keywords
            # 3. Line is too short to be a meaningful call
            if (line_stripped.startswith(function_name) or
                any(keyword in line_stripped for keyword in ['def ', 'function ', 'func ', 'class ']) or
                len(line_stripped) < 10):
                logger.debug(f"Skipping false self-loop for {function_name}: {line_stripped}")
                return

            logger.debug(f"Creating recursive call relationship for {function_name}: {line_stripped}")

        rel = UniversalRelationship(
            id=f"calls:{calling_function.id}:{target_node.id}:{line_number}",
            source_id=calling_function.id,
            target_id=target_node.id,
            relationship_type=RelationshipType.CALLS,
            metadata={
                "call_line": line_number,
                "call_context": line.strip(),
                "is_recursive": calling_function.id == target_node.id
            }
        )
        self.graph.add_relationship(rel)

    def _parse_variable_references(self, sg_root: Any, file_path: Path, language_config: LanguageConfig) -> None:
        """Parse variable references to create REFERENCES relationships."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()

            # Get all variable nodes for this file and other files
            variable_nodes = {}
            for node in self.graph.nodes.values():
                if node.node_type == NodeType.VARIABLE:
                    variable_nodes[node.name] = node

            # Parse each line for variable references
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith(tuple(language_config.comment_patterns)):
                    continue

                # Look for variable references
                variable_refs = self._extract_variable_references(line, language_config, frozenset(variable_nodes.keys()))

                for var_name in variable_refs:
                    if var_name in variable_nodes:
                        target_node = variable_nodes[var_name]

                        # Create a reference node for this usage
                        ref_node = UniversalNode(
                            id=f"ref:{file_path}:{var_name}:{i}",
                            name=var_name,
                            node_type=NodeType.REFERENCE,
                            location=UniversalLocation(
                                file_path=str(file_path),
                                start_line=i,
                                end_line=i,
                                language=language_config.name
                            ),
                            content=line.strip(),
                            metadata={
                                "reference_context": line.strip(),
                                "referenced_variable": target_node.id
                            }
                        )
                        self.graph.add_node(ref_node)

                        # Create REFERENCES relationship
                        rel = UniversalRelationship(
                            id=f"references:{ref_node.id}:{target_node.id}",
                            source_id=ref_node.id,
                            target_id=target_node.id,
                            relationship_type=RelationshipType.REFERENCES,
                            metadata={
                                "reference_line": i,
                                "reference_context": line.strip()
                            }
                        )
                        self.graph.add_relationship(rel)

        except Exception as e:
            logger.debug("Error parsing variable references in %s: %s", file_path, e)

    def _parse_method_invocations(self, sg_root: Any, file_path: Path, language_config: LanguageConfig) -> None:
        """Parse method invocations (object.method() calls)."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith(tuple(language_config.comment_patterns)):
                    continue

                # Look for method invocation patterns like obj.method()
                method_calls = self._extract_method_invocations(line, language_config)

                for obj_name, method_name in method_calls:
                    # Try to find the method in our graph
                    target_nodes = self.graph.find_nodes_by_name(method_name, exact_match=True)

                    for target_node in target_nodes:
                        if target_node.node_type == NodeType.FUNCTION:
                            # Find the calling context
                            calling_function = self._find_containing_function(file_path, i)

                            if calling_function:
                                # Create CALLS relationship for method invocation
                                rel = UniversalRelationship(
                                    id=f"calls:{calling_function.id}:{target_node.id}:{i}:method",
                                    source_id=calling_function.id,
                                    target_id=target_node.id,
                                    relationship_type=RelationshipType.CALLS,
                                    metadata={
                                        "call_line": i,
                                        "call_type": "method_invocation",
                                        "object": obj_name,
                                        "method": method_name,
                                        "call_context": line.strip()
                                    }
                                )
                                self.graph.add_relationship(rel)

        except Exception as e:
            logger.debug("Error parsing method invocations in %s: %s", file_path, e)

    @lru_cache(maxsize=200000)
    def _extract_function_calls(self, line: str, language_config: LanguageConfig) -> List[str]:
        """Extract function call names from a line of code with LRU caching."""
        import re
        calls = []

        # More precise function call pattern - must have opening parenthesis
        # and not be preceded by definition keywords or be part of a class definition
        pattern = r'(?<!def\s)(?<!function\s)(?<!func\s)(?<!fn\s)(?<!class\s)(?<!struct\s)\b(\w+)\s*\('

        matches = re.findall(pattern, line)
        for match in matches:
            # Filter out keywords, control structures, and common constructs
            excluded_keywords = {
                'if', 'for', 'while', 'class', 'def', 'function', 'var', 'let', 'const',
                'return', 'import', 'from', 'try', 'except', 'catch', 'finally',
                'with', 'as', 'assert', 'raise', 'throw', 'new', 'delete',
                'typeof', 'instanceof', 'in', 'of', 'is', 'not', 'and', 'or'
            }

            if match.lower() not in excluded_keywords and len(match) > 1:
                calls.append(match)

        return calls

    def _read_file_with_encoding_detection(self, file_path: Path) -> str:
        """Read file with proper encoding detection."""
        # Try common encodings in order of likelihood
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Error reading {file_path} with {encoding}: {e}")
                continue

        # Last resort: read as binary and decode with errors='replace'
        try:
            return file_path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise

    @lru_cache(maxsize=300000)
    def _extract_variable_references(self, line: str, language_config: LanguageConfig, known_variables: frozenset) -> List[str]:
        """Extract variable references from a line of code with LRU caching."""
        import re
        refs = []

        # Look for word boundaries to find variable names
        words = re.findall(r'\b\w+\b', line)

        for word in words:
            if word in known_variables:
                # Make sure it's not a definition context
                if not any(pattern in line for pattern in language_config.variable_patterns):
                    refs.append(word)

        return refs

    @lru_cache(maxsize=150000)
    def _extract_method_invocations(self, line: str, language_config: LanguageConfig) -> List[tuple]:
        """Extract method invocations (object.method calls) from a line with LRU caching."""
        import re
        invocations = []

        # Pattern for obj.method() or obj.method
        pattern = r'(\w+)\.(\w+)\s*\('
        matches = re.findall(pattern, line)

        for obj_name, method_name in matches:
            invocations.append((obj_name, method_name))

        return invocations

    def _find_containing_function(self, file_path: Path, line_number: int) -> Optional[UniversalNode]:
        """Find the function that contains the given line number."""
        for node in self.graph.nodes.values():
            if (node.location.file_path == str(file_path) and
                node.node_type == NodeType.FUNCTION and
                node.location.start_line <= line_number <= (node.location.end_line or node.location.start_line + 50)):
                return node
        return None

    def _should_ignore_path(self, file_path: Path, project_root: Path) -> bool:
        """Check if a path should be ignored based on .gitignore patterns and common skip patterns."""
        # Always skip system/cache directories that should never be analyzed
        common_skip_dirs = {
            '__pycache__', '.git', '.svn', '.hg', '.bzr',
            '.pytest_cache', '.mypy_cache', '.tox', '.coverage',
            '.sass-cache', '.cache', '.DS_Store', '.idea', '.vscode', '.vs'
        }

        # Check if any part of the path contains common skip directories
        if any(part in common_skip_dirs for part in file_path.parts):
            return True

        # Check .gitignore patterns
        gitignore_path = project_root / '.gitignore'
        if not gitignore_path.exists():
            return False

        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except Exception:
            return False

        # Convert file path to relative path from project root
        try:
            relative_path = file_path.relative_to(project_root)
            path_str = str(relative_path)

            # Check against each gitignore pattern
            for pattern in patterns:
                if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(path_str, pattern + '/*'):
                    return True
                # Handle directory patterns
                if pattern.endswith('/') and path_str.startswith(pattern[:-1] + '/'):
                    return True

        except ValueError:
            # Path is not relative to project root
            pass

        return False

    def parse_directory(self, directory: Path, recursive: bool = True) -> int:
        """Parse all supported files in a directory, respecting .gitignore."""
        if not directory.is_dir():
            logger.error("Not a directory: %s", directory)
            return 0

        logger.info(f"Starting parse_directory for: {directory}")
        parsed_count = 0
        supported_extensions = self.registry.get_supported_extensions()
        logger.info(f"Supported extensions: {list(supported_extensions)[:10]}...")

        if recursive:
            files = directory.rglob("*")
        else:
            files = directory.iterdir()

        total_files = 0
        for file_path in files:
            total_files += 1
            if total_files % 100 == 0:
                logger.info(f"Processed {total_files} files, parsed {parsed_count} successfully")

            # Skip files ignored by .gitignore
            if self._should_ignore_path(file_path, directory):
                logger.debug(f"Skipping ignored path: {file_path}")
                continue

            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                # Skip files that are too large (> 1MB)
                try:
                    if file_path.stat().st_size > 1024 * 1024:  # 1MB limit
                        logger.debug(f"Skipping large file: {file_path} ({file_path.stat().st_size} bytes)")
                        continue
                except OSError:
                    continue

                logger.debug(f"Parsing file: {file_path}")
                if self.parse_file(file_path):
                    parsed_count += 1
                else:
                    logger.debug(f"Failed to parse: {file_path}")

        logger.info("Parsed %d files in %s", parsed_count, directory)
        return parsed_count

    def get_parsing_statistics(self) -> Dict[str, Any]:
        """Get statistics about the parsed code."""
        stats = self.graph.get_statistics()
        stats.update({
            "supported_languages": len(self.registry.LANGUAGES),
            "supported_extensions": list(self.registry.get_supported_extensions()),
            "ast_grep_available": self._ast_grep_available
        })
        return stats

