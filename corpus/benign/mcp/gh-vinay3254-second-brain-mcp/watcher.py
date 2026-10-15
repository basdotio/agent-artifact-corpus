import os
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from parser import parse_markdown_file

def get_file_last_modified(file_path: str) -> str:
    """Returns the file's last modified time as a string formatted as YYYY-MM-DD HH:MM:SS."""
    try:
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class VaultHandler(FileSystemEventHandler):
    def __init__(self, graph_db, vector_db, vault_path: str):
        self.graph_db = graph_db
        self.vector_db = vector_db
        self.vault_path = vault_path

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            self._sync_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            self._sync_file(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            # The file is deleted, so we get its title from the filename
            title = os.path.splitext(os.path.basename(event.src_path))[0]
            print(f"[Watcher] File deleted: {event.src_path}. Removing note '{title}' from databases.")
            try:
                self.graph_db.delete_note(title)
                self.vector_db.delete_note(title)
            except Exception as e:
                print(f"[Watcher] Error deleting note '{title}': {e}")

    def _sync_file(self, file_path: str):
        # Wait a short moment to ensure the writing process is fully completed
        time.sleep(0.1)
        if not os.path.exists(file_path):
            return
        
        last_modified = get_file_last_modified(file_path)
        print(f"[Watcher] Syncing file: {file_path} (modified: {last_modified})")
        
        try:
            note = parse_markdown_file(file_path)
            # Sync to Graph Database
            self.graph_db.upsert_note(
                title=note["title"],
                body=note["body"],
                tags=note["tags"],
                last_modified=last_modified,
                wikilinks=note["wikilinks"]
            )
            # Sync to Vector Database
            self.vector_db.index_note(
                title=note["title"],
                body=note["body"],
                tags=note["tags"]
            )
            print(f"[Watcher] Successfully synced: '{note['title']}'")
        except Exception as e:
            print(f"[Watcher] Error syncing file '{file_path}': {e}")


class VaultWatcher:
    def __init__(self, vault_path: str, graph_db, vector_db):
        self.vault_path = os.path.abspath(vault_path)
        self.graph_db = graph_db
        self.vector_db = vector_db
        self.observer = None

    def initial_sync(self):
        """Crawls the entire vault directory and indexes all markdown files."""
        print(f"[Sync] Starting initial synchronization of vault: {self.vault_path}")
        if not os.path.exists(self.vault_path):
            print(f"[Sync] Warning: Vault path does not exist: {self.vault_path}")
            return

        sync_count = 0
        for root, _, files in os.walk(self.vault_path):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    last_modified = get_file_last_modified(file_path)
                    try:
                        note = parse_markdown_file(file_path)
                        self.graph_db.upsert_note(
                            title=note["title"],
                            body=note["body"],
                            tags=note["tags"],
                            last_modified=last_modified,
                            wikilinks=note["wikilinks"]
                        )
                        self.vector_db.index_note(
                            title=note["title"],
                            body=note["body"],
                            tags=note["tags"]
                        )
                        sync_count += 1
                    except Exception as e:
                        print(f"[Sync] Error indexing file '{file_path}': {e}")
        
        print(f"[Sync] Initial synchronization completed. Indexed {sync_count} notes.")

    def start(self):
        """Starts monitoring the vault directory for live changes."""
        if not os.path.exists(self.vault_path):
            print(f"[Watcher] Cannot start watcher: Vault path does not exist: {self.vault_path}")
            return

        event_handler = VaultHandler(self.graph_db, self.vector_db, self.vault_path)
        self.observer = Observer()
        self.observer.schedule(event_handler, path=self.vault_path, recursive=True)
        self.observer.start()
        print(f"[Watcher] Live file monitoring started for: {self.vault_path}")

    def stop(self):
        """Stops the watcher observer thread."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            print("[Watcher] Live file monitoring stopped.")
