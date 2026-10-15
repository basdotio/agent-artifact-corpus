import os
import re
import atexit
from fastmcp import FastMCP

from graph import GraphDB
from vector import VectorDB
from watcher import VaultWatcher

# Setup FastMCP server
mcp = FastMCP("Second Brain")

# Setup project directories for database storage
project_dir = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.join(project_dir, ".db_data")
os.makedirs(db_dir, exist_ok=True)

kuzu_dir = os.path.join(db_dir, "kuzu")
chroma_dir = os.path.join(db_dir, "chroma")

# Initialize DB wrappers
graph_db = GraphDB(kuzu_dir)
vector_db = VectorDB(chroma_dir)

# Read vault path from environment variable or default to local directory
vault_path = os.getenv("VAULT_PATH")
if not vault_path:
    print("[Server] Warning: VAULT_PATH environment variable is not set. Defaulting to local './vault' folder.")
    vault_path = os.path.abspath("./vault")
    os.makedirs(vault_path, exist_ok=True)
else:
    vault_path = os.path.abspath(vault_path)

# Initialize and start vault file watcher
watcher = VaultWatcher(vault_path, graph_db, vector_db)
watcher.initial_sync()
watcher.start()

# Ensure background watchdog threads are stopped clean on server exit
atexit.register(watcher.stop)


@mcp.tool()
def search_notes(query: str) -> list[dict]:
    """
    Performs semantic search across all note contents in the vault using ChromaDB.
    Returns the top-5 most relevant unique notes.
    """
    return vector_db.search_notes(query, top_n=5)


@mcp.tool()
def list_all_notes() -> list[dict]:
    """
    Returns all notes stored in the vault, ordered by last-modified date (newest first).
    Each entry contains: title, tags, and last_modified timestamp.
    """
    return graph_db.list_all_notes()


@mcp.tool()
def get_note(title: str) -> dict:
    """
    Retrieves the full content, tags, outgoing links, and incoming backlinks for a specific note from the graph.
    """
    note = graph_db.get_note(title)
    if not note:
        return {"error": f"Note '{title}' not found in second brain."}
    return note


@mcp.tool()
def find_related(title: str) -> list[str]:
    """
    Finds 1-hop and 2-hop related notes for a specific note title using graph traversal.
    """
    return graph_db.find_related(title)


@mcp.tool()
def list_tags() -> list[dict]:
    """
    Returns all unique tags used across the vault, each with a note count.
    Results are sorted by usage count (most-used tags first).
    """
    return graph_db.list_tags()


@mcp.tool()
def search_by_tag(tag: str) -> list[dict]:
    """
    Returns all notes that carry the specified tag (case-insensitive).
    Each result includes the note title, its full tag list, and last_modified date.
    """
    return graph_db.search_by_tag(tag)


@mcp.tool()
def get_note_stats() -> dict:
    """
    Returns vault-wide statistics including:
    - total_notes: number of notes indexed
    - total_links: number of [[wikilink]] relationships
    - unique_tags: number of distinct tags
    - avg_note_length_chars: average note body size in characters
    - top_hub_notes: top 10 most-connected notes (highest in+out link count)
    - recently_modified: top 10 most recently changed notes
    """
    return graph_db.get_note_stats()


@mcp.tool()
def surface_contradictions(topic: str) -> list[dict]:
    """
    Finds notes with conflicting statements on a given topic using local semantic search and NLI/lexical checks.
    """
    # 1. Search for topic relevant chunks
    search_results = vector_db.search_notes(topic, top_n=10)
    if not search_results:
        return []

    # 2. Split chunks into sentences
    def split_sentences(text: str) -> list[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 12]

    sentences_by_note = {}
    for res in search_results:
        note_title = res["title"]
        content = res["content"]
        sentences = split_sentences(content)
        if sentences:
            if note_title not in sentences_by_note:
                sentences_by_note[note_title] = []
            sentences_by_note[note_title].extend(sentences)

    note_titles = list(sentences_by_note.keys())
    if len(note_titles) < 2:
        return []

    contradictions = []

    # Try to load local NLI cross-encoder
    tokenizer = None
    model = None
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        model_name = "cross-encoder/nli-MiniLM2-L6-H768"
        
        global _nli_tokenizer, _nli_model
        if '_nli_tokenizer' not in globals():
            print("[Contradiction] Loading NLI model locally...")
            _nli_tokenizer = AutoTokenizer.from_pretrained(model_name)
            _nli_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
        tokenizer = _nli_tokenizer
        model = _nli_model
        
        label2id = model.config.label2id
        contra_idx = None
        for lbl, idx in label2id.items():
            if "contradict" in lbl.lower():
                contra_idx = idx
                break
        if contra_idx is None:
            contra_idx = 0
    except Exception as e:
        print(f"[Contradiction] Could not load NLI model (will use Jaccard negation fallback): {e}")

    # Compare sentences from different notes
    for i in range(len(note_titles)):
        for j in range(i + 1, len(note_titles)):
            title_a = note_titles[i]
            title_b = note_titles[j]
            
            for s_a in sentences_by_note[title_a]:
                for s_b in sentences_by_note[title_b]:
                    if tokenizer and model:
                        try:
                            inputs = tokenizer(s_a, s_b, return_tensors="pt", truncation=True)
                            with torch.no_grad():
                                logits = model(**inputs).logits
                            probs = torch.softmax(logits, dim=1)[0]
                            contra_prob = float(probs[contra_idx])
                            
                            if contra_prob > 0.7:  # Contradiction threshold
                                contradictions.append({
                                    "note_a": title_a,
                                    "note_b": title_b,
                                    "statement_a": s_a,
                                    "statement_b": s_b,
                                    "confidence": contra_prob,
                                    "method": "NLI Model"
                                })
                        except Exception:
                            pass
                    else:
                        # Fallback Lexical Jaccard Negation Heuristic
                        words_a = set(re.findall(r'\b\w+\b', s_a.lower()))
                        words_b = set(re.findall(r'\b\w+\b', s_b.lower()))
                        
                        stop_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "at", "by", "with", "this", "that", "it"}
                        words_a = words_a - stop_words
                        words_b = words_b - stop_words
                        
                        if not words_a or not words_b:
                            continue
                            
                        intersection = words_a.intersection(words_b)
                        union = words_a.union(words_b)
                        jaccard = len(intersection) / len(union)
                        
                        # High semantic/lexical overlap in subjects
                        if jaccard > 0.4:
                            negations = {"not", "never", "no", "fails", "refutes", "contradicts", "doesn't", "don't", "won't", "isn't", "aren't"}
                            has_neg_a = any(w in negations for w in words_a)
                            has_neg_b = any(w in negations for w in words_b)
                            
                            if has_neg_a != has_neg_b:
                                contradictions.append({
                                    "note_a": title_a,
                                    "note_b": title_b,
                                    "statement_a": s_a,
                                    "statement_b": s_b,
                                    "confidence": 0.8,
                                    "method": "Lexical Negation Fallback"
                                })

    # Sort results by confidence descending
    contradictions = sorted(contradictions, key=lambda x: x['confidence'], reverse=True)
    return contradictions


@mcp.tool()
def daily_context(date: str) -> list[dict]:
    """
    Returns notes tagged with that date or modified on that day.
    Input date format: YYYY-MM-DD.
    """
    return graph_db.get_daily_context(date)


@mcp.tool()
def create_note(title: str, body: str, tags: list[str] = None, wikilinks: list[str] = None) -> dict:
    """
    Creates a new markdown note in the vault with optional YAML frontmatter tags and wikilink mentions.
    The file watcher will automatically index the note into the graph and vector databases.
    Returns an error if a note with the same title already exists.

    Args:
        title: The note title (also used as filename).
        body: The main content of the note.
        tags: Optional list of tags to include in the YAML frontmatter.
        wikilinks: Optional list of note titles to reference as [[wikilinks]] at the end of the body.
    """
    tags = tags or []
    wikilinks = wikilinks or []

    # Sanitize title for use as a filename
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title).strip()
    file_path = os.path.join(vault_path, f"{safe_title}.md")

    if os.path.exists(file_path):
        return {"error": f"A note named '{title}' already exists in the vault."}

    # Build YAML frontmatter
    frontmatter_lines = ["---", f"title: \"{title}\""]
    if tags:
        tag_str = ", ".join(f'"{t}"' for t in tags)
        frontmatter_lines.append(f"tags: [{tag_str}]")
    frontmatter_lines.append("---")
    frontmatter_block = "\n".join(frontmatter_lines)

    # Append wikilinks section if provided
    wikilink_section = ""
    if wikilinks:
        links_formatted = "  ".join(f"[[{link}]]" for link in wikilinks)
        wikilink_section = f"\n\n---\nRelated: {links_formatted}"

    full_content = f"{frontmatter_block}\n\n{body}{wikilink_section}\n"

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        return {
            "status": "created",
            "title": title,
            "file": file_path,
            "tags": tags,
            "wikilinks": wikilinks
        }
    except Exception as e:
        return {"error": f"Failed to write note: {e}"}


@mcp.tool()
def rename_note(old_title: str, new_title: str) -> dict:
    """
    Renames an existing note and updates all [[wikilink]] references to it across the entire vault.
    The renamed file is re-indexed in both the graph and vector databases.

    Args:
        old_title: The current title of the note to rename.
        new_title: The desired new title.
    """
    old_safe = re.sub(r'[<>:"/\\|?*]', '_', old_title).strip()
    new_safe = re.sub(r'[<>:"/\\|?*]', '_', new_title).strip()

    old_path = os.path.join(vault_path, f"{old_safe}.md")
    new_path = os.path.join(vault_path, f"{new_safe}.md")

    if not os.path.exists(old_path):
        return {"error": f"Note '{old_title}' not found in the vault."}
    if os.path.exists(new_path):
        return {"error": f"A note named '{new_title}' already exists in the vault."}

    updated_files = []

    # Walk vault and replace all [[old_title]] references in other markdown files
    for root, _, files in os.walk(vault_path):
        for fname in files:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Match [[old_title]], [[old_title|alias]], [[old_title#section]]
                pattern = re.compile(
                    r'\[\[' + re.escape(old_title) + r'([\]|#])',
                    re.IGNORECASE
                )
                new_content = pattern.sub(f'[[{new_title}' + r'\1', content)
                if new_content != content:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    updated_files.append(os.path.basename(fpath))
            except Exception:
                pass

    # Rename the note file itself
    try:
        os.rename(old_path, new_path)
    except Exception as e:
        return {"error": f"Failed to rename file: {e}"}

    # Remove old note from DBs (watcher will pick up the new file, but we clean up old entry)
    try:
        graph_db.delete_note(old_title)
        vector_db.delete_note(old_title)
    except Exception:
        pass

    return {
        "status": "renamed",
        "old_title": old_title,
        "new_title": new_title,
        "new_file": new_path,
        "references_updated_in": updated_files
    }


@mcp.tool()
def get_orphan_notes() -> list[dict]:
    """
    Returns all notes that have no incoming or outgoing [[wikilink]] connections —
    completely isolated nodes in the knowledge graph.
    Useful for identifying forgotten or disconnected notes that may need linking.
    Each result includes title, tags, and last_modified.
    """
    return graph_db.get_orphan_notes()


@mcp.tool()
def get_unresolved_links() -> list[dict]:
    """
    Finds all note titles that are referenced via [[wikilinks]] but do not exist
    as actual files in the vault (i.e. placeholder/stub notes).
    Returns a list of dicts: {"unresolved_title": str, "referenced_by": list[str]}
    """
    return graph_db.get_unresolved_links()


@mcp.tool()
def get_link_suggestions(target_title: str) -> list[dict]:
    """
    Finds notes that mention the target note title in their text but do not currently link to it.
    Returns a list of suggestion dicts containing:
    - source_title: the title of the note that mentions the target title
    - context: a snippet showing the target title in context
    """
    return graph_db.get_link_suggestions(target_title)


if __name__ == "__main__":
    mcp.run()


