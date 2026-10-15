"""Make the sibling ``atlas_pca`` package importable without an install.

``atlas-pca-fastmcp`` depends on ``atlas-pca`` (``sdks/python-pca``). In CI that dependency is
installed; for a local in-tree ``pytest`` run we just put the sibling package dir on ``sys.path`` so
the tests need no build step, exactly as ``sdks/python-pca`` runs in-tree.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PYTHON_PCA = os.path.normpath(os.path.join(_HERE, "..", ".."))

for _path in (_HERE, _PYTHON_PCA):
    if _path not in sys.path:
        sys.path.insert(0, _path)
