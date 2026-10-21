"""Session state with Memento-based snapshot undo/redo."""
import copy
from collections import deque
from typing import Any, Dict, Optional

class SessionMemento:
    def __init__(self, max_depth: int = 50):
        self.max_depth = max_depth
        self.current_state: Dict[str, Any] = {}
        self.undo_stack: deque = deque(maxlen=max_depth)
        self.redo_stack: deque = deque(maxlen=max_depth)

    def mutate(self, new_state: Dict[str, Any]):
        self.undo_stack.append(copy.deepcopy(self.current_state))
        self.redo_stack.clear()
        self.current_state = copy.deepcopy(new_state)

    def undo(self) -> Optional[Dict[str, Any]]:
        if not self.undo_stack:
            return None
        self.redo_stack.append(copy.deepcopy(self.current_state))
        self.current_state = self.undo_stack.pop()
        return copy.deepcopy(self.current_state)

    def redo(self) -> Optional[Dict[str, Any]]:
        if not self.redo_stack:
            return None
        self.undo_stack.append(copy.deepcopy(self.current_state))
        self.current_state = self.redo_stack.pop()
        return copy.deepcopy(self.current_state)
