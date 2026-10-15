import kuzu
import threading
import re
from contextlib import contextmanager

class GraphDB:
    def __init__(self, db_path: str):
        self.db = kuzu.Database(db_path)
        self.lock = threading.Lock()
        self._init_schema()

    @contextmanager
    def get_conn(self):
        """Context manager to obtain a connection."""
        conn = kuzu.Connection(self.db)
        try:
            yield conn
        finally:
            # Connections are cleaned up automatically
            pass

    def _init_schema(self):
        """Initializes tables if they do not exist."""
        with self.lock:
            with self.get_conn() as conn:
                try:
                    conn.execute("CREATE NODE TABLE Note (title STRING, body STRING, tags STRING[], last_modified STRING, PRIMARY KEY (title))")
                except Exception:
                    # Table already exists
                    pass

                try:
                    conn.execute("CREATE REL TABLE Links (FROM Note TO Note)")
                except Exception:
                    # Relationship already exists
                    pass

    def upsert_note(self, title: str, body: str, tags: list[str], last_modified: str, wikilinks: list[str]):
        """Upserts a note and updates its outgoing relationships."""
        with self.lock:
            with self.get_conn() as conn:
                # 1. Check if the note node already exists
                res = conn.execute("MATCH (n:Note) WHERE n.title = $title RETURN count(n)", {"title": title})
                exists = False
                if res.has_next():
                    exists = res.get_next()[0] > 0

                # 2. Insert or update the note node
                if exists:
                    conn.execute(
                        "MATCH (n:Note) WHERE n.title = $title SET n.body = $body, n.tags = $tags, n.last_modified = $last_modified",
                        {"title": title, "body": body, "tags": tags, "last_modified": last_modified}
                    )
                else:
                    conn.execute(
                        "CREATE (:Note {title: $title, body: $body, tags: $tags, last_modified: $last_modified})",
                        {"title": title, "body": body, "tags": tags, "last_modified": last_modified}
                    )

                # 3. Clean up existing outgoing Links relationships
                conn.execute("MATCH (a:Note)-[r:Links]->(b:Note) WHERE a.title = $title DELETE r", {"title": title})

                # 4. Handle wikilinks
                for target in wikilinks:
                    if target == title:
                        continue
                    
                    # Ensure target node exists (as a placeholder if it doesn't already)
                    target_res = conn.execute("MATCH (n:Note) WHERE n.title = $target RETURN count(n)", {"target": target})
                    target_exists = False
                    if target_res.has_next():
                        target_exists = target_res.get_next()[0] > 0

                    if not target_exists:
                        # Insert a placeholder node
                        conn.execute(
                            "CREATE (:Note {title: $target, body: '', tags: [], last_modified: ''})",
                            {"target": target}
                        )

                    # Create the Links relationship
                    try:
                        conn.execute(
                            "MATCH (a:Note), (b:Note) WHERE a.title = $source AND b.title = $target CREATE (a)-[:Links]->(b)",
                            {"source": title, "target": target}
                        )
                    except Exception:
                        # Skip if there's any duplicate link creation error
                        pass

    def delete_note(self, title: str):
        """Deletes a note and all its connected relationships."""
        with self.lock:
            with self.get_conn() as conn:
                conn.execute("MATCH (n:Note) WHERE n.title = $title DETACH DELETE n", {"title": title})

    def get_note(self, title: str) -> dict | None:
        """Retrieves a note's properties along with outgoing links and incoming backlinks."""
        with self.lock:
            with self.get_conn() as conn:
                # Get node properties
                res = conn.execute(
                    "MATCH (n:Note) WHERE n.title = $title RETURN n.body, n.tags, n.last_modified",
                    {"title": title}
                )
                if not res.has_next():
                    return None
                
                row = res.get_next()
                body, tags, last_modified = row[0], row[1], row[2]

                # Get outgoing links
                links_res = conn.execute(
                    "MATCH (a:Note)-[:Links]->(b:Note) WHERE a.title = $title RETURN b.title",
                    {"title": title}
                )
                links = []
                while links_res.has_next():
                    links.append(links_res.get_next()[0])

                # Get incoming backlinks
                backlinks_res = conn.execute(
                    "MATCH (b:Note)-[:Links]->(a:Note) WHERE a.title = $title RETURN b.title",
                    {"title": title}
                )
                backlinks = []
                while backlinks_res.has_next():
                    backlinks.append(backlinks_res.get_next()[0])

                return {
                    "title": title,
                    "body": body,
                    "tags": tags,
                    "last_modified": last_modified,
                    "links": links,
                    "backlinks": backlinks
                }

    def find_related(self, title: str) -> list[str]:
        """Finds 1-hop and 2-hop related note titles in the graph."""
        with self.lock:
            with self.get_conn() as conn:
                try:
                    res = conn.execute(
                        "MATCH (a:Note)-[:Links*1..2]-(b:Note) WHERE a.title = $title AND b.title <> $title RETURN DISTINCT b.title",
                        {"title": title}
                    )
                    related = []
                    while res.has_next():
                        related.append(res.get_next()[0])
                    return related
                except Exception:
                    # Fallback to manual 1-hop + 2-hop if variable-length path query fails
                    related = set()
                    # 1-hop outgoing
                    r1_out = conn.execute("MATCH (a:Note {title: $title})-[:Links]->(b:Note) RETURN b.title", {"title": title})
                    while r1_out.has_next():
                        related.add(r1_out.get_next()[0])
                    # 1-hop incoming
                    r1_in = conn.execute("MATCH (b:Note)-[:Links]->(a:Note {title: $title}) RETURN b.title", {"title": title})
                    while r1_in.has_next():
                        related.add(r1_in.get_next()[0])
                    
                    # 2-hop
                    hop1_list = list(related)
                    for h1 in hop1_list:
                        # Outgoing from h1
                        r2_out = conn.execute("MATCH (a:Note {title: $h1})-[:Links]->(b:Note) RETURN b.title", {"h1": h1})
                        while r2_out.has_next():
                            t = r2_out.get_next()[0]
                            if t != title:
                                related.add(t)
                        # Incoming to h1
                        r2_in = conn.execute("MATCH (b:Note)-[:Links]->(a:Note {title: $h1}) RETURN b.title", {"h1": h1})
                        while r2_in.has_next():
                            t = r2_in.get_next()[0]
                            if t != title:
                                related.add(t)
                    return sorted(list(related))

    def list_all_notes(self) -> list[dict]:
        """Returns all notes in the vault with title, tags, and last_modified."""
        with self.lock:
            with self.get_conn() as conn:
                res = conn.execute(
                    "MATCH (n:Note) RETURN n.title, n.tags, n.last_modified ORDER BY n.last_modified DESC"
                )
                notes = []
                while res.has_next():
                    row = res.get_next()
                    notes.append({
                        "title": row[0],
                        "tags": row[1],
                        "last_modified": row[2]
                    })
                return notes

    def get_daily_context(self, date_str: str) -> list[dict]:
        """Returns notes tagged with that date or modified on that day."""
        with self.lock:
            with self.get_conn() as conn:
                res = conn.execute(
                    "MATCH (n:Note) RETURN n.title, n.body, n.tags, n.last_modified"
                )
                results = []
                while res.has_next():
                    row = res.get_next()
                    n_title, n_body, n_tags, n_last_modified = row[0], row[1], row[2], row[3]
                    
                    is_match = False
                    # Check tags
                    if n_tags and any(date_str in tag for tag in n_tags):
                        is_match = True
                    # Check last_modified (format: YYYY-MM-DD)
                    elif n_last_modified and date_str in n_last_modified:
                        is_match = True
                        
                    if is_match:
                        results.append({
                            "title": n_title,
                            "body": n_body,
                            "tags": n_tags,
                            "last_modified": n_last_modified
                        })
                return results

    def list_tags(self) -> list[dict]:
        """Returns all unique tags across the vault with note counts, sorted by count descending."""
        with self.lock:
            with self.get_conn() as conn:
                res = conn.execute("MATCH (n:Note) RETURN n.tags")
                tag_counts: dict[str, int] = {}
                while res.has_next():
                    row = res.get_next()
                    tags = row[0] or []
                    for tag in tags:
                        if tag:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
                return [
                    {"tag": tag, "count": count}
                    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
                ]

    def search_by_tag(self, tag: str) -> list[dict]:
        """Returns all notes that have the specified tag (case-insensitive match)."""
        with self.lock:
            with self.get_conn() as conn:
                res = conn.execute("MATCH (n:Note) RETURN n.title, n.tags, n.last_modified")
                results = []
                tag_lower = tag.lower().strip()
                while res.has_next():
                    row = res.get_next()
                    n_title, n_tags, n_last_modified = row[0], row[1] or [], row[2]
                    if any(t.lower().strip() == tag_lower for t in n_tags):
                        results.append({
                            "title": n_title,
                            "tags": n_tags,
                            "last_modified": n_last_modified
                        })
                return sorted(results, key=lambda x: x["last_modified"] or "", reverse=True)

    def get_note_stats(self) -> dict:
        """
        Returns vault-wide statistics:
        - total notes, total links, unique tags
        - average note body length (characters)
        - top 10 hub notes (most incoming + outgoing links)
        - top 10 most recently modified notes
        """
        with self.lock:
            with self.get_conn() as conn:
                # Gather all notes
                notes_res = conn.execute(
                    "MATCH (n:Note) RETURN n.title, n.body, n.tags, n.last_modified"
                )
                total_notes = 0
                total_chars = 0
                tag_set: set[str] = set()
                recent_notes: list[dict] = []

                while notes_res.has_next():
                    row = notes_res.get_next()
                    t, body, tags, lm = row[0], row[1] or "", row[2] or [], row[3] or ""
                    total_notes += 1
                    total_chars += len(body)
                    for tag in tags:
                        if tag:
                            tag_set.add(tag)
                    recent_notes.append({"title": t, "last_modified": lm})

                # Count all links
                links_res = conn.execute("MATCH (a:Note)-[:Links]->(b:Note) RETURN count(*)")
                total_links = 0
                if links_res.has_next():
                    total_links = links_res.get_next()[0]

                # Hub notes: count degree (in + out) per note
                degree: dict[str, int] = {}
                deg_res = conn.execute(
                    "MATCH (a:Note)-[:Links]->(b:Note) RETURN a.title, b.title"
                )
                while deg_res.has_next():
                    row = deg_res.get_next()
                    src, tgt = row[0], row[1]
                    degree[src] = degree.get(src, 0) + 1
                    degree[tgt] = degree.get(tgt, 0) + 1

                top_hubs = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:10]

                # Sort recently modified
                recent_sorted = sorted(
                    recent_notes, key=lambda x: x["last_modified"] or "", reverse=True
                )[:10]

                avg_length = round(total_chars / total_notes, 1) if total_notes else 0

                return {
                    "total_notes": total_notes,
                    "total_links": total_links,
                    "unique_tags": len(tag_set),
                    "avg_note_length_chars": avg_length,
                    "top_hub_notes": [{"title": t, "link_count": c} for t, c in top_hubs],
                    "recently_modified": recent_sorted
                }

    def get_orphan_notes(self) -> list[dict]:
        """
        Returns notes that have no incoming or outgoing [[wikilink]] connections —
        completely isolated nodes in the knowledge graph.
        Each result includes title, tags, and last_modified.
        """
        with self.lock:
            with self.get_conn() as conn:
                # Collect all notes that appear in at least one link (as source or target)
                linked_res = conn.execute(
                    "MATCH (a:Note)-[:Links]->(b:Note) RETURN DISTINCT a.title, b.title"
                )
                connected: set[str] = set()
                while linked_res.has_next():
                    row = linked_res.get_next()
                    connected.add(row[0])
                    connected.add(row[1])

                # Return all notes NOT in the connected set
                all_res = conn.execute(
                    "MATCH (n:Note) RETURN n.title, n.tags, n.last_modified"
                )
                orphans = []
                while all_res.has_next():
                    row = all_res.get_next()
                    title, tags, lm = row[0], row[1] or [], row[2] or ""
                    if title not in connected:
                        orphans.append({
                            "title": title,
                            "tags": tags,
                            "last_modified": lm
                        })
                return sorted(orphans, key=lambda x: x["title"])

    def get_unresolved_links(self) -> list[dict]:
        """
        Finds all note titles that are referenced via [[wikilinks]] but do not exist
        as actual files in the vault (their Note node exists as a placeholder with empty last_modified).
        Returns a list of dicts: {"unresolved_title": str, "referenced_by": list[str]}
        """
        with self.lock:
            with self.get_conn() as conn:
                res = conn.execute(
                    "MATCH (src:Note)-[:Links]->(dest:Note) WHERE dest.last_modified = '' RETURN dest.title, src.title"
                )
                mapping = {}
                while res.has_next():
                    row = res.get_next()
                    dest_title, src_title = row[0], row[1]
                    if dest_title not in mapping:
                        mapping[dest_title] = []
                    mapping[dest_title].append(src_title)
                
                return [
                    {"unresolved_title": dest, "referenced_by": sorted(sources)}
                    for dest, sources in sorted(mapping.items())
                ]

    def get_link_suggestions(self, target_title: str) -> list[dict]:
        """
        Finds notes that mention `target_title` in their text but do not currently link to it.
        Returns a list of dicts: {"source_title": str, "context": str}
        """
        with self.lock:
            with self.get_conn() as conn:
                # 1. Get notes that already link to target_title
                linked_res = conn.execute(
                    "MATCH (src:Note)-[:Links]->(dest:Note) WHERE dest.title = $target RETURN src.title",
                    {"target": target_title}
                )
                already_linked = set()
                while linked_res.has_next():
                    already_linked.add(linked_res.get_next()[0])

                # 2. Get all notes (title and body)
                notes_res = conn.execute(
                    "MATCH (n:Note) RETURN n.title, n.body"
                )
                suggestions = []
                pattern = re.compile(r'\b' + re.escape(target_title) + r'\b', re.IGNORECASE)
                
                while notes_res.has_next():
                    row = notes_res.get_next()
                    title, body = row[0], row[1] or ""
                    if title == target_title or title in already_linked:
                        continue
                    
                    match = pattern.search(body)
                    if match:
                        # Extract a snippet around the match
                        start = max(0, match.start() - 60)
                        end = min(len(body), match.end() + 60)
                        snippet = body[start:end].strip()
                        if start > 0:
                            snippet = "..." + snippet
                        if end < len(body):
                            snippet = snippet + "..."
                            
                        suggestions.append({
                            "source_title": title,
                            "context": snippet
                        })
                return suggestions


