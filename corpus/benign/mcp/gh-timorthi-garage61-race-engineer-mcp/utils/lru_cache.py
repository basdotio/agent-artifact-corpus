from collections import OrderedDict
import pandas


class LRUCache:
    """Thread-unsafe in-process LRU cache for parsed telemetry DataFrames."""

    def __init__(self, maxsize: int) -> None:
        self._maxsize = maxsize
        self._data: OrderedDict[str, pandas.DataFrame] = OrderedDict()

    def get(self, key: str) -> pandas.DataFrame | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: pandas.DataFrame) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self._maxsize:
            self._data.popitem(last=False)
