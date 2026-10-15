import os
import json
import re
from datetime import datetime, timezone
import string
import random
from mcp.server.fastmcp import FastMCP

# Initialize the server
mcp = FastMCP(
    "MarkdownCriticReviewer",
    instructions="""
    You are an editorial review assistant using the CriticMarkup MCP server.
    CRITICAL PROTOCOL RULES:
    1. IMMUTABLE DIFFS: CriticMarkup tags ({~~...~~}, {--...--}, {++...++}) are read-only markers 
       reserved strictly for the human author to accept or reject in their editor (e.g., Monoleaf). 
       This is intentional, and included to preserve human governance and accountability.
    2. NEVER REVERT OR CLEAN DIFFS: Never include CriticMarkup delimiters in 'search_string' or 'replacement_string'.
       Do not attempt to undo, revert, clean up, or accept previous edits.
    3. SURGICAL REVISIONS: Keep search and replacement strings minimal (under 15 words). Do not replace whole paragraphs.
    """
)

# --- REGEX & PARSING PATTERNS ---

# Primary pattern: Protects unresolved CriticMarkup and bottom JSON payloads.
PROTECTED_PATTERN = re.compile(
    r'(\{[\+\-\~\=\>]{2}[\s\S]*?[\+\-\~\=\>]{2}\}|<!--c:[a-zA-Z0-9]+\s+\{[\s\S]*?\}\s*-->)'
)

# Comments protect the bottom JSON payloads (allowing comments on CriticMarkup and code)
PROTECTED_PATTERN_COMMENTS = re.compile(
    r'<!--c:[a-zA-Z0-9]+\s+\{[\s\S]*?\}\s*-->'
)

# Inline anchors marking comment highlights: <!--c:id1s--> and <!--c:id1e-->
INLINE_ANCHOR_PATTERN = re.compile(r'<!--c:[a-zA-Z0-9]+[se]-->')

# Trailing JSON comment thread payloads: <!--c:{id} {json}-->
COMMENT_PAYLOAD_RE = re.compile(r'<!--c:([a-zA-Z0-9]+)\s+(\{[\s\S]*?\})\s*-->')


# --- HELPER FUNCTIONS ---

def _load_md(filepath: str) -> str:
    """Validates extension (case-insensitive), existence, and normalizes line endings to \n."""
    if not filepath.lower().endswith(('.md', '.markdown')):
        raise ValueError(f"Access denied: '{filepath}'. Only .md and .markdown files are supported.")
    if not os.path.exists(filepath):
        raise ValueError(f"File not found: '{filepath}'. Please supply a valid absolute path.")
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read().replace('\r\n', '\n')


def _is_in_protected_region(content: str, start_pos: int, end_pos: int) -> bool:
    """Checks if a target string span overlaps with unresolved CriticMarkup or JSON payloads."""
    for match in PROTECTED_PATTERN.finditer(content):
        m_start, m_end = match.span()
        if max(start_pos, m_start) < min(end_pos, m_end):
            return True
    return False


def _is_slicing_anchor(content: str, start_pos: int, end_pos: int) -> bool:
    """Prevents an edit from starting or ending inside an inline anchor tag."""
    for match in INLINE_ANCHOR_PATTERN.finditer(content):
        m_start, m_end = match.span()
        if m_start < start_pos < m_end or m_start < end_pos < m_end:
            return True
    return False


def _get_valid_matches(content: str, search_string: str, allow_critic: bool = False) -> list[tuple[int, int]]:
    """
    Finds all (start, end) spans of search_string that exist strictly 
    OUTSIDE of code blocks and bottom JSON payloads, without bisecting anchors.
    If allow_critic=True, matches inside CriticMarkup are permitted (used for comments).
    """
    if not search_string:
        return []

    pattern = PROTECTED_PATTERN_COMMENTS if allow_critic else PROTECTED_PATTERN
    matches = []
    start = 0
    while True:
        pos = content.find(search_string, start)
        if pos == -1:
            break
        end = pos + len(search_string)

        is_protected = any(
            max(pos, m.start()) < min(end, m.end())
            for m in pattern.finditer(content)
        )
        if not is_protected and not _is_slicing_anchor(content, pos, end):
            matches.append((pos, end))
        start = pos + 1
    return matches


def _apply_single_change(content: str, search_string: str, replacement_string: str) -> str:
    """
    Applies a single search/replace operation with CriticMarkup and anchor preservation.
    Raises ValueError on failure so MCP hosts register a retryable error.
    """
    valid_matches = _get_valid_matches(content, search_string)
    if len(valid_matches) == 0:
        raise ValueError(
            f"Target text '{search_string[:60]}...' not found in editable text. "
            "Ensure exact capitalization/whitespace or supply more surrounding context."
        )
    if len(valid_matches) > 1:
        raise ValueError(
            f"Target text '{search_string[:60]}...' matched {len(valid_matches)} times. "
            "Include more surrounding context words to make the search string unique."
        )

    start_pos, end_pos = valid_matches[0]

    # Extract existing anchors from the target span
    start_anchors = re.findall(r'<!--c:[a-zA-Z0-9]+s-->', search_string)
    end_anchors = re.findall(r'<!--c:[a-zA-Z0-9]+e-->', search_string)

    clean_search = INLINE_ANCHOR_PATTERN.sub('', search_string or '')
    clean_replacement = INLINE_ANCHOR_PATTERN.sub('', replacement_string or '')

    if not clean_search.strip():
        raise ValueError(
            "'search_string' contains no editable text (only anchor tags or whitespace). "
            "Supply the actual words to modify."
        )

    # Reject no-op edits where replacement text is identical to the search text
    if clean_search == clean_replacement:
        raise ValueError(
            f"No-op edit rejected: 'replacement_string' is identical to 'search_string' ('{clean_search}'). "
            "Supply different replacement text or omit the edit."
        )

    # Core CriticMarkup formatting: deletion if replacement is empty, substitution otherwise
    if not clean_replacement:
        critic_body = f"{{--{clean_search}--}}"
    else:
        critic_body = f"{{~~{clean_search}~>{clean_replacement}~~}}"

    # Slide original anchors outward so they wrap around the edit cleanly
    prefix_anchors = "".join(start_anchors)
    suffix_anchors = "".join(end_anchors)
    critic_markup = f"{prefix_anchors}{critic_body}{suffix_anchors}"

    return content[:start_pos] + critic_markup + content[end_pos:]


# --- MCP TOOLS ---

@mcp.tool()
def get_md_contents(filepath: str) -> str:
    """
    Reads a markdown file, returning raw markdown prose alongside an abbreviated summary of 
    discussion comment threads at the bottom instead of bulky raw JSON.
    Inline anchors (<!--c:...s-->) remain in the body text for location context.

    Core Workflow:
    - After inspecting the document, synthesize and bundle ALL desired revisions first.
    - Execute edits together in a single batch using replace_multiple, rather than calling tools one-by-one.

    Use when: You need to inspect the document.
    """
    content = _load_md(filepath)

    comment_blocks = list(COMMENT_PAYLOAD_RE.finditer(content))
    if not comment_blocks:
        return content

    # Strip raw JSON payloads from the file body
    body = COMMENT_PAYLOAD_RE.sub('', content).rstrip()

    # Build concise human-readable summary
    summary_lines = ["\n\n---", "### Comments & Threads:"]
    for match in comment_blocks:
        thread_id = match.group(1)
        try:
            payload = json.loads(match.group(2))
            status = "RESOLVED" if payload.get("resolved") else "OPEN"
            summary_lines.append(f"\nThread [{thread_id}] ({status}):")
            for entry in payload.get("thread", []):
                author = entry.get("author", "Unknown")
                text = entry.get("text", "")
                summary_lines.append(f"  - {author}: {text}")
        except json.JSONDecodeError:
            summary_lines.append(f"\nThread [{thread_id}]: [Corrupted JSON Payload]")

    return body + "\n" + "\n".join(summary_lines)


@mcp.tool()
def replace_multiple(filepath: str, edits: list[dict]) -> str:
    """
    Applies MULTIPLE editorial revisions across different sections in a single call using CriticMarkup.
    Edits are applied bottom-to-top to maintain offset stability across the document.
    
    Intended usage:

    1. Bundle ideas first to minimize token-costly tool calls.
    2. Surgical Precision: Do NOT replace entire paragraphs or large sections for minor corrections.
    Keep 'search_string' and 'replacement_string' strictly minimal—target only the specific phrase or sentence
    being revised, with just enough surrounding words to ensure a unique match. Large block replacements ruin
    granular track-changes review. If a search string matches in multiple places across the file, you will 
    receive an error and can retry with more surrounding context.
    3. Order of Operations: Propose all text revisions (replace_multiple/request_changes) BEFORE adding discussion comments.

    Use when: Making several prose revisions across a chapter or file at once.

    Args:
        filepath: Absolute path to the markdown file.
        edits: List of dicts with 'search_string' (or 'search') and 'replacement_string' (or 'replace').
    """
    content = _load_md(filepath)

    if not edits:
        raise ValueError("No edits supplied in the 'edits' list.")

    applied_count = 0
    failed_edits = []
    planned_edits = []

    # Phase 1: Test each edit and record matches or specific reasons for failure
    for i, edit in enumerate(edits):
        search_str = edit.get("search_string") or edit.get("search") or ""
        replace_str = edit.get("replacement_string") if "replacement_string" in edit else edit.get("replace", "")
        if replace_str is None:
            replace_str = ""

        if not search_str.strip():
            failed_edits.append(f"Edit #{i+1}: 'search_string' was empty or whitespace.")
            continue

        matches = _get_valid_matches(content, search_str)
        if len(matches) == 0:
            failed_edits.append(f"Edit #{i+1}: Target text '{search_str[:50]}...' not found in editable text.")
            continue
        if len(matches) > 1:
            failed_edits.append(f"Edit #{i+1}: Target text '{search_str[:50]}...' matched {len(matches)} times (ambiguous match).")
            continue

        start_pos, end_pos = matches[0]
        planned_edits.append((start_pos, end_pos, search_str, replace_str, i + 1))

    # Phase 2: Check for overlapping spans among successful matches
    planned_edits.sort(key=lambda x: x[0])
    non_overlapping_edits = []
    last_end = -1
    for start_pos, end_pos, search_str, replace_str, idx in planned_edits:
        if start_pos < last_end:
            failed_edits.append(f"Edit #{idx}: Overlapped with an earlier edit in this batch.")
            continue
        non_overlapping_edits.append((start_pos, end_pos, search_str, replace_str))
        last_end = end_pos

    # Phase 3: Apply valid edits in REVERSE order (bottom to top) to maintain offsets
    non_overlapping_edits.sort(key=lambda x: x[0], reverse=True)
    for _, _, search_str, replace_str in non_overlapping_edits:
        content = _apply_single_change(content, search_str, replace_str)
        applied_count += 1

    # Save changes if at least one edit succeeded
    if applied_count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    # Phase 4: Construct technical feedback for the model
    report = [f"Successfully applied {applied_count} of {len(edits)} edits."]
    if failed_edits:
        report.append("\nSkipped edits:")
        for fail in failed_edits:
            report.append(f"- {fail}")
        report.append(
            "\nNote for model: If you still need to apply any of the skipped edits, "
            "call the editing tools again in a separate call based on the updated document state."
        )

    if applied_count == 0 and failed_edits:
        raise ValueError("\n".join(report))

    return "\n".join(report)


@mcp.tool()
def request_changes(filepath: str, search_string: str, replacement_string: str) -> str:
    """
    Applies a single targeted change or deletion to a specific text excerpt using CriticMarkup.
    Automatically detects and preserves any comment anchors in the target span.

    Use when: Making a single, isolated edit or deletion in the document.
    Note: Always propose text changes BEFORE adding comments, so comment anchors do not interfere with search strings.

    Args:
        filepath: Absolute path to the markdown file.
        search_string: Exact text to replace or delete.
        replacement_string: New text to substitute (leave empty for pure deletion).
    """
    content = _load_md(filepath)
    new_content = _apply_single_change(content, search_string, replacement_string)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return "Successfully applied change while preserving comment anchors."


@mcp.tool()
def replace_all(filepath: str, search_string: str, replacement_string: str) -> str:
    """
    Globally replaces ALL instances of a specific word or phrase throughout the document using CriticMarkup.
    Enforces word boundaries (\\b) on alphanumeric words to avoid substring accidents.
    Skips code blocks, links, YAML frontmatter, and existing CriticMarkup.

    Use when: Standardizing terminology, correcting a repeated typo, or renaming a concept everywhere.
    """
    content = _load_md(filepath)

    if not search_string.strip():
        raise ValueError("'search_string' cannot be empty or whitespace.")

    # this regex will find all instances of the search string (INCORRECT: we are not using regex, we use exact string replacement to avoid markdown symbol escaping issues) [ANNOTATION: Reused from previous logic, updated for replacing multiple occurrences globally] [ANNOTATION 2: Now correctly using regex with word boundaries and skip patterns to avoid code blocks/links] [ANNOTATION 3: Updated skip pattern to also preserve existing CriticMarkup blocks] [ANNOTATION 4: Upgraded to PROTECTED_PATTERN to prevent corrupting HTML comment metadata and anchor tags] [ANNOTATION 5: Moved to replace_all tool with smart word boundaries for global term replacement]

    clean_replacement = INLINE_ANCHOR_PATTERN.sub('', replacement_string or '')

    # Reject no-op global edits where replacement is identical to search
    if search_string == clean_replacement:
        raise ValueError(
            f"No-op edit rejected: 'replacement_string' is identical to 'search_string' ('{search_string}'). "
            "Supply different replacement text or omit the edit."
        )

    # Use \b only if search_string starts/ends with alphanumeric characters
    prefix_b = r'\b' if search_string[:1].isalnum() else ''
    suffix_b = r'\b' if search_string[-1:].isalnum() else ''
    target_pattern = prefix_b + re.escape(search_string) + suffix_b

    combined_pattern = re.compile(
        PROTECTED_PATTERN.pattern + r'|(' + target_pattern + r')',
        re.MULTILINE
    )

    matches_found = 0
    def replacer(match: re.Match) -> str:
        nonlocal matches_found
        if match.group(1):
            return match.group(1)  # Protected zone: leave untouched
        matches_found += 1
        return f"{{~~{match.group(2)}~>{clean_replacement}~~}}"

    new_content = combined_pattern.sub(replacer, content)

    if matches_found == 0:
        raise ValueError(f"No instances of '{search_string}' found in editable text.")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return (
        f"Successfully replaced {matches_found} instances of '{search_string}' with '{clean_replacement}' globally using CriticMarkup. "
        f"For all subsequent tool calls in this session, target the updated wording - or when too complex, re-read with get_md_contents."
    )


@mcp.tool()
def write_comment(filepath: str, search_string: str, comment_text: str) -> str:
    """
    Attaches an inline comment anchor around target text and creates an open discussion thread.
    Can anchor to both clean prose and proposed CriticMarkup diffs.
    
    Use when: Leaving feedback, asking questions, or suggesting high-level changes without directly editing the text.
    Note: Always propose text edits (replace_multiple/request_changes) BEFORE adding comments.

    Args:
        filepath: Absolute path to the markdown file.
        search_string: The exact phrase in the document to anchor the comment to.
        comment_text: The feedback, critique, or note to record in the thread.
    """
    content = _load_md(filepath)

    if not search_string.strip():
        raise ValueError("'search_string' cannot be empty or whitespace.")
    if not comment_text.strip():
        raise ValueError("'comment_text' cannot be empty or whitespace.")

    # allow_critic=True enables commenting directly on proposed CriticMarkup revisions
    valid_matches = _get_valid_matches(content, search_string, allow_critic=True)
    if len(valid_matches) == 0:
        raise ValueError(
            f"Comment target '{search_string}' not found in editable text. "
            "Ensure exact capitalization/whitespace or supply more context words."
        )
    if len(valid_matches) > 1:
        raise ValueError(
            f"Comment target '{search_string}' matched {len(valid_matches)} times. "
            "Include more surrounding context to guarantee uniqueness."
        )

    start_pos, end_pos = valid_matches[0]

    # Generate a conflict-safe 4-character ID
    while True:
        candidate_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        if f"<!--c:{candidate_id}" not in content:
            thread_id = candidate_id
            break

    # Sanitize comment text to prevent premature closure of the HTML comment block
    safe_comment_text = comment_text.replace("-->", "->")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    comment_json = {
        "resolved": False,
        "thread": [{"author": "AI AGENT", "ts": ts, "text": safe_comment_text}]
    }

    # 1. Replace target text with inline anchors
    anchor_replacement = f"<!--c:{thread_id}s-->{search_string}<!--c:{thread_id}e-->"
    content = content[:start_pos] + anchor_replacement + content[end_pos:]

    # 2. Append metadata payload to the bottom of the file
    comment_payload = f"\n\n<!--c:{thread_id} {json.dumps(comment_json, separators=(',', ':'))}-->"
    content = content.rstrip() + comment_payload + "\n"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return f"Comment successfully written under Thread ID [{thread_id}]."


@mcp.tool()
def reply_to_comment(filepath: str, thread_id: str, reply_text: str) -> str:
    """
    Replies to an existing discussion thread by its 4-character UID (e.g., 'o1b7').
    
    Use when: Responding to a user's comment or continuing an ongoing review discussion.

    Args:
        filepath: Absolute path to the markdown file.
        thread_id: The 4-character UID of the thread (e.g., 'o1b7').
        reply_text: The message to append to the thread.
    """
    content = _load_md(filepath)

    if not thread_id.strip():
        raise ValueError("'thread_id' cannot be empty or whitespace.")
    if not reply_text.strip():
        raise ValueError("'reply_text' cannot be empty or whitespace.")

    # Strip optional 'c:' prefix and anchor suffix only if 5 chars long (e.g. 'cwa4s' -> 'cwa4')
    clean_id = re.sub(r'^c:', '', thread_id.strip())
    if len(clean_id) == 5 and clean_id[-1].lower() in ('s', 'e'):
        clean_id = clean_id[:-1]
    thread_id = clean_id

    pattern = re.compile(rf'<!--c:{re.escape(thread_id)}\s+(\{{[\s\S]*?\}})\s*-->')
    match = pattern.search(content)

    if not match:
        raise ValueError(f"Comment thread with UID '{thread_id}' not found.")

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        raise ValueError(f"Comment thread '{thread_id}' contains invalid JSON metadata.")

    # Sanitize reply text to prevent premature closure of the HTML comment block
    safe_reply_text = reply_text.replace("-->", "->")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    payload.setdefault("thread", []).append({
        "author": "AI AGENT",
        "ts": ts,
        "text": safe_reply_text
    })

    updated_block = f"<!--c:{thread_id} {json.dumps(payload, separators=(',', ':'))}-->"
    new_content = content[:match.start()] + updated_block + content[match.end():]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return f"Successfully added reply to thread [{thread_id}]."


if __name__ == "__main__":
    mcp.run(transport="stdio")