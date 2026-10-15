"""Replace one instrument while retaining an existing arrangement's raw events."""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
from uuid import uuid4

from .fl_project import (_encode_event, _installed_fl_version, read_events,
                         replace_native_wrapper_state, replace_wrapper_state)


def _spans(blob: bytes, events: list[tuple[int, bytes]]) -> list[bytes]:
    """Retain original length encodings as well as unknown event payload bytes."""
    cursor, spans = 22, []
    for event, value in events:
        start = cursor
        cursor += 1
        if event >= 192:
            while blob[cursor] & 128:
                cursor += 1
            cursor += 1
        cursor += len(value)
        spans.append(blob[start:cursor])
    if cursor != len(blob):
        raise ValueError("Source event byte ranges are inconsistent")
    return spans


def _version(events):
    raw = next((value for event, value in events if event == 199), b"")
    try:
        version = tuple(int(part) for part in raw.rstrip(b"\0").decode("ascii").split("."))
    except (ValueError, UnicodeError):
        raise ValueError("Invalid FL project version") from None
    if len(version) != 4 or version[0] != 24:
        raise ValueError("Arrangement replacement currently requires a native FL24 project")
    return version


def _plugin_block(events, start):
    """Only support native generator sections ending at channel enable event 0."""
    end = start + 1
    while end < len(events) and events[end][0] not in {0, 64, 99}:
        end += 1
    if end >= len(events) or events[end][0] != 0:
        raise ValueError("Unsupported channel block; expected native generator configuration")
    block = events[start + 1:end]
    for required in (21, 201, 212, 213):
        if sum(event == required for event, _ in block) != 1:
            raise ValueError(f"Expected exactly one instrument event {required}")
    if next(value for event, value in block if event == 21) != b"\x02":
        raise ValueError("Selected channel must be an instrument plugin, not an audio clip or sampler")
    if sum(event == 41 for event, _ in block) > 1:
        raise ValueError("Ambiguous native plugin wrapper flags")
    return end, block


def replace_channel_serum(source_project: Path, channel_index: int, preset: Path,
                          wrapper_project: Path, output_dir: Path,
                          fl_install: Path) -> dict:
    """Create a new FLP changing only one channel's plugin identity/state.

    Preserves raw note, arrangement, mixer, routing, labels, volume and other
    channel events. Parameter automation is not remapped between instruments.
    Channel indices are zero-based native FL channel IDs.
    """
    if isinstance(channel_index, bool) or not isinstance(channel_index, int) or channel_index < 0:
        raise ValueError("channel_index must be a nonnegative integer")
    source_project, preset, wrapper_project = (Path(path).expanduser().resolve(strict=True)
                                               for path in (source_project, preset, wrapper_project))
    original = source_project.read_bytes()
    events, wrapper_events = read_events(source_project), read_events(wrapper_project)
    source_version = _version(events)
    if _version(wrapper_events) != source_version or _installed_fl_version(Path(fl_install)) != source_version:
        raise ValueError("Source, wrapper, and installed FL executable versions must match exactly")
    selected = [index for index, (event, value) in enumerate(events)
                if event == 64 and struct.unpack("<H", value)[0] == channel_index]
    if len(selected) != 1:
        raise ValueError(f"Expected exactly one channel with native index {channel_index}")
    start = selected[0]
    end, block = _plugin_block(events, start)
    wrapper_state_index = next((index for index, (event, value) in enumerate(wrapper_events)
                                if event == 213 and b"Serum2" in value and b"XferJson\0" in value), None)
    if wrapper_state_index is None:
        raise ValueError("Wrapper project has no saved Serum 2 VST3 instrument")
    wrapper_start = max((index for index in range(wrapper_state_index)
                         if wrapper_events[index][0] == 64), default=-1)
    if wrapper_start < 0:
        raise ValueError("Serum wrapper is not contained in an instrument channel")
    _, source_plugin = _plugin_block(wrapper_events, wrapper_start)
    replacements = {event: value for event, value in source_plugin if event in {201, 212, 213, 41}}
    state = replacements[213]
    native = preset.read_bytes().startswith(b"XferJson\0")
    replacements[213] = (replace_native_wrapper_state(state, preset) if native
                         else replace_wrapper_state(state, preset))
    window = bytearray(replacements[212])
    if len(window) < 20:
        raise ValueError("Unsupported Serum plugin window state")
    struct.pack_into("<I", window, 16, 0x51)
    replacements[212] = bytes(window)
    spans = _spans(original, events)
    rewritten, changed_indices = [], []
    has_flag = any(event == 41 for event, _ in block)
    for index, ((event, _), span) in enumerate(zip(events, spans, strict=True)):
        if start < index < end:
            if event == 213 and not has_flag and 41 in replacements:
                rewritten.append(_encode_event(41, replacements[41]))
            if event in replacements:
                span = _encode_event(event, replacements[event])
                changed_indices.append(index)
        rewritten.append(span)
    body = b"".join(rewritten)
    result_blob = original[:18] + struct.pack("<I", len(body)) + body
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"MidiMCP-channel-{channel_index}-{uuid4().hex}.flp"
    with target.open("xb") as stream:
        stream.write(result_blob)
    result_events = read_events(target)
    # These events contain notes, playlists and mixer routes. No reserialization.
    protected = {224, 233, 22, 219, 225, 235, 236, 237}
    if [(e, v) for e, v in events if e in protected] != [(e, v) for e, v in result_events if e in protected]:
        raise ValueError("Protected arrangement events changed unexpectedly")
    channel_name = next((value.decode("utf-16-le").rstrip("\0") for event, value in block if event == 203), "")
    return {"path": str(target), "channel_index": channel_index, "channel_name": channel_name,
            "fl_version": ".".join(map(str, source_version)),
            "source_sha256": hashlib.sha256(original).hexdigest(),
            "sha256": hashlib.sha256(result_blob).hexdigest(),
            "preset_sha256": hashlib.sha256(preset.read_bytes()).hexdigest(),
            "changed_source_event_indices": changed_indices,
            "inserted_wrapper_flag": not has_flag and 41 in replacements,
            "all_other_event_bytes_preserved": True, "native_render_verified": False,
            "warnings": ["Existing plugin-parameter automation is preserved but not translated to Serum parameters.",
                         "Notes, expression, channel volume, mixer processing and routing retain their original state.",
                         "Native rendering and listening are required to assess the replacement sound."]}
