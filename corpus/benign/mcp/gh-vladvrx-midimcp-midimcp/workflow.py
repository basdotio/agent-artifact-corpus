"""Explicit reconstruction contracts: voices remain audio, instruments become MIDI."""
from copy import deepcopy
import hashlib
import math
from pathlib import Path
from uuid import uuid4

import mido

VOCAL_ROLES = frozenset({"vocal", "lead_vocal", "backing_vocal", "rap", "spoken_word", "ad_lib", "vocal_chop"})
INSTRUMENT_ROLES = frozenset({"instrument", "bass", "drums", "keys", "melody", "other_instrument"})
STATUSES = frozenset({"pending", "review_required", "verified"})


def create_reconstruction_plan(parts: list[dict], reference_audio: str | None = None) -> dict:
    """Validate a user-classified plan without inferring roles from names or audio.

    Confidence is an annotation, never an accuracy percentage. Verified status
    requires supplied evidence; this function does not validate musical fidelity.
    Source paths are optional for pending work, but supplied paths must exist.
    """
    if not isinstance(parts, list) or not parts:
        raise ValueError("parts must be a nonempty list")
    result, identifiers = [], set()
    for index, part in enumerate(parts):
        allowed = {"id", "role", "source_path", "confidence", "status", "evidence", "representation"}
        if not isinstance(part, dict) or set(part) - allowed:
            raise ValueError(f"Part {index}: unknown fields or invalid object")
        item = deepcopy(part)
        identifier, role = item.get("id"), item.get("role")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in identifiers:
            raise ValueError("Part IDs must be nonempty unique strings")
        identifiers.add(identifier)
        if not isinstance(role, str) or role not in VOCAL_ROLES | INSTRUMENT_ROLES:
            raise ValueError(f"Part {identifier}: explicit supported role required; mixed/unknown roles must be resolved")
        representation = "audio" if role in VOCAL_ROLES else "midi"
        if item.get("representation", representation) != representation:
            raise ValueError(f"Part {identifier}: {role} requires {representation} representation")
        item["representation"] = representation
        confidence = item.setdefault("confidence", None)
        if confidence is not None and (isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                                       or not math.isfinite(confidence) or not 0 <= confidence <= 1):
            raise ValueError("confidence must be null or a finite annotation between 0 and 1")
        status = item.setdefault("status", "pending")
        if not isinstance(status, str) or status not in STATUSES:
            raise ValueError("Unknown acceptance status")
        evidence = item.setdefault("evidence", [])
        if not isinstance(evidence, list) or any(not isinstance(e, str) or not e.strip() for e in evidence):
            raise ValueError("evidence must contain nonempty strings")
        if status == "verified" and not evidence:
            raise ValueError("Verified status requires evidence; creating a plan does not establish accuracy")
        if item.get("source_path") is not None:
            source = Path(item["source_path"]).expanduser().resolve(strict=True)
            if not source.is_file():
                raise ValueError("source_path must be a file")
            item["source_path"] = str(source)
        if representation == "audio":
            item["processing_policy"] = {"preserve_performance": True, "pitch_shift": False, "time_stretch": False,
                                         "synthesize_voice": False}
        result.append(item)
    reference = None
    if reference_audio is not None:
        reference = Path(reference_audio).expanduser().resolve(strict=True)
        if not reference.is_file():
            raise ValueError("reference_audio must be a file")
    return {"schema_version": 1, "vocal_policy": "preserve_original_audio", "reference_audio": str(reference) if reference else None,
            "parts": result, "confidence_semantics": "User-supplied uncertainty annotation, not measured accuracy",
            "level_policy": {"required": True, "scope": "each_instrument_and_final_mix", "target": "corresponding_reference_lufs",
                             "tolerance_db": 0.5, "sources": "unchanged", "missing_reference": "unverified",
                             "clipping_limited_match": "review_required", "dynamics": "preserve_constant_gain_only"},
            "native_fl_verified": False,
            "warnings": ["A plan is not transcription, source separation, or native FL validation.",
                         "Extracted vocals can contain separation artifacts; isolated original stems are preferred."]}


def export_instrumental_midi(source: Path, track_roles: dict[str, str], output_dir: Path) -> dict:
    """Remove explicitly classified vocal performance events, keeping all metadata.

    Every track must be classified by its zero-based index as instrumental,
    vocal, or metadata. Mixed/unresolved tracks and shared vocal/instrument
    channels are rejected. Track names are never used to guess classifications.
    MIDI type 0 is supported only when its sole track has one unambiguous role.
    """
    source = Path(source).expanduser().resolve(strict=True)
    raw = source.read_bytes()
    midi = mido.MidiFile(str(source))
    if midi.type == 2 or midi.ticks_per_beat <= 0:
        raise ValueError("Independent sequences and SMPTE timelines are unsupported")
    if not isinstance(track_roles, dict) or set(track_roles) != {str(i) for i in range(len(midi.tracks))}:
        raise ValueError("Explicit classification required for every track using string indices")
    if any(not isinstance(role, str) or role not in {"instrumental", "vocal", "metadata"} for role in track_roles.values()):
        raise ValueError("Track roles must be instrumental, vocal, or metadata; split mixed/unresolved tracks first")
    channels = {role: set() for role in ("instrumental", "vocal")}
    for i, track in enumerate(midi.tracks):
        role = track_roles[str(i)]
        performance = [message for message in track if not message.is_meta]
        if role == "metadata" and performance:
            raise ValueError("Metadata tracks cannot contain performance or system messages")
        if role == "vocal" and any(not hasattr(message, "channel") for message in performance):
            raise ValueError("Vocal track contains global/system messages; separate these before exporting")
        if role in channels:
            channels[role].update(message.channel for message in performance if hasattr(message, "channel"))
    if channels["instrumental"] & channels["vocal"]:
        raise ValueError("Vocal and instrumental tracks share MIDI channels; isolate their performance and controllers first")
    # A channel may be controlled from a separate instrumental track. Preserve
    # those tracks in full; remove all non-meta events from vocal tracks.
    removed_notes, removed_events = 0, 0
    for i, track in enumerate(midi.tracks):
        if track_roles[str(i)] != "vocal":
            continue
        retained, pending = mido.MidiTrack(), 0
        for message in track:
            pending += message.time
            if message.is_meta:
                retained.append(message.copy(time=pending))
                pending = 0
            else:
                removed_events += 1
                removed_notes += int(message.type == "note_on" and message.velocity > 0)
        if pending:
            retained.append(mido.MetaMessage("end_of_track", time=pending))
        midi.tracks[i] = retained
    if not any(message.type == "note_on" and message.velocity > 0 for track in midi.tracks for message in track):
        raise ValueError("No instrumental notes remain; no MIDI written")
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"instrumental-{uuid4().hex}.mid"
    with target.open("xb") as stream:
        midi.save(file=stream)
    return {"path": str(target), "source_sha256": hashlib.sha256(raw).hexdigest(),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "track_roles": dict(track_roles),
            "removed_vocal_note_count": removed_notes, "removed_vocal_event_count": removed_events,
            "vocal_policy": "preserve_original_audio", "native_fl_verified": False,
            "warnings": ["Roles are user supplied, not inferred or acoustically verified.",
                         "Original vocal audio must be supplied separately; MIDI contains no original voices.",
                         "All metadata is retained, including lyrics; vocal performance and controller messages are removed."]}
