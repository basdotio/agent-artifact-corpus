"""
Language Router and Project Analysis

Intelligent language detection and project analysis system that determines
the primary languages, frameworks, and project structure for optimal parsing.
"""

import json
import logging
import mimetypes
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .universal_parser import LanguageConfig, LanguageRegistry

logger = logging.getLogger(__name__)


@dataclass
class ProjectStructure:
    """Analysis of project structure and characteristics."""

    root_path: Path
    primary_language: Optional[str] = None
    languages: Dict[str, int] = field(default_factory=dict)  # language -> file count
    frameworks: List[str] = field(default_factory=list)
    project_type: str = "unknown"

    # Directory analysis
    source_directories: List[str] = field(default_factory=list)
    test_directories: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)

    # Framework hints
    framework_hints: Dict[str, List[str]] = field(default_factory=dict)

    # Build system detection
    build_system: Optional[str] = None
    package_managers: List[str] = field(default_factory=list)

    # Quality indicators
    has_tests: bool = False
    has_docs: bool = False
    has_ci: bool = False
    has_linting: bool = False


class LanguageDetector:
    """Advanced language detection with multiple detection methods."""

    def __init__(self):
        self.registry = LanguageRegistry()
        self.mime_type_mappings = self._build_mime_mappings()
        self.shebang_patterns = self._build_shebang_patterns()
        self.content_signatures = self._build_content_signatures()

    def _build_mime_mappings(self) -> Dict[str, str]:
        """Build comprehensive MIME type to language mappings."""
        # Initialize system MIME types for better detection
        mimetypes.init()

        # Add custom MIME types for programming languages
        custom_types = [
            ('.py', 'text/x-python'),
            ('.pyw', 'text/x-python'),
            ('.java', 'text/x-java-source'),
            ('.c', 'text/x-c'),
            ('.h', 'text/x-c'),
            ('.cpp', 'text/x-c++src'),
            ('.cxx', 'text/x-c++src'),
            ('.cc', 'text/x-c++src'),
            ('.hpp', 'text/x-c++src'),
            ('.cs', 'text/x-csharp'),
            ('.js', 'application/javascript'),
            ('.mjs', 'application/javascript'),
            ('.ts', 'application/typescript'),
            ('.tsx', 'application/typescript'),
            ('.go', 'text/x-go'),
            ('.rs', 'text/x-rust'),
            ('.rb', 'text/x-ruby'),
            ('.php', 'text/x-php'),
            ('.swift', 'text/x-swift'),
            ('.kt', 'text/x-kotlin'),
            ('.scala', 'text/x-scala'),
            ('.hs', 'text/x-haskell'),
            ('.lua', 'text/x-lua'),
            ('.pl', 'text/x-perl'),
            ('.sql', 'text/x-sql'),
            ('.html', 'text/html'),
            ('.htm', 'text/html'),
            ('.css', 'text/css'),
            ('.scss', 'text/x-scss'),
            ('.sass', 'text/x-sass'),
            ('.less', 'text/x-less'),
            ('.vue', 'text/x-vue'),
            ('.jsx', 'text/x-jsx'),
        ]

        for ext, mime_type in custom_types:
            mimetypes.add_type(mime_type, ext)

        return {
            'text/x-python': 'python',
            'text/x-java-source': 'java',
            'text/x-c': 'c',
            'text/x-c++src': 'cpp',
            'text/x-csharp': 'csharp',
            'application/javascript': 'javascript',
            'text/javascript': 'javascript',
            'application/typescript': 'typescript',
            'text/x-go': 'go',
            'text/x-rust': 'rust',
            'text/x-ruby': 'ruby',
            'text/x-php': 'php',
            'text/x-swift': 'swift',
            'text/x-kotlin': 'kotlin',
            'text/x-scala': 'scala',
            'text/x-haskell': 'haskell',
            'text/x-lua': 'lua',
            'text/x-perl': 'perl',
            'text/x-sql': 'sql',
            'text/html': 'html',
            'text/css': 'css',
            'text/x-scss': 'scss',
            'text/x-sass': 'sass',
            'text/x-less': 'less',
            'text/x-vue': 'vue',
            'text/x-jsx': 'jsx',
        }

    def _build_shebang_patterns(self) -> Dict[str, str]:
        """Build shebang patterns to language mappings."""
        return {
            r'#!/usr/bin/env python': 'python',
            r'#!/usr/bin/python': 'python',
            r'#!/bin/python': 'python',
            r'#!/usr/bin/env node': 'javascript',
            r'#!/usr/bin/env ruby': 'ruby',
            r'#!/usr/bin/ruby': 'ruby',
            r'#!/bin/ruby': 'ruby',
            r'#!/usr/bin/env perl': 'perl',
            r'#!/usr/bin/perl': 'perl',
            r'#!/bin/perl': 'perl',
            r'#!/bin/bash': 'bash',
            r'#!/bin/sh': 'bash',
            r'#!/usr/bin/env bash': 'bash',
        }

    def _build_content_signatures(self) -> Dict[str, List[Tuple[str, float]]]:
        """Build content signature patterns for language detection."""
        return {
            'python': [
                (r'import\s+\w+', 0.8),
                (r'from\s+\w+\s+import', 0.8),
                (r'def\s+\w+\s*\(', 0.7),
                (r'class\s+\w+\s*\(', 0.7),
                (r'if\s+__name__\s*==\s*["\']__main__["\']', 0.9),
                (r'#.*coding[:=]\s*([-\w.]+)', 0.9),
            ],
            'javascript': [
                (r'function\s+\w+\s*\(', 0.7),
                (r'var\s+\w+\s*=', 0.6),
                (r'let\s+\w+\s*=', 0.7),
                (r'const\s+\w+\s*=', 0.7),
                (r'require\s*\(["\']', 0.8),
                (r'module\.exports\s*=', 0.8),
                (r'=>', 0.6),
            ],
            'typescript': [
                (r'interface\s+\w+', 0.8),
                (r'type\s+\w+\s*=', 0.7),
                (r':\s*\w+\s*=', 0.6),
                (r'export\s+', 0.6),
                (r'import.*from\s+["\']', 0.7),
            ],
            'java': [
                (r'public\s+class\s+\w+', 0.8),
                (r'public\s+static\s+void\s+main', 0.9),
                (r'import\s+[\w.]+;', 0.7),
                (r'package\s+[\w.]+;', 0.8),
                (r'@\w+', 0.6),
            ],
            'cpp': [
                (r'#include\s*<\w+>', 0.8),
                (r'#include\s*"\w+"', 0.8),
                (r'using\s+namespace\s+\w+', 0.7),
                (r'std::', 0.7),
                (r'int\s+main\s*\(', 0.8),
            ],
            'c': [
                (r'#include\s*<\w+\.h>', 0.8),
                (r'int\s+main\s*\(', 0.7),
                (r'printf\s*\(', 0.6),
                (r'malloc\s*\(', 0.6),
            ],
            'rust': [
                (r'fn\s+\w+\s*\(', 0.8),
                (r'use\s+\w+', 0.7),
                (r'let\s+\w+\s*=', 0.6),
                (r'match\s+\w+', 0.7),
                (r'impl\s+', 0.7),
            ],
            'go': [
                (r'package\s+\w+', 0.8),
                (r'import\s*\(', 0.7),
                (r'func\s+\w+\s*\(', 0.8),
                (r'go\s+\w+\(', 0.7),
                (r'defer\s+', 0.7),
            ],
        }

    def detect_file_language(self, file_path: Path) -> Optional[LanguageConfig]:
        """Detect the programming language of a file using multiple methods."""
        # Method 1: File extension (most reliable)
        ext_result = self.registry.get_language_by_extension(file_path)
        if ext_result:
            return ext_result

        # Method 2: MIME type detection
        mime_result = self._detect_by_mime_type(file_path)
        if mime_result:
            return mime_result

        # Method 3: File content analysis
        return self._detect_by_content(file_path)

    def _detect_by_mime_type(self, file_path: Path) -> Optional[LanguageConfig]:
        """Detect language by MIME type."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and mime_type in self.mime_type_mappings:
            lang_name = self.mime_type_mappings[mime_type]
            return self.registry.get_language_by_name(lang_name)
        return None

    def _detect_by_content(self, file_path: Path) -> Optional[LanguageConfig]:
        """Detect language by file content analysis."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            # Check shebang first
            shebang_result = self._check_shebang(content)
            if shebang_result:
                return shebang_result

            # Content signature analysis
            return self._analyze_content_signatures(content)

        except (UnicodeDecodeError, PermissionError, OSError):
            return None

    def _check_shebang(self, content: str) -> Optional[LanguageConfig]:
        """Check shebang patterns in file content."""
        if content.startswith('#!'):
            first_line = content.split('\n')[0]
            for pattern, lang_name in self.shebang_patterns.items():
                if re.match(pattern, first_line):
                    return self.registry.get_language_by_name(lang_name)
        return None

    def _analyze_content_signatures(self, content: str) -> Optional[LanguageConfig]:
        """Analyze content signatures to determine language."""
        language_scores = defaultdict(float)

        for lang_name, signatures in self.content_signatures.items():
            for pattern, weight in signatures:
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                language_scores[lang_name] += matches * weight

        if language_scores:
            best_lang = max(language_scores.keys(), key=lambda lang: language_scores[lang])
            if language_scores[best_lang] > 2.0:  # Threshold for confidence
                return self.registry.get_language_by_name(best_lang)

        return None

    def analyze_project_languages(self, project_root: Path) -> Dict[str, int]:
        """Analyze all languages used in a project."""
        language_counts = defaultdict(int)

        # Scan all files in the project
        for file_path in project_root.rglob('*'):
            if file_path.is_file() and not self._should_ignore_file(file_path):
                lang_config = self.detect_file_language(file_path)
                if lang_config:
                    language_counts[lang_config.name] += 1

        return dict(language_counts)

    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if a file should be ignored during analysis."""
        ignore_patterns = [
            # Version control
            '.git', '.svn', '.hg', '.bzr',
            # Build artifacts
            'node_modules', '__pycache__', '.pytest_cache', 'target', 'build',
            'dist', 'out', 'bin', 'obj', '.gradle', '.mvn',
            # IDE files
            '.idea', '.vscode', '.eclipse', '.settings',
            # OS files
            '.DS_Store', 'Thumbs.db', 'desktop.ini',
            # Package files
            '*.pyc', '*.pyo', '*.class', '*.o', '*.so', '*.dll', '*.exe',
        ]

        path_str = str(file_path)
        return any(pattern in path_str for pattern in ignore_patterns)


class ProjectAnalyzer:
    """Comprehensive project structure and framework analysis."""

    def __init__(self):
        self.language_detector = LanguageDetector()
        self.framework_detectors = self._build_framework_detectors()
        self.build_system_detectors = self._build_build_system_detectors()

    def _build_framework_detectors(self) -> Dict[str, Dict[str, List[str]]]:
        """Build framework detection rules."""
        return {
            'javascript': {
                'react': ['package.json:react', 'jsx', 'tsx'],
                'vue': ['package.json:vue', '.vue', 'vue.config.js'],
                'angular': ['package.json:@angular', 'angular.json', '.angular-cli.json'],
                'express': ['package.json:express'],
                'next': ['package.json:next', 'next.config.js'],
                'nuxt': ['package.json:nuxt', 'nuxt.config.js'],
                'gatsby': ['package.json:gatsby', 'gatsby-config.js'],
                'electron': ['package.json:electron'],
            },
            'python': {
                'django': ['manage.py', 'django', 'requirements.txt:Django'],
                'flask': ['app.py', 'requirements.txt:Flask'],
                'fastapi': ['requirements.txt:fastapi', 'main.py:FastAPI'],
                'tornado': ['requirements.txt:tornado'],
                'pyramid': ['requirements.txt:pyramid'],
                'bottle': ['requirements.txt:bottle'],
                'cherrypy': ['requirements.txt:cherrypy'],
                'aiohttp': ['requirements.txt:aiohttp'],
            },
            'java': {
                'spring': ['pom.xml:spring', 'build.gradle:spring'],
                'maven': ['pom.xml'],
                'gradle': ['build.gradle', 'gradlew'],
                'android': ['AndroidManifest.xml', 'build.gradle:android'],
                'junit': ['pom.xml:junit', 'build.gradle:junit'],
            },
            'rust': {
                'cargo': ['Cargo.toml'],
                'actix': ['Cargo.toml:actix'],
                'rocket': ['Cargo.toml:rocket'],
                'warp': ['Cargo.toml:warp'],
                'tokio': ['Cargo.toml:tokio'],
            },
            'go': {
                'gin': ['go.mod:gin', 'main.go:gin'],
                'echo': ['go.mod:echo'],
                'fiber': ['go.mod:fiber'],
                'beego': ['go.mod:beego'],
                'revel': ['go.mod:revel'],
            },
        }

    def _build_build_system_detectors(self) -> Dict[str, List[str]]:
        """Build system detection rules."""
        return {
            'npm': ['package.json', 'package-lock.json'],
            'yarn': ['yarn.lock'],
            'pnpm': ['pnpm-lock.yaml'],
            'pip': ['requirements.txt', 'setup.py', 'pyproject.toml'],
            'poetry': ['pyproject.toml', 'poetry.lock'],
            'pipenv': ['Pipfile', 'Pipfile.lock'],
            'conda': ['environment.yml', 'conda.yml'],
            'maven': ['pom.xml'],
            'gradle': ['build.gradle', 'gradlew'],
            'sbt': ['build.sbt'],
            'cargo': ['Cargo.toml', 'Cargo.lock'],
            'go_modules': ['go.mod', 'go.sum'],
            'composer': ['composer.json', 'composer.lock'],
            'bundler': ['Gemfile', 'Gemfile.lock'],
            'make': ['Makefile', 'makefile'],
            'cmake': ['CMakeLists.txt'],
            'bazel': ['WORKSPACE', 'BUILD'],
        }

    def analyze_project(self, project_root: Path) -> ProjectStructure:
        """Perform comprehensive project analysis."""
        logger.info("Analyzing project structure: %s", project_root)

        structure = ProjectStructure(root_path=project_root)

        # Language analysis
        structure.languages = self.language_detector.analyze_project_languages(project_root)
        if structure.languages:
            structure.primary_language = max(structure.languages.keys(), key=lambda lang: structure.languages[lang])

        # Directory structure analysis
        self._analyze_directory_structure(project_root, structure)

        # Framework detection
        structure.frameworks = self._detect_frameworks(project_root, structure.primary_language)
        structure.framework_hints = self._get_framework_hints(project_root)

        # Build system detection
        structure.build_system, structure.package_managers = self._detect_build_systems(project_root)

        # Project type classification
        structure.project_type = self._classify_project_type(structure)

        # Quality indicators
        structure.has_tests = self._has_tests(project_root)
        structure.has_docs = self._has_documentation(project_root)
        structure.has_ci = self._has_ci_cd(project_root)
        structure.has_linting = self._has_linting_config(project_root)

        logger.info("Project analysis complete: %s project with %d languages",
                   structure.project_type, len(structure.languages))

        return structure

    def _analyze_directory_structure(self, project_root: Path, structure: ProjectStructure) -> None:
        """Analyze directory structure to identify common patterns."""
        common_source_dirs = ['src', 'lib', 'app', 'source', 'code']
        common_test_dirs = ['test', 'tests', '__tests__', 'spec', 'specs']

        for item in project_root.iterdir():
            if item.is_dir():
                dir_name = item.name.lower()

                # Source directories
                if dir_name in common_source_dirs or 'src' in dir_name:
                    structure.source_directories.append(item.name)

                # Test directories
                if any(test_pattern in dir_name for test_pattern in common_test_dirs):
                    structure.test_directories.append(item.name)

            elif item.is_file():
                # Configuration files
                config_patterns = [
                    '.gitignore', '.gitattributes', 'LICENSE', 'README',
                    'setup.py', 'setup.cfg', 'pyproject.toml', 'requirements.txt',
                    'package.json', 'package-lock.json', 'yarn.lock',
                    'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
                    'Makefile', 'CMakeLists.txt', 'Dockerfile',
                    '.eslintrc', '.prettierrc', 'tsconfig.json',
                ]

                if any(pattern in item.name for pattern in config_patterns):
                    structure.config_files.append(item.name)

    def _detect_frameworks(self, project_root: Path, primary_language: Optional[str]) -> List[str]:
        """Detect frameworks used in the project."""
        if not primary_language:
            return []

        frameworks = []
        lang_lower = primary_language.lower()

        if lang_lower in self.framework_detectors:
            for framework, indicators in self.framework_detectors[lang_lower].items():
                if self._check_framework_indicators(project_root, indicators):
                    frameworks.append(framework)

        return frameworks

    def _check_framework_indicators(self, project_root: Path, indicators: List[str]) -> bool:
        """Check if framework indicators are present."""
        for indicator in indicators:
            if ':' in indicator:
                # File content check (e.g., 'package.json:react')
                file_name, content_pattern = indicator.split(':', 1)
                file_path = project_root / file_name
                if file_path.exists():
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        if content_pattern in content:
                            return True
                    except (UnicodeDecodeError, PermissionError):
                        continue
            else:
                # File existence check
                if indicator.startswith('.'):
                    # Extension check
                    if list(project_root.rglob(f"*{indicator}")):
                        return True
                else:
                    # File name check
                    if (project_root / indicator).exists():
                        return True

        return False

    def _get_framework_hints(self, project_root: Path) -> Dict[str, List[str]]:
        """Get additional framework hints from various sources."""
        hints = defaultdict(list)

        # Package.json analysis
        package_json = project_root / 'package.json'
        if package_json.exists():
            hints.update(self._analyze_package_json(package_json))

        # Requirements.txt analysis
        requirements_txt = project_root / 'requirements.txt'
        if requirements_txt.exists():
            hints.update(self._analyze_requirements_txt(requirements_txt))

        # Cargo.toml analysis
        cargo_toml = project_root / 'Cargo.toml'
        if cargo_toml.exists():
            hints.update(self._analyze_cargo_toml(cargo_toml))

        return dict(hints)

    def _analyze_package_json(self, package_json_path: Path) -> Dict[str, List[str]]:
        """Analyze package.json for framework hints."""
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            hints = defaultdict(list)

            # Check dependencies
            deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}

            framework_mappings = {
                'react': ['react', '@types/react'],
                'vue': ['vue', 'vue-cli'],
                'angular': ['@angular/core', '@angular/cli'],
                'express': ['express'],
                'next': ['next'],
                'gatsby': ['gatsby'],
                'electron': ['electron'],
                'typescript': ['typescript', '@types/node'],
                'webpack': ['webpack'],
                'babel': ['@babel/core'],
                'eslint': ['eslint'],
                'jest': ['jest'],
                'mocha': ['mocha'],
                'cypress': ['cypress'],
            }

            for framework, packages in framework_mappings.items():
                for package in packages:
                    if package in deps:
                        hints[framework].append(f"dependency: {package}")

            return dict(hints)

        except (OSError, PermissionError):
            return {}
        except Exception:  # Covers JSONDecodeError and other issues
            return {}

    def _analyze_requirements_txt(self, requirements_path: Path) -> Dict[str, List[str]]:
        """Analyze requirements.txt for framework hints."""
        try:
            content = requirements_path.read_text(encoding='utf-8', errors='ignore')
            hints = defaultdict(list)

            framework_mappings = {
                'django': ['Django', 'django'],
                'flask': ['Flask', 'flask'],
                'fastapi': ['fastapi', 'FastAPI'],
                'tornado': ['tornado'],
                'pyramid': ['pyramid'],
                'aiohttp': ['aiohttp'],
                'requests': ['requests'],
                'pandas': ['pandas'],
                'numpy': ['numpy'],
                'tensorflow': ['tensorflow'],
                'pytorch': ['torch', 'pytorch'],
                'pytest': ['pytest'],
            }

            for framework, packages in framework_mappings.items():
                for package in packages:
                    if package in content:
                        hints[framework].append(f"requirement: {package}")

            return dict(hints)

        except (FileNotFoundError, PermissionError):
            return {}

    def _analyze_cargo_toml(self, cargo_path: Path) -> Dict[str, List[str]]:
        """Analyze Cargo.toml for framework hints."""
        try:
            content = cargo_path.read_text(encoding='utf-8', errors='ignore')
            hints = defaultdict(list)

            framework_mappings = {
                'actix': ['actix-web', 'actix'],
                'rocket': ['rocket'],
                'warp': ['warp'],
                'tokio': ['tokio'],
                'serde': ['serde'],
                'clap': ['clap'],
                'diesel': ['diesel'],
            }

            for framework, packages in framework_mappings.items():
                for package in packages:
                    if package in content:
                        hints[framework].append(f"dependency: {package}")

            return dict(hints)

        except (FileNotFoundError, PermissionError):
            return {}

    def _detect_build_systems(self, project_root: Path) -> Tuple[Optional[str], List[str]]:
        """Detect build systems and package managers."""
        detected_systems = []

        for system, indicators in self.build_system_detectors.items():
            for indicator in indicators:
                if (project_root / indicator).exists():
                    detected_systems.append(system)
                    break

        # Determine primary build system
        primary_system = None
        if detected_systems:
            # Priority order for primary system
            priority_order = [
                'cargo', 'go_modules', 'maven', 'gradle', 'npm', 'yarn', 'pnpm',
                'poetry', 'pipenv', 'pip', 'composer', 'bundler', 'make', 'cmake'
            ]

            for system in priority_order:
                if system in detected_systems:
                    primary_system = system
                    break

        return primary_system, detected_systems

    def _classify_project_type(self, structure: ProjectStructure) -> str:
        """Classify the type of project based on analysis."""

        # Web application indicators
        web_frameworks = ['react', 'vue', 'angular', 'django', 'flask', 'express', 'next', 'gatsby']
        if any(fw in structure.frameworks for fw in web_frameworks):
            return 'web_application'

        # Mobile application indicators
        mobile_indicators = ['android', 'react-native', 'flutter', 'ionic']
        if any(ind in structure.frameworks for ind in mobile_indicators):
            return 'mobile_application'

        # Desktop application indicators
        desktop_indicators = ['electron', 'qt', 'gtk', 'tkinter']
        if any(ind in structure.frameworks for ind in desktop_indicators):
            return 'desktop_application'

        # API/Service indicators
        api_frameworks = ['fastapi', 'express', 'actix', 'gin', 'spring']
        if any(fw in structure.frameworks for fw in api_frameworks):
            return 'api_service'

        # Library/package indicators
        if structure.build_system in ['cargo', 'npm', 'pip', 'maven', 'gradle']:
            setup_files = ['setup.py', 'package.json', 'Cargo.toml', 'pom.xml']
            if any(setup_file in structure.config_files for setup_file in setup_files):
                return 'library_package'

        # CLI tool indicators
        cli_indicators = ['click', 'argparse', 'clap', 'cobra']
        if any(cli in str(structure.framework_hints) for cli in cli_indicators):
            return 'cli_tool'

        # Data science project indicators
        ds_indicators = ['jupyter', 'pandas', 'numpy', 'tensorflow', 'pytorch']
        if any(ds in str(structure.framework_hints) for ds in ds_indicators):
            return 'data_science'

        # Game development indicators
        game_indicators = ['unity', 'unreal', 'godot', 'pygame']
        if any(game in str(structure.framework_hints) for game in game_indicators):
            return 'game'

        return 'application'

    def _has_tests(self, project_root: Path) -> bool:
        """Check if the project has test files."""
        test_patterns = ['*test*', '*spec*', 'tests/*', 'test/*', '__tests__/*']

        for pattern in test_patterns:
            if list(project_root.rglob(pattern)):
                return True

        return False

    def _has_documentation(self, project_root: Path) -> bool:
        """Check if the project has documentation."""
        doc_files = ['README.md', 'README.rst', 'README.txt', 'CHANGELOG.md', 'docs/']

        for doc_file in doc_files:
            if (project_root / doc_file).exists():
                return True

        return False

    def _has_ci_cd(self, project_root: Path) -> bool:
        """Check if the project has CI/CD configuration."""
        ci_files = [
            '.github/workflows/',
            '.gitlab-ci.yml',
            '.travis.yml',
            'circle.yml',
            '.circleci/',
            'azure-pipelines.yml',
            'Jenkinsfile',
            '.drone.yml',
        ]

        for ci_file in ci_files:
            if (project_root / ci_file).exists():
                return True

        return False

    def _has_linting_config(self, project_root: Path) -> bool:
        """Check if the project has linting configuration."""
        lint_files = [
            '.eslintrc.js', '.eslintrc.json', '.eslintrc.yml',
            '.pylintrc', 'pylint.cfg', 'setup.cfg',
            '.flake8', 'tox.ini',
            '.rustfmt.toml', 'rustfmt.toml',
            '.golangci.yml', '.golangci.yaml',
            'ktlint.gradle',
        ]

        for lint_file in lint_files:
            if (project_root / lint_file).exists():
                return True

        return False

    def get_optimal_parsing_strategy(self, structure: ProjectStructure) -> Dict[str, Any]:
        """Get optimal parsing strategy based on project analysis."""
        strategy = {
            'primary_language': structure.primary_language,
            'languages_to_parse': list(structure.languages.keys()),
            'framework_optimizations': [],
            'ignore_patterns': [],
            'priority_directories': structure.source_directories,
            'parsing_order': [],
        }

        # Framework-specific optimizations
        if 'react' in structure.frameworks:
            strategy['framework_optimizations'].append('jsx_support')
        if 'vue' in structure.frameworks:
            strategy['framework_optimizations'].append('vue_sfc_support')
        if 'django' in structure.frameworks:
            strategy['framework_optimizations'].append('django_templates')

        # Ignore patterns based on project type
        common_ignores = [
            'node_modules/*', '__pycache__/*', '.git/*',
            'build/*', 'dist/*', 'target/*', 'out/*'
        ]
        strategy['ignore_patterns'].extend(common_ignores)

        # Language-specific ignores
        if 'javascript' in structure.languages:
            strategy['ignore_patterns'].extend(['*.min.js', '*.bundle.js'])
        if 'python' in structure.languages:
            strategy['ignore_patterns'].extend(['*.pyc', '*.pyo', '.pytest_cache/*'])

        # Parsing order (most important first)
        if structure.source_directories:
            strategy['parsing_order'].extend(structure.source_directories)
        strategy['parsing_order'].append('.')  # Root directory
        if structure.test_directories:
            strategy['parsing_order'].extend(structure.test_directories)

        return strategy


def get_project_languages() -> List[str]:
    """Get list of supported project languages."""
    registry = LanguageRegistry()
    return [config.name for config in registry.get_all_languages()]


def analyze_project_structure(project_root: Path) -> ProjectStructure:
    """Convenience function to analyze project structure."""
    analyzer = ProjectAnalyzer()
    return analyzer.analyze_project(project_root)


def detect_file_language(file_path: Path) -> Optional[str]:
    """Convenience function to detect file language."""
    detector = LanguageDetector()
    result = detector.detect_file_language(file_path)
    return result.name if result else None

