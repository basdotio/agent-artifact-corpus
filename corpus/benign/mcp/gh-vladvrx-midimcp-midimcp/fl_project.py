"""Build an isolated one-channel FL project from user-installed native templates.

Wrapper chunks are retained from a user-selected Serum 2 project. Processor and
controller states are replaced from a VST3 preset; no source notes are copied.
The FL wrapper format is observational and version-gated, not an official API.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import math
import os
import struct
from uuid import uuid4

from .midi import inspect_midi
from serum_mcp.preset.packer import SerumPreset, pack_bytes, unpack_bytes


def read_events(path: Path) -> list[tuple[int, bytes]]:
    data = Path(path).read_bytes()
    if len(data) < 22 or data[:4] != b"FLhd" or data[14:18] != b"FLdt":
        raise ValueError("Not a supported FLP/FST event container")
    if struct.unpack_from("<I", data, 4)[0] != 6 or len(data) != 22 + struct.unpack_from("<I", data, 18)[0]:
        raise ValueError("Invalid FLP header or event length")
    offset, result = 22, []
    while offset < len(data):
        event = data[offset]
        offset += 1
        if event < 192:
            size = 1 if event < 64 else 2 if event < 128 else 4
        else:
            size = shift = 0
            while True:
                if offset >= len(data) or shift > 28:
                    raise ValueError("Malformed FLP variable length")
                byte = data[offset]
                offset += 1
                size |= (byte & 127) << shift
                shift += 7
                if byte < 128:
                    break
        if offset + size > len(data):
            raise ValueError("Truncated FLP event")
        result.append((event, data[offset:offset + size]))
        offset += size
    return result


def _encode_event(event: int, value: bytes) -> bytes:
    prefix = bytes([event])
    if event >= 192:
        size = len(value)
        while size >= 128:
            prefix += bytes([(size & 127) | 128])
            size >>= 7
        prefix += bytes([size])
    return prefix + value


def _chunks(blob: bytes, version: int):
    if len(blob) < 4 or struct.unpack_from("<I", blob)[0] != version:
        raise ValueError(f"Unsupported native FL wrapper version, expected {version}")
    cursor, chunks = 4, []
    while cursor < len(blob):
        if cursor + 12 > len(blob):
            raise ValueError("Truncated native wrapper chunk")
        kind, size = struct.unpack_from("<IQ", blob, cursor)
        cursor += 12
        if cursor + size > len(blob):
            raise ValueError("Invalid native wrapper chunk length")
        chunks.append((kind, blob[cursor:cursor + size]))
        cursor += size
    return chunks


def _encode_chunks(chunks, version):
    return struct.pack("<I", version) + b"".join(struct.pack("<IQ", kind, len(value)) + value for kind, value in chunks)


def _vst_chunks(path: Path):
    data = Path(path).read_bytes()
    if len(data) < 48 or data[:4] != b"VST3":
        raise ValueError("Expected VST3 preset")
    offset = struct.unpack_from("<Q", data, 40)[0]
    if offset + 8 > len(data) or data[offset:offset + 4] != b"List":
        raise ValueError("Invalid VST3 chunk table")
    count = struct.unpack_from("<I", data, offset + 4)[0]
    if offset + 8 + 20 * count > len(data):
        raise ValueError("Truncated VST3 chunk table")
    chunks = {}
    for index in range(count):
        name, start, size = struct.unpack_from("<4sQQ", data, offset + 8 + 20 * index)
        if start < 48 or start + size > offset:
            raise ValueError("Invalid VST3 chunk range")
        chunks[name] = data[start:start + size]
    if not all(chunks.get(key, b"").startswith(b"XferJson\0") for key in (b"Comp", b"Cont")):
        raise ValueError("VST3 preset must contain Serum processor and controller states")
    return data[8:40], chunks


def _installed_fl_version(fl_install: Path) -> tuple[int, int, int, int]:
    """Read the actual PE version resource; folder names are not version evidence."""
    if os.name != "nt":
        raise ValueError("Native FL project construction currently requires Windows")
    import ctypes
    from ctypes import wintypes
    executable = Path(fl_install) / "FL64.exe"
    if not executable.is_file():
        raise ValueError("FL installation must contain FL64.exe")
    version = ctypes.WinDLL("version", use_last_error=True)
    version.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    version.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    version.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    version.GetFileVersionInfoW.restype = wintypes.BOOL
    version.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
    version.VerQueryValueW.restype = wintypes.BOOL
    ignored = wintypes.DWORD()
    size = version.GetFileVersionInfoSizeW(str(executable), ctypes.byref(ignored))
    if not size:
        raise ValueError("Cannot read FL64.exe version resource")
    data = ctypes.create_string_buffer(size)
    if not version.GetFileVersionInfoW(str(executable), 0, size, data):
        raise ValueError("Cannot load FL64.exe version resource")
    pointer, length = ctypes.c_void_p(), wintypes.UINT()
    if not version.VerQueryValueW(data, "\\", ctypes.byref(pointer), ctypes.byref(length)) or length.value < 52:
        raise ValueError("Invalid FL64.exe version resource")
    fixed = struct.unpack("<13I", ctypes.string_at(pointer, 52))
    if fixed[0] != 0xFEEF04BD:
        raise ValueError("Invalid executable version signature")
    high, low = fixed[2:4]
    return high >> 16, high & 65535, low >> 16, low & 65535


def replace_wrapper_state(wrapper: bytes, vstpreset: Path) -> bytes:
    class_id, states = _vst_chunks(vstpreset)
    outer = _chunks(wrapper, 11)
    identities = [value for kind, value in outer if kind == 52]
    expected = bytes.fromhex(class_id.decode("ascii"))
    # FL stores the GUID's DWORD and two WORDs in Windows byte order.
    fl_identity = expected[:4][::-1] + expected[4:6][::-1] + expected[6:8][::-1] + expected[8:]
    if identities != [fl_identity] or b"Serum2" not in wrapper:
        raise ValueError("Wrapper and VST preset do not identify the same Serum 2 plugin")
    result, count = [], 0
    for kind, value in outer:
        if kind == 53:
            inner = _chunks(value, 1)
            if sum(k == 3 for k, _ in inner) != 1 or sum(k == 2 for k, _ in inner) != 1:
                raise ValueError("Expected one processor and one controller wrapper chunk")
            value = _encode_chunks([(k, states[b"Comp"] if k == 3 else states[b"Cont"] if k == 2 else v) for k, v in inner], 1)
            count += 1
        result.append((kind, value))
    if count != 1:
        raise ValueError("Expected one saved VST3 state in wrapper")
    return _encode_chunks(result, 11)


_CONTROLLER_FIELDS = {"ClipPlayer", "Filter", "SerumGUI", "arpBankDisplayName", "clipBankDisplayName", "GranularOsc", "MultiSampleOsc", "Osc", "SpectralOsc", "WTOsc"}
_METADATA_FIELDS = {"fileType", "presetName", "presetAuthor", "presetDescription"}
_CONTROLLER_SUBFIELDS = {"Macro": ("name",), "FXRack": ("displayName",),
                         "MidiClip": ("displayLength_Beats", "gridWidth_Beats", "gridYOffset_Rows", "laneTabs", "name"),
                         "PitchQuantizer": ("scaleName",)}


def _processor_defaults(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "plainParams" and child == "default":
                value[key] = {}
            else:
                _processor_defaults(child)
    elif isinstance(value, list):
        for child in value:
            _processor_defaults(child)


def _pack_component(component: SerumPreset) -> bytes:
    # Serum component headers carry a digest of the compressed CBOR payload.
    blob = pack_bytes(component)
    metadata_length = struct.unpack_from("<I", blob, 9)[0]
    component.metadata["hash"] = hashlib.md5(blob[25 + metadata_length:]).hexdigest()
    return pack_bytes(component)


def replace_native_wrapper_state(wrapper: bytes, native_preset: Path) -> bytes:
    """Translate native preset DSP/UI state using the installed wrapper version.

    Reuses the upstream codec; the processor/controller split is based on native
    Serum 2.0.18 captures. The result still requires native audio validation.
    """
    outer = _chunks(wrapper, 11)
    if b"Serum2" not in wrapper or sum(kind == 53 for kind, _ in outer) != 1:
        raise ValueError("Expected one native saved Serum 2 wrapper")
    if [value for kind, value in outer if kind == 52] != [bytes.fromhex("58455356736673506572756D20320000")]:
        raise ValueError("Native wrapper does not identify the supported Serum 2 VST3 class")
    native = unpack_bytes(Path(native_preset).read_bytes())
    inner = _chunks(next(value for kind, value in outer if kind == 53), 1)
    if sum(kind == 3 for kind, _ in inner) != 1 or sum(kind == 2 for kind, _ in inner) != 1:
        raise ValueError("Expected native processor and controller chunks")
    processor = unpack_bytes(next(value for kind, value in inner if kind == 3))
    controller = unpack_bytes(next(value for kind, value in inner if kind == 2))
    if processor.metadata.get("product") != "Serum2" or processor.metadata.get("productVersion") != "2.0.18":
        raise ValueError("Native preset translation currently supports captured Serum 2.0.18 wrappers only")
    params = deepcopy(native.data)
    for key in _CONTROLLER_FIELDS | _METADATA_FIELDS:
        params.pop(key, None)
    _processor_defaults(params)
    for key, value in params.items():
        if not isinstance(value, dict):
            continue
        for prefix, names in _CONTROLLER_SUBFIELDS.items():
            if key.startswith(prefix) and key[len(prefix):].isdigit():
                for field in names:
                    value.pop(field, None)
        if key.startswith("Arp") and key[3:].isdigit():
            value.setdefault("activeClip", 0)
    for key in ("component", "killEnvsGracefullyCompat", "productVersion", "version"):
        if key in processor.data:
            params[key] = deepcopy(processor.data[key])
    processor.data = params
    for key in ("presetName", "presetAuthor", "presetDescription"):
        controller.metadata[key] = native.metadata.get(key, "")
        controller.data[key] = native.metadata.get(key, "")
    for key, value in native.data.items():
        if key in _CONTROLLER_FIELDS:
            controller.data[key] = deepcopy(value)
        if isinstance(value, dict):
            for prefix, names in _CONTROLLER_SUBFIELDS.items():
                if key.startswith(prefix) and key[len(prefix):].isdigit():
                    for field in names:
                        if field in value:
                            if not isinstance(controller.data.get(key), dict):
                                controller.data[key] = {}
                            controller.data[key][field] = deepcopy(value[field])
    controller.data["presetHasBeenEdited"] = False
    # This UI-only field otherwise exposes the source library path and points
    # Serum's browser at the unrelated patch used to capture the wrapper.
    controller.data["selectedPresetPath"] = ""
    components = {3: _pack_component(processor), 2: _pack_component(controller)}
    replacement = _encode_chunks([(kind, components.get(kind, value)) for kind, value in inner], 1)
    return _encode_chunks([(kind, replacement if kind == 53 else value) for kind, value in outer], 11)


def build_serum_project(wrapper_project: Path, vstpreset: Path, midi_path: Path,
                        output_dir: Path, fl_install: Path, *, bpm: float = 120) -> dict:
    """Create a new project. Expression MIDI is rejected until implemented."""
    if not math.isfinite(bpm) or not 4 <= bpm <= 1000:
        raise ValueError("Invalid tempo")
    phrase = inspect_midi(midi_path)
    if not phrase["notes"] or phrase["expression_events"] or phrase["warnings"]:
        raise ValueError("FL project builder needs nonempty valid notes without MIDI expression")
    if len({note["channel"] for note in phrase["notes"]}) != 1:
        raise ValueError("FL project builder accepts one MIDI channel; split multi-instrument MIDI into separate phrases")
    original = read_events(wrapper_project)
    native_version = next((value for event, value in original if event == 199), b"")
    native_build = next((value for event, value in original if event == 159), b"")
    native_playlist = next((value for event, value in original if event == 233 and value), b"")
    if not native_version.startswith(b"24.") or len(native_build) != 4 or len(native_playlist) < 60 or len(native_playlist) % 60:
        raise ValueError("Builder requires a native FL Studio 24 project with 60-byte playlist records")
    try:
        project_version = tuple(int(part) for part in native_version.rstrip(b"\0").decode("ascii").split("."))
    except (ValueError, UnicodeError):
        raise ValueError("Invalid native FL project version") from None
    installed_version = _installed_fl_version(Path(fl_install))
    if installed_version != project_version:
        raise ValueError(f"FL executable version {installed_version} differs from wrapper project {project_version}; save a wrapper in the exact installed FL version")
    wrapper_index = next((i for i, (event, value) in enumerate(original) if event == 213 and b"Serum2" in value and b"XferJson\0" in value), None)
    if wrapper_index is None:
        raise ValueError("Selected project has no supported saved Serum 2 VST3 state")
    start = max(i for i in range(wrapper_index) if original[i][0] == 64)
    plugin = []
    for event, value in original[start + 1:wrapper_index + 1]:
        if event not in {21, 201, 212, 203, 155, 128, 41, 213}:
            continue
        if event == 213:
            if Path(vstpreset).read_bytes().startswith(b"XferJson\0"):
                value = replace_native_wrapper_state(value, vstpreset)
            else:
                value = replace_wrapper_state(value, vstpreset)
        elif event == 212:
            value = bytearray(value)
            if len(value) < 20:
                raise ValueError("Unsupported FL plugin window state")
            struct.pack_into("<I", value, 16, 0x51)
            value = bytes(value)
        elif event == 203:
            value = "MidiMCP Serum 2\0".encode("utf-16-le")
        plugin.append((event, value))
    installed = Path(fl_install)
    template = read_events(installed / "Data/System/Render tests/FLEX.flp")
    empty = read_events(installed / "Data/Templates/Minimal/Empty/Empty.flp")
    pattern = next(i for i, (event, _) in enumerate(template) if event == 65)
    arrangement = next(i for i, (event, _) in enumerate(template) if event == 99)
    echannel = next(i for i, (event, _) in enumerate(empty) if event == 64)
    earr = next(i for i, (event, _) in enumerate(empty) if event == 99)
    generic = empty[echannel:earr]
    generic = generic[next(i for i, (event, _) in enumerate(generic) if event == 0):]
    result = []
    for event, value in template[:pattern]:
        if event == 199:
            value = native_version
        elif event == 159:
            value = native_build
        elif event == 156:
            value = struct.pack("<I", round(bpm * 1000))
        elif event == 9:
            value = b"\x01"
        elif event == 194:
            value = "MidiMCP Serum phrase\0".encode("utf-16-le")
        elif event == 195:
            value = "Generated isolated Serum 2 phrase\0".encode("utf-16-le")
        result.append((event, value))
    ticks = lambda seconds: round(seconds * bpm * 960 / 60)
    note_data = b"".join(struct.pack("<IHHIHH8B", ticks(note["start"]), 0x4000, 0,
                            max(1, ticks(note["end"]) - ticks(note["start"])), note["pitch"], 0,
                            120, 0, 64, 0, 64, note["velocity"], 128, 128) for note in phrase["notes"])
    result += [(65, struct.pack("<H", 1)), (224, note_data), (193, "Serum phrase\0".encode("utf-16-le")), (64, struct.pack("<H", 0))]
    result += plugin
    for event, value in generic:
        if event == 22:
            value = b"\0"
        elif event == 132:
            value = bytes(4)
        elif event == 219:
            value = bytearray(value)
            struct.pack_into("<I", value, 4, 12800)
            value = bytes(value)
        elif event == 215:
            value = bytearray(value)
            struct.pack_into("<I", value, 40, 0)
            value = bytes(value)
        result.append((event, value))
    length = ticks(max(note["end"] for note in phrase["notes"]))
    # Pattern offsets use native sentinel bits, not the float -1.0 encoding
    # used by audio clips. Preserve a native pattern record's unknown fields.
    anchors = [native_playlist[i:i + 60] for i in range(0, len(native_playlist), 60)
               if struct.unpack_from("<H", native_playlist, i + 6)[0] > 20480]
    if not anchors:
        raise ValueError("Native FL template needs at least one pattern playlist clip")
    playlist = bytearray(anchors[0])
    struct.pack_into("<IHHI", playlist, 0, 0, 20480, 20481, length)
    struct.pack_into("<H", playlist, 12, 499)
    struct.pack_into("<I", playlist, 32, 1)
    playlist = bytes(playlist)
    for event, value in template[arrangement:]:
        if event == 233:
            value = playlist
        result.append((event, value))
    # Clip ends at the final note so it cannot loop notes during a render tail.
    body = b"".join(_encode_event(*event) for event in result)
    blob = struct.pack("<4sIhHH", b"FLhd", 6, 0, 1, 960) + b"FLdt" + struct.pack("<I", len(body)) + body
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"MidiMCP-{uuid4().hex}.flp"
    with target.open("xb") as handle:
        handle.write(blob)
    verified = read_events(target)
    if sum(len(value) // 24 for event, value in verified if event == 224) != len(phrase["notes"]):
        raise ValueError("Saved FL project note verification failed")
    return {"path": str(target), "note_count": len(phrase["notes"]), "bpm": bpm,
            "fl_version": ".".join(map(str, installed_version)),
            "native_render_verified": False,
            "warnings": ["FL wrapper format is observational; native rendering and reopen verification are required.",
                         "Only notes and velocities are imported; MIDI expression is rejected.",
                         "Render tail is controlled by FL Studio's export settings."]}
