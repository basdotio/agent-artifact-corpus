import pytest
from cli_anything_g_helper.core.memento_state import SessionMemento

def test_session_memento_undo_redo():
    m = SessionMemento(max_depth=10)
    m.mutate({"step": 1})
    m.mutate({"step": 2})
    assert m.current_state == {"step": 2}
    
    prev = m.undo()
    assert prev == {"step": 1}
    
    redo = m.redo()
    assert redo == {"step": 2}

def test_memento_empty_undo():
    m = SessionMemento()
    assert m.undo() is None
