"""Regex-based filtering for module members and class methods."""

import re
from typing import Optional, Pattern, Union, List


class MemberFilter:
    """Filters symbols (functions, classes, methods) using regex patterns."""

    def __init__(
        self,
        include: Optional[Union[str, List[str]]] = None,
        exclude: Optional[Union[str, List[str]]] = None,
    ) -> None:
        self.include_patterns: List[Pattern[str]] = self._compile_patterns(include)
        self.exclude_patterns: List[Pattern[str]] = self._compile_patterns(exclude)

    @staticmethod
    def _compile_patterns(patterns: Optional[Union[str, List[str]]]) -> List[Pattern[str]]:
        if not patterns:
            return []
        if isinstance(patterns, str):
            patterns = [patterns]
        compiled = []
        for pat in patterns:
            if pat:
                try:
                    compiled.append(re.compile(pat))
                except re.error as e:
                    raise ValueError(f"Invalid regex pattern '{pat}': {e}") from e
        return compiled

    def matches(self, name: str, qualified_name: Optional[str] = None) -> bool:
        """Check if a symbol name passes include/exclude rules.
        
        Args:
            name: Simple name (e.g. 'fit', 'load_iris')
            qualified_name: Full name (e.g. 'RandomForestClassifier.fit')
        """
        candidates = [name]
        if qualified_name and qualified_name != name:
            candidates.append(qualified_name)

        # Check excludes first
        for pat in self.exclude_patterns:
            for cand in candidates:
                if pat.search(cand):
                    return False

        # If no includes are specified, everything non-excluded passes
        if not self.include_patterns:
            return True

        # Check includes
        for pat in self.include_patterns:
            for cand in candidates:
                if pat.search(cand):
                    return True

        return False
