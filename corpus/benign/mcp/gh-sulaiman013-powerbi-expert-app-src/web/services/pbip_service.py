"""
PBIP Service
============
Handles PBIP (Power BI Project) file operations including
parsing natural language requests and managing rename operations.
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class RenameRequest:
    """A single rename operation request."""
    old_name: str
    new_name: str


@dataclass
class ParsedPBIPRequest:
    """Parsed PBIP request from natural language."""
    path: Optional[str]
    renames: List[RenameRequest]


class PBIPService:
    """
    Service for handling PBIP file operations via natural language.
    """

    # Keywords that indicate a PBIP operation request
    PBIP_KEYWORDS = [
        'pbip', 'rename table', 'rename tables', 'rename the table',
        'rename column', 'rename columns', 'rename the column',
        'rename measure', 'rename measures', 'rename the measure',
        'edit table name', 'change table name', 'modify table name',
        'tmdl', 'semantic model file', 'project file',
        # Path-based detection for powerbi folders
        '\\powerbi\\', '/powerbi/', '.pbip', '.semanticmodel'
    ]

    # Patterns for extracting file paths
    PATH_PATTERNS = [
        r"(?:path|directory|folder|location)[:\s]+['\"]?([A-Za-z]:[\\\/][^\n'\"]+)['\"]?",
        r"['\"]([A-Za-z]:[\\\/][^\n'\"]+)['\"]",
        r"([A-Za-z]:[\\\/](?:[^\s\\\/]+[\\\/])+[^\s\\\/]+)"
    ]

    # Patterns for extracting rename operations
    RENAME_PATTERNS = [
        # Numbered list: "1. OldName to NewName" or "1) OldName to NewName"
        r"\d+[\.\)]\s+['\"]?([^'\"\\\/\n]+?)['\"]?\s+to\s+['\"]?([^'\"\\\/\n]+?)['\"]?\s*(?:\n|$|,)",
        # Arrow syntax: "OldName -> NewName" or "OldName -> NewName"
        r"['\"]?([^'\"\\\/\n]+?)['\"]?\s*(?:->|\u2192)\s*['\"]?([^'\"\\\/\n]+?)['\"]?\s*(?:\n|$|,)",
        # Explicit rename: "rename OldName to NewName"
        r"rename\s+['\"]?([^'\"\\\/\n]+?)['\"]?\s+to\s+['\"]?([^'\"\\\/\n]+?)['\"]?"
    ]

    @classmethod
    def is_pbip_request(cls, message: str) -> bool:
        """
        Check if the user message is requesting PBIP file operations.

        Args:
            message: The user's message

        Returns:
            True if the message appears to be a PBIP operation request
        """
        message_lower = message.lower()

        # Check for explicit PBIP keywords
        if any(kw in message_lower for kw in cls.PBIP_KEYWORDS):
            return True

        # Check for rename + table/column/measure pattern (flexible detection)
        has_rename = 'rename' in message_lower
        has_target = any(word in message_lower for word in ['table', 'tables', 'column', 'columns', 'measure', 'measures'])
        has_path = bool(re.search(r'[A-Za-z]:[\\\/]', message))  # Windows path pattern

        # If user mentions rename + target + has a path, likely PBIP request
        if has_rename and has_target and has_path:
            return True

        # Check for powerbi folder in path (with or without trailing slash)
        if re.search(r'[\\\/]powerbi[\\\/]?(?:[\'"\s]|$)', message_lower):
            return True

        return False

    @classmethod
    def parse_request(cls, message: str) -> ParsedPBIPRequest:
        """
        Parse a PBIP rename request from natural language.

        Args:
            message: The user's message

        Returns:
            ParsedPBIPRequest with path and list of rename operations
        """
        path = cls._extract_path(message)
        renames = cls._extract_renames(message)

        return ParsedPBIPRequest(path=path, renames=renames)

    @classmethod
    def _extract_path(cls, message: str) -> Optional[str]:
        """Extract PBIP project path from message."""
        for pattern in cls.PATH_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).strip().rstrip('\\/')
        return None

    @classmethod
    def _extract_renames(cls, message: str) -> List[RenameRequest]:
        """Extract rename operations from message."""
        renames = []

        for pattern in cls.RENAME_PATTERNS:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for old_name, new_name in matches:
                old_name = old_name.strip()
                new_name = new_name.strip()

                # Validate the rename operation
                if cls._is_valid_rename(old_name, new_name):
                    renames.append(RenameRequest(
                        old_name=old_name,
                        new_name=new_name
                    ))

        return renames

    @staticmethod
    def _is_valid_rename(old_name: str, new_name: str) -> bool:
        """
        Validate a rename operation.

        Filters out path-like patterns and ensures valid table names.
        """
        if not old_name or not new_name:
            return False
        if old_name == new_name:
            return False
        if '\\' in old_name or '/' in old_name:
            return False
        if '\\' in new_name or '/' in new_name:
            return False
        if len(old_name) >= 100 or len(new_name) >= 100:
            return False
        return True

    @staticmethod
    def format_rename_result(results: List[Dict[str, Any]]) -> str:
        """
        Format rename results into a markdown response.

        Args:
            results: List of rename result dictionaries

        Returns:
            Formatted markdown string
        """
        all_success = all(r['success'] for r in results)
        total_files = set()
        total_refs = 0

        for r in results:
            total_refs += r.get('refs', 0)
            total_files.update(r.get('files_modified', []))

        if all_success:
            response = "✅ **PBIP Table Rename Complete!**\n\n"
        else:
            response = "⚠️ **PBIP Table Rename Partially Complete**\n\n"

        response += f"**Summary:**\n"
        response += f"- Tables renamed: {len(results)}\n"
        response += f"- Files modified: {len(total_files)}\n"
        response += f"- References updated: {total_refs}\n\n"

        response += "**Renames:**\n"
        for r in results:
            status = "✅" if r['success'] else "❌"
            response += f"{status} `{r['old']}` → `{r['new']}` ({r['refs']} refs in {r['files']} files)\n"

        response += "\n📦 **Backup created automatically** before changes.\n"
        response += "\n💡 **Tip:** Refresh your Power BI Desktop to see the changes."

        return response
