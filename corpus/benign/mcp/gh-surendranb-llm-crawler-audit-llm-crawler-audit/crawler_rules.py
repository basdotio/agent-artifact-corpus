# SPDX-License-Identifier: MIT
"""Core engine for RFC 9309 simulation, llms.txt verification, and markdown mirror auditing."""
from __future__ import annotations

import re
import urllib.parse
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

AI_USER_AGENTS: List[Dict[str, str]] = [
    {
        "name": "GPTBot",
        "operator": "OpenAI",
        "category": "training_and_search",
        "description": "OpenAI crawler for model training and ChatGPT Search indexing",
    },
    {
        "name": "ChatGPT-User",
        "operator": "OpenAI",
        "category": "live_search",
        "description": "User-directed live browsing & real-time search citations",
    },
    {
        "name": "ClaudeBot",
        "operator": "Anthropic",
        "category": "live_search",
        "description": "Anthropic crawler for Claude products and search citations",
    },
    {
        "name": "anthropic-ai",
        "operator": "Anthropic",
        "category": "training",
        "description": "Anthropic model training and corpus crawler",
    },
    {
        "name": "PerplexityBot",
        "operator": "Perplexity AI",
        "category": "live_search",
        "description": "Perplexity AI real-time search indexer and source citation bot",
    },
    {
        "name": "Applebot-Extended",
        "operator": "Apple",
        "category": "training",
        "description": "Apple Intelligence training and Siri answer ingestion",
    },
    {
        "name": "Bytespider",
        "operator": "ByteDance",
        "category": "training",
        "description": "ByteDance TikTok/Douyin LLM training and search crawler",
    },
    {
        "name": "Google-Extended",
        "operator": "Google",
        "category": "training",
        "description": "Google Gemini and Vertex AI training crawler",
    },
    {
        "name": "CCBot",
        "operator": "Common Crawl",
        "category": "training",
        "description": "Common Crawl open web dataset used across open-weights models",
    },
]

class RobotsGroup:
    def __init__(self):
        self.user_agents: List[str] = []
        self.rules: List[Tuple[str, str]] = []  # ('allow' | 'disallow', path)
        self.crawl_delay: Optional[float] = None

class RobotsTxt:
    """RFC 9309 compliant parser and crawler permission simulator."""

    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.groups: List[RobotsGroup] = []
        self.sitemaps: List[str] = []
        self.llm_directives: List[str] = []
        self._parse()

    def _parse(self):
        current_group: Optional[RobotsGroup] = None
        in_directive_section = False

        for raw_line in self.raw_text.splitlines():
            line = raw_line.strip()
            # Catch comments that might reference llms.txt or AI policies
            if line.startswith("#"):
                comment = line[1:].strip()
                if any(k in comment.lower() for k in ("llm", "ai", "llms.txt")):
                    self.llm_directives.append(comment)
                continue

            # Strip inline comments
            if "#" in line:
                line = line.split("#", 1)[0].strip()

            if not line:
                if current_group and current_group.user_agents and current_group.rules:
                    self.groups.append(current_group)
                    current_group = None
                    in_directive_section = False
                continue

            if ":" not in line:
                continue

            field, value = line.split(":", 1)
            field = field.strip().lower()
            value = value.strip()

            if field == "user-agent":
                if in_directive_section or current_group is None:
                    if current_group and current_group.user_agents and (current_group.rules or current_group.crawl_delay is not None):
                        self.groups.append(current_group)
                    current_group = RobotsGroup()
                    in_directive_section = False
                current_group.user_agents.append(value)
            elif field in ("allow", "disallow"):
                if current_group is None:
                    continue
                in_directive_section = True
                current_group.rules.append((field, value))
            elif field == "crawl-delay":
                if current_group is None:
                    continue
                in_directive_section = True
                try:
                    current_group.crawl_delay = float(value)
                except ValueError:
                    pass
            elif field == "sitemap":
                if value and value not in self.sitemaps:
                    self.sitemaps.append(value)

        if current_group and current_group.user_agents:
            self.groups.append(current_group)

    @staticmethod
    def _path_matches(pattern: str, path: str) -> bool:
        if not pattern:
            return False
        # RFC 9309 pattern matching: * matches anything, $ matches end
        regex_pattern = "^"
        i = 0
        while i < len(pattern):
            c = pattern[i]
            if c == "*":
                regex_pattern += ".*"
            elif c == "$":
                if i == len(pattern) - 1:
                    regex_pattern += "$"
                else:
                    regex_pattern += re.escape(c)
            else:
                regex_pattern += re.escape(c)
            i += 1
        return re.match(regex_pattern, path) is not None

    def simulate_agent(self, agent_name: str, path: str = "/") -> Dict[str, Any]:
        """Simulate crawler permissions for a specific agent under RFC 9309 rules."""
        target_group: Optional[RobotsGroup] = None
        matched_token: Optional[str] = None

        # 1. Look for specific user-agent group (case-insensitive)
        for group in self.groups:
            for ua in group.user_agents:
                if ua.lower() == agent_name.lower():
                    target_group = group
                    matched_token = ua
                    break
            if target_group:
                break

        # 2. Fall back to wildcard '*' group if no specific group matched
        if not target_group:
            for group in self.groups:
                for ua in group.user_agents:
                    if ua == "*":
                        target_group = group
                        matched_token = "*"
                        break
                if target_group:
                    break

        # 3. If no matching group, default is ALLOW unspecified
        if not target_group:
            return {
                "agent": agent_name,
                "status": "allowed",
                "matched_group": "none",
                "rule_type": "default_allow",
                "rule_pattern": None,
                "crawl_delay": None,
            }

        # 4. Longest match rule in RFC 9309 section 2.2.2
        best_rule_type: Optional[str] = None
        best_pattern: Optional[str] = None
        best_len = -1

        for rule_type, pattern in target_group.rules:
            # Empty disallow means allow all
            if rule_type == "disallow" and not pattern:
                rule_type = "allow"
                pattern = "/"

            if self._path_matches(pattern, path):
                pat_len = len(pattern)
                if pat_len > best_len:
                    best_len = pat_len
                    best_rule_type = rule_type
                    best_pattern = pattern
                elif pat_len == best_len and rule_type == "allow" and best_rule_type == "disallow":
                    # Tie-breaker: Allow wins
                    best_rule_type = "allow"
                    best_pattern = pattern

        if best_rule_type == "disallow":
            status = "disallowed"
        else:
            status = "allowed"

        return {
            "agent": agent_name,
            "status": status,
            "matched_group": matched_token,
            "rule_type": best_rule_type or "implicit_allow",
            "rule_pattern": best_pattern,
            "crawl_delay": target_group.crawl_delay,
        }

class HeadLinkParser(HTMLParser):
    """Extracts alternate link tags from HTML head."""

    def __init__(self):
        super().__init__()
        self.in_head = False
        self.alternate_markdown_links: List[str] = []
        self.describedby_links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        ltag = tag.lower()
        if ltag == "head":
            self.in_head = True
        elif ltag == "link":
            attr_dict = {k.lower(): (v or "") for k, v in attrs}
            rel = attr_dict.get("rel", "").lower()
            href = attr_dict.get("href", "")
            type_attr = attr_dict.get("type", "").lower()

            if "alternate" in rel and type_attr in ("text/markdown", "text/x-markdown"):
                if href and href not in self.alternate_markdown_links:
                    self.alternate_markdown_links.append(href)
            if "describedby" in rel:
                if href and href not in self.describedby_links:
                    self.describedby_links.append(href)

    def handle_endtag(self, tag: str):
        if tag.lower() == "head":
            self.in_head = False

def parse_link_headers(link_header: str) -> List[Dict[str, str]]:
    """Parse HTTP Link header values (RFC 8288)."""
    results: List[Dict[str, str]] = []
    if not link_header:
        return results

    parts = link_header.split(",")
    for part in parts:
        segments = part.strip().split(";")
        if not segments:
            continue
        url_match = re.match(r"<([^>]+)>", segments[0].strip())
        if not url_match:
            continue
        target_url = url_match.group(1)
        params: Dict[str, str] = {"url": target_url}
        for seg in segments[1:]:
            if "=" in seg:
                k, v = seg.strip().split("=", 1)
                params[k.strip().lower()] = v.strip().strip('"\'')
        results.append(params)
    return results

def validate_llms_txt_content(content: str) -> Dict[str, Any]:
    """Validate structure, H1, blockquote, and links according to llmstxt.org."""
    lines = [line.strip() for line in content.splitlines()]
    non_empty = [line for line in lines if line]

    h1_title: Optional[str] = None
    summary_block: Optional[str] = None
    sections: List[str] = []
    links: List[Dict[str, str]] = []

    # First non-empty line should be H1
    if non_empty and non_empty[0].startswith("# "):
        h1_title = non_empty[0][2:].strip()

    # Look for blockquote summary (> ...)
    for line in non_empty[1:6]:
        if line.startswith(">"):
            summary_block = line.lstrip("> ").strip()
            break

    # Extract sections and structured markdown links
    link_regex = re.compile(r"-\s*\[([^\]]+)\]\(([^)]+)\)(?::\s*(.*))?")
    for line in lines:
        if line.startswith("## "):
            sections.append(line[3:].strip())
        else:
            m = link_regex.match(line)
            if m:
                links.append({
                    "title": m.group(1).strip(),
                    "url": m.group(2).strip(),
                    "description": (m.group(3) or "").strip(),
                })

    has_h1 = bool(h1_title)
    has_summary = bool(summary_block)
    has_links = len(links) > 0

    # Calculate compliance score
    score = 0
    if len(content) > 10:
        score += 40
    if has_h1:
        score += 20
    if has_summary:
        score += 20
    if has_links:
        score += 20

    warnings: List[str] = []
    if not has_h1:
        warnings.append("Missing top-level H1 header (# Title) on first non-empty line")
    if not has_summary:
        warnings.append("Missing blockquote summary (> Description) directly beneath H1")
    if not has_links:
        warnings.append("No structured markdown links (- [Title](url): Description) discovered")

    return {
        "valid": has_h1 and has_summary,
        "compliance_score": score,
        "title": h1_title,
        "summary": summary_block,
        "sections": sections,
        "links_count": len(links),
        "links": links[:10],
        "character_count": len(content),
        "estimated_tokens": max(1, round(len(content) / 4)),
        "warnings": warnings,
    }
