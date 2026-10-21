"""State management and token-saving word-based object store for Integrum."""

import inspect
import random
from typing import Any, Dict, List, Optional, Tuple


ADJECTIVES: List[str] = [
    "playful", "swift", "calm", "clever", "brave", "bright", "gentle", "silent",
    "golden", "cosmic", "frosty", "amber", "emerald", "lively", "agile", "mighty",
    "nimble", "vibrant", "serene", "dapper", "sunny", "quiet", "daring", "eager",
    "fuzzy", "grand", "happy", "jolly", "keen", "lucid", "merry", "noble",
    "polar", "quick", "radiant", "stellar", "tidy", "unique", "valiant", "warm",
    "witty", "zen", "bold", "crisp", "dawn", "fleet", "gleaming", "honest",
    "iron", "jade", "kind", "lunar", "mystic", "nova", "optic", "proud",
]

NOUNS: List[str] = [
    "llama", "falcon", "otter", "badger", "dolphin", "fox", "panda", "tiger",
    "eagle", "sparrow", "wolf", "lynx", "bear", "hawk", "koala", "bison",
    "raven", "crane", "beaver", "puma", "finch", "jaguar", "lemur", "moose",
    "newt", "owl", "quail", "robin", "seal", "swan", "viper", "walrus",
    "yak", "zebra", "comet", "river", "cedar", "coral", "ember", "glacier",
    "haven", "island", "meadow", "oasis", "pebble", "ridge", "shadow", "valley",
]


class WordIdGenerator:
    """Generates memorable, token-efficient word IDs like 'playful_llama'."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._used_ids: set[str] = set()

    def generate(self, prefix: Optional[str] = None) -> str:
        """Generate a unique word ID.
        
        Args:
            prefix: Optional hint prefix, though word pairs are preferred to save tokens.
        """
        for _ in range(500):
            adj = self._rng.choice(ADJECTIVES)
            noun = self._rng.choice(NOUNS)
            word_id = f"{adj}_{noun}"
            if word_id not in self._used_ids:
                self._used_ids.add(word_id)
                return word_id

        # Fallback if dictionary space is heavily populated
        counter = 1
        while True:
            adj = self._rng.choice(ADJECTIVES)
            noun = self._rng.choice(NOUNS)
            word_id = f"{adj}_{noun}_{counter}"
            if word_id not in self._used_ids:
                self._used_ids.add(word_id)
                return word_id
            counter += 1

    def release(self, word_id: str) -> None:
        """Release a word ID back to the generator."""
        self._used_ids.discard(word_id)


class ObjectStore:
    """In-memory multi-session store for Python objects with dot-notation resolution."""

    def __init__(self) -> None:
        # session_id -> {obj_id -> python_object}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        # session_id -> {obj_id -> metadata_dict}
        self._metadata: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._id_generators: Dict[str, WordIdGenerator] = {}

    def _get_generator(self, session_id: str) -> WordIdGenerator:
        if session_id not in self._id_generators:
            self._id_generators[session_id] = WordIdGenerator()
        return self._id_generators[session_id]

    def _ensure_session(self, session_id: str) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = {}
            self._metadata[session_id] = {}

    def register(self, obj: Any, label: Optional[str] = None, session_id: str = "default") -> str:
        """Register an object into the store and return its word ID.
        
        Also generates child references for composite objects (e.g. tuples or bunches).
        """
        self._ensure_session(session_id)
        generator = self._get_generator(session_id)
        obj_id = generator.generate()

        self._sessions[session_id][obj_id] = obj

        # Metadata summary
        type_name = type(obj).__name__
        module_name = getattr(type(obj), "__module__", "")
        full_type = f"{module_name}.{type_name}" if module_name else type_name

        try:
            shape = getattr(obj, "shape", None)
            if shape is not None:
                shape_str = str(shape)
            elif hasattr(obj, "__len__") and not isinstance(obj, (str, bytes)):
                shape_str = f"len={len(obj)}"
            else:
                shape_str = None
        except Exception:
            shape_str = None

        meta: Dict[str, Any] = {
            "type": full_type,
            "label": label or type_name,
            "shape": shape_str,
            "repr": repr(obj)[:120],
        }

        # If object is a tuple/list, register indexed shortcuts
        if isinstance(obj, (tuple, list)):
            item_ids = []
            for idx, item in enumerate(obj):
                child_id = f"{obj_id}_{idx}"
                self._sessions[session_id][child_id] = item
                item_ids.append(child_id)
            meta["items"] = item_ids

        # If object has keys/attributes (e.g. scikit-learn Bunch or dict), record available sub-paths
        if isinstance(obj, dict) or hasattr(obj, "keys"):
            try:
                keys = list(obj.keys())[:10]
                meta["keys"] = keys
            except Exception:
                pass

        self._metadata[session_id][obj_id] = meta
        return obj_id

    def has(self, key: str, session_id: str = "default") -> bool:
        """Check if an object or valid dot-notation path exists."""
        self._ensure_session(session_id)
        if key in self._sessions[session_id]:
            return True
        try:
            self.get(key, session_id=session_id)
            return True
        except KeyError:
            return False

    def get(self, key: str, session_id: str = "default") -> Any:
        """Retrieve an object by key, supporting dot-notation attribute and index access."""
        self._ensure_session(session_id)
        session_store = self._sessions[session_id]

        if key in session_store:
            return session_store[key]

        # Check dot notation e.g. 'playful_llama.data' or index access 'playful_llama[0]'
        if "." in key:
            parts = key.split(".")
            root_id = parts[0]
            if root_id in session_store:
                curr = session_store[root_id]
                for part in parts[1:]:
                    if isinstance(curr, dict) and part in curr:
                        curr = curr[part]
                    elif hasattr(curr, part):
                        curr = getattr(curr, part)
                    else:
                        raise KeyError(f"Attribute or key '{part}' not found on object '{root_id}'")
                return curr

        # Check bracket indexing e.g. 'playful_llama[0]'
        if "[" in key and key.endswith("]"):
            root_id, index_str = key[:-1].split("[", 1)
            if root_id in session_store:
                curr = session_store[root_id]
                try:
                    idx = int(index_str)
                    return curr[idx]
                except (ValueError, IndexError, TypeError) as e:
                    raise KeyError(f"Index [{index_str}] invalid on object '{root_id}': {e}")

        available = list(session_store.keys())
        raise KeyError(
            f"Object '{key}' not found in session '{session_id}'. "
            f"Available objects: {available}"
        )

    def resolve(self, val: Any, session_id: str = "default") -> Any:
        """Resolve a value to an underlying stored object if it references one."""
        if isinstance(val, str):
            # Strip whitespace
            stripped = val.strip()
            # If it's a registered ID or dot-notation path, resolve it
            if self.has(stripped, session_id=session_id):
                return self.get(stripped, session_id=session_id)
        return val

    def list_objects(self, session_id: str = "default") -> Dict[str, Dict[str, Any]]:
        """List summary of all primary objects stored in this session."""
        self._ensure_session(session_id)
        return dict(self._metadata[session_id])

    def delete(self, key: str, session_id: str = "default") -> bool:
        """Delete an object from this session."""
        self._ensure_session(session_id)
        if key in self._sessions[session_id]:
            del self._sessions[session_id][key]
            self._metadata[session_id].pop(key, None)
            self._get_generator(session_id).release(key)
            return True
        return False

    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear objects for a specific session, or all sessions if None."""
        if session_id is not None:
            self._sessions.pop(session_id, None)
            self._metadata.pop(session_id, None)
            self._id_generators.pop(session_id, None)
        else:
            self._sessions.clear()
            self._metadata.clear()
            self._id_generators.clear()
