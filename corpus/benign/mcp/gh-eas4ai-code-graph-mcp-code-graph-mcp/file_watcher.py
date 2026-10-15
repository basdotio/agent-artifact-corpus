#!/usr/bin/env python3
"""
Debounced File Watcher for Code Graph MCP

Provides intelligent file system monitoring with debouncing to automatically
trigger graph updates when source files change.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Awaitable, Callable, Optional, Set, Union

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class DebouncedFileWatcher:
    """
    A debounced file system watcher that monitors source code files and triggers
    callbacks when changes are detected, with intelligent debouncing to prevent
    excessive re-analysis during bulk operations.
    """

    def __init__(
        self,
        project_root: Path,
        callback: Union[Callable[[], None], Callable[[], Awaitable[None]]],
        debounce_delay: float = 2.0,
        should_ignore_path: Optional[Callable[[Path, Path], bool]] = None,
        supported_extensions: Optional[Set[str]] = None,
    ):
        """
        Initialize the debounced file watcher.

        Args:
            project_root: Root directory to watch
            callback: Function to call when files change (sync or async)
            debounce_delay: Delay in seconds before triggering callback
            should_ignore_path: Function to check if a path should be ignored
            supported_extensions: Set of file extensions to watch
        """
        self.project_root = project_root
        self.callback = callback
        self.debounce_delay = debounce_delay
        self.should_ignore_path = should_ignore_path
        self.supported_extensions = supported_extensions or set()

        self._observer: Optional[Observer] = None
        self._debounce_task: Optional[asyncio.Task] = None
        self._last_change_time = 0
        self._is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Track recent changes to avoid duplicate processing
        self._recent_changes: Set[str] = set()
        self._change_cleanup_timer: Optional[float] = None

    class _EventHandler(FileSystemEventHandler):
        """Internal event handler for file system events."""

        def __init__(self, watcher: "DebouncedFileWatcher"):
            self.watcher = watcher
            super().__init__()

        def on_modified(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self.watcher._handle_file_change(Path(event.src_path))

        def on_created(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self.watcher._handle_file_change(Path(event.src_path))

        def on_deleted(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self.watcher._handle_file_change(Path(event.src_path))

        def on_moved(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                # Handle both source and destination for moves
                self.watcher._handle_file_change(Path(event.src_path))
                if hasattr(event, 'dest_path'):
                    self.watcher._handle_file_change(Path(event.dest_path))

    def _should_watch_file(self, file_path: Path) -> bool:
        """Check if a file should be watched based on extension and ignore rules."""
        try:
            # Check if path should be ignored (e.g., .gitignore rules)
            if self.should_ignore_path and self.should_ignore_path(file_path, self.project_root):
                return False

            # Check file extension
            if self.supported_extensions and file_path.suffix.lower() not in self.supported_extensions:
                return False

            # Skip temporary files and common non-source files
            if file_path.name.startswith('.') or file_path.name.endswith('~'):
                return False

            # Skip common temporary file patterns
            temp_patterns = {'.tmp', '.temp', '.swp', '.swo', '.bak', '.orig'}
            if any(file_path.name.endswith(pattern) for pattern in temp_patterns):
                return False

            return True

        except Exception as e:
            logger.debug(f"Error checking if file should be watched: {file_path}: {e}")
            return False

    def _handle_file_change(self, file_path: Path) -> None:
        """Handle a file system change event."""
        if not self._should_watch_file(file_path):
            return

        # Convert to string for set operations
        file_str = str(file_path)

        # Clean up old changes first
        self._cleanup_recent_changes_if_needed()

        # Skip if we've recently processed this file
        if file_str in self._recent_changes:
            return

        # Add to recent changes and schedule cleanup
        self._recent_changes.add(file_str)
        self._schedule_change_cleanup()

        logger.debug(f"File change detected: {file_path}")
        self._last_change_time = time.time()

        # Cancel existing debounce task and start a new one
        if self._loop and self._loop.is_running():
            if self._debounce_task and not self._debounce_task.done():
                self._debounce_task.cancel()

            # Schedule the debounced callback in the main event loop
            self._loop.call_soon_threadsafe(self._create_debounce_task)

    def _create_debounce_task(self) -> None:
        """Create the debounce task in the main event loop."""
        self._debounce_task = asyncio.create_task(self._debounced_callback())

    def _schedule_change_cleanup(self) -> None:
        """Schedule cleanup of recent changes tracking."""
        # Use a simple timer instead of async task
        self._change_cleanup_timer = time.time() + 10.0  # Clear after 10 seconds

    def _cleanup_recent_changes_if_needed(self) -> None:
        """Clean up recent changes if enough time has passed."""
        if (self._change_cleanup_timer and
            time.time() > self._change_cleanup_timer):
            # Log cleanup for monitoring
            changes_count = len(self._recent_changes)
            self._recent_changes.clear()
            self._change_cleanup_timer = None
            if changes_count > 0:
                logger.debug(f"File watcher cleanup: cleared {changes_count} recent changes")

    async def _debounced_callback(self) -> None:
        """Execute the callback after the debounce delay."""
        try:
            await asyncio.sleep(self.debounce_delay)

            # Double-check that enough time has passed since the last change
            time_since_change = time.time() - self._last_change_time
            if time_since_change < self.debounce_delay:
                # More changes occurred, wait a bit more
                remaining_delay = self.debounce_delay - time_since_change
                await asyncio.sleep(remaining_delay)

            logger.info(f"Triggering callback after {self.debounce_delay}s debounce delay")

            # Handle both sync and async callbacks
            result = self.callback()
            if asyncio.iscoroutine(result):
                await result

        except asyncio.CancelledError:
            logger.debug("Debounced callback cancelled")
            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            logger.error(f"Error in debounced callback: {e}")
            # Don't re-raise to prevent crashing the file watcher

    async def start(self) -> None:
        """Start watching for file changes."""
        if self._is_running:
            logger.warning("File watcher is already running")
            return

        try:
            # Store the current event loop
            self._loop = asyncio.get_running_loop()

            self._observer = Observer()
            event_handler = self._EventHandler(self)

            # Watch the project root recursively
            self._observer.schedule(
                event_handler,
                str(self.project_root),
                recursive=True
            )

            self._observer.start()
            self._is_running = True

            logger.info(f"Started file watcher for: {self.project_root}")

        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop watching for file changes."""
        if not self._is_running:
            return

        logger.info("Stopping file watcher...")

        # Cancel debounce task
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
            try:
                await self._debounce_task
            except asyncio.CancelledError:
                pass

        # Clear cleanup timer
        self._change_cleanup_timer = None

        # Stop observer
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)  # Wait up to 5 seconds
            self._observer = None

        self._is_running = False
        self._recent_changes.clear()
        self._loop = None
        logger.info("File watcher stopped")

    @property
    def is_running(self) -> bool:
        """Check if the file watcher is currently running."""
        return self._is_running

    def get_stats(self) -> dict:
        """Get statistics about the file watcher."""
        return {
            "is_running": self._is_running,
            "project_root": str(self.project_root),
            "debounce_delay": self.debounce_delay,
            "recent_changes_count": len(self._recent_changes),
            "last_change_time": self._last_change_time,
            "has_pending_callback": self._debounce_task is not None and not self._debounce_task.done(),
        }
