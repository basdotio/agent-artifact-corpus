"""MIDI phrase creation and inspection with time values expressed in seconds."""
from pathlib import Path
from collections import defaultdict, deque
import math
import mido


def make_phrase(path: Path, notes: list[dict], bpm=120) -> dict:
    if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or not math.isfinite(bpm) or not 4 <= bpm <= 1000:
        raise ValueError("bpm must be finite and between 4 and 1000")
    tempo, ticks_per_beat = mido.bpm2tempo(bpm), 960
    events = []
    intervals = defaultdict(list)
    for index, note in enumerate(notes):
        pitch, velocity = note.get("pitch"), note.get("velocity", 100)
        start, end = note.get("start"), note.get("end")
        for name, value, low, high in (("pitch", pitch, 0, 127), ("velocity", velocity, 1, 127)):
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"Note {index}: {name} must be an integer in [{low}, {high}]")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (start, end)):
            raise ValueError(f"Note {index}: start/end must be finite seconds")
        if start < 0 or end <= start:
            raise ValueError(f"Note {index}: require 0 <= start < end")
        start_tick = round(mido.second2tick(start, ticks_per_beat, tempo))
        end_tick = round(mido.second2tick(end, ticks_per_beat, tempo))
        if end_tick <= start_tick:
            raise ValueError(f"Note {index}: duration is below MIDI tick resolution")
        intervals[pitch].append((start_tick, end_tick))
        events.extend([(start_tick, 1, pitch, velocity), (end_tick, 0, pitch, 0)])
    for pitch, spans in intervals.items():
        spans.sort()
        if any(next_start < end for (_, end), (next_start, _) in zip(spans, spans[1:])):
            raise ValueError(f"Overlapping notes of pitch {pitch} are ambiguous on one MIDI channel")
    midi = mido.MidiFile(type=0, ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo))
    last = 0
    for tick, is_on, pitch, velocity in sorted(events):
        track.append(mido.Message("note_on" if is_on else "note_off", note=pitch,
                                  velocity=velocity, channel=0, time=tick-last))
        last = tick
    track.append(mido.MetaMessage("end_of_track"))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(path))
    return inspect_midi(path)


def inspect_midi(path: Path) -> dict:
    midi = mido.MidiFile(str(path))
    if midi.type == 2:
        raise ValueError("Type 2 MIDI contains independent sequences and has no single timeline")
    if midi.ticks_per_beat <= 0:
        raise ValueError("SMPTE MIDI time division is not supported")
    active = defaultdict(deque)
    notes, tempos, warnings, expression = [], [], [], []
    elapsed = 0.0
    unmatched_off = 0
    for message in midi:  # mido merges tracks and applies every tempo change.
        elapsed += message.time
        if message.type == "set_tempo":
            tempos.append({"seconds": elapsed, "bpm": mido.tempo2bpm(message.tempo)})
        if message.type in {"pitchwheel", "control_change", "aftertouch", "polytouch", "program_change"}:
            event = message.dict()
            event.pop("time", None)
            event["seconds"] = elapsed
            expression.append(event)
        if message.type == "note_on" and message.velocity > 0:
            active[(message.channel, message.note)].append((elapsed, message.velocity))
        elif message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
            queue = active[(message.channel, message.note)]
            if queue:
                start, velocity = queue.popleft()
                notes.append({"start": start, "end": elapsed, "pitch": message.note,
                              "velocity": velocity, "channel": message.channel})
            else:
                unmatched_off += 1
    unfinished = sum(map(len, active.values()))
    if unfinished:
        warnings.append(f"{unfinished} note-on messages have no matching note-off; omitted from notes")
    if unmatched_off:
        warnings.append(f"{unmatched_off} note-off messages have no matching note-on")
    if expression:
        warnings.append("Note intervals represent key presses; expression events are reported separately, including sustain and pitch bends")
    notes.sort(key=lambda n: (n["start"], n["pitch"]))
    return {"path": str(Path(path).resolve()), "type": midi.type, "tracks": len(midi.tracks),
            "ticks_per_beat": midi.ticks_per_beat, "duration_seconds": elapsed,
            "note_count": len(notes), "notes": notes, "tempo_changes": tempos,
            "expression_events": expression,
            "default_bpm": 120, "warnings": warnings}
