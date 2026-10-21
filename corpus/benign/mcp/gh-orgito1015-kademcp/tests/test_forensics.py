"""Tests for tools.forensics extraction bookkeeping and bounded reads."""

import os
import tempfile

import tools.forensics as fx


def test_extraction_dirs_capped_by_count():
    fx._EXTRACT_DIRS.clear()
    made = [fx._new_extract_dir() for _ in range(13)]
    assert len(fx._EXTRACT_DIRS) <= fx._MAX_EXTRACT_DIRS
    # oldest should have been evicted from disk
    assert not os.path.exists(made[0])
    fx._cleanup_extract_dirs()
    assert len(fx._EXTRACT_DIRS) == 0


def test_atexit_sweep_clears_all():
    fx._EXTRACT_DIRS.clear()
    d = fx._new_extract_dir()
    assert os.path.exists(d)
    fx._cleanup_extract_dirs()
    assert not os.path.exists(d)
    assert fx._EXTRACT_DIRS == []


def test_read_preview_is_bounded():
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.write(b"X" * 100_000)
    tf.close()
    try:
        shown, total = fx._read_preview(tf.name, preview=500)
        assert len(shown) == 500
        assert total == 100_000
    finally:
        os.unlink(tf.name)
