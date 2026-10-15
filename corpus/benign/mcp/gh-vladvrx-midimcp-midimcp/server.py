"""Local stdio MCP server. All generated artifacts live in unique job folders."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from importlib.metadata import version

from mcp.server.fastmcp import FastMCP
from . import __version__, audio, fl, fl_project, fl_arrangement, midi, presets, reference as reference_audio
from . import vocals, comparison, workflow, levels

mcp = FastMCP("MidiMCP", instructions=(
    "Recreate reference music with editable MIDI and Serum 2 presets. "
    "Recreate instruments only: preserve all singing, rap, speech, backing vocals and vocal chops as source audio. "
    "Do not synthesize vocal guides in the default recreation workflow. Separated vocals are not studio stems. "
    "For every reconstruction, monitor every instrument against its reference and the final mix against the reference mix. "
    "Use audio_monitor_levels before delivery. Missing references or capped gains are unresolved, never a perfect match. "
    "MIDI does not contain synth audio. Validate changes by native render and A/B listening. "
    "Compare isolated matching phrases where possible. Audio distances are diagnostics, "
    "not accuracy percentages. Never claim a generated preset was loaded in FL without evidence."
))


def _root() -> Path:
    return Path(os.environ.get("MIDIMCP_OUTPUT_DIR", str(Path.cwd() / "midimcp-output"))).expanduser().resolve()


def _job(kind: str) -> Path:
    root = _root()
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=kind + "-", dir=root))


def _save(job: Path, result: dict) -> dict:
    result["manifest"] = str(job / "manifest.json")
    (job / "manifest.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result


def _input(path: str, extensions: tuple[str, ...] | None = None) -> Path:
    resolved = Path(path).expanduser().resolve(strict=True)
    if not resolved.is_file():
        raise ValueError("Expected a file")
    if extensions and resolved.suffix.lower() not in extensions:
        raise ValueError("Expected file type: " + ", ".join(extensions))
    return resolved


@mcp.tool()
def capabilities() -> dict:
    """Report installed versions and honest integration limits; does not launch FL."""
    executable = os.environ.get("MIDIMCP_FL_EXECUTABLE") or fl.discover_fl()
    return {"version": __version__, "upstream_version": version("serum-mcp"),
            "upstream_revision": presets.UPSTREAM_REVISION,
            "output_dir": str(_root()), "fl_executable": str(executable) if executable else None,
            "transport": "stdio", "supports": ["serum_preset_create_edit_describe", "midi_phrase_create_inspect",
            "audio_reference_excerpt", "audio_compare_ab", "saved_flp_render", "experimental_serum_flp_create", "experimental_arrangement_instrument_replace",
            "preserved_vocal_assets", "aligned_vocal_mix", "numbered_stereo_comparisons",
            "reconstruction_role_contract", "instrumental_only_midi_export", "default_reference_level_monitoring"],
            "level_policy": {"default": "match_reference_per_instrument_and_mix", "tolerance_db": 0.5,
                             "source_files": "unchanged", "missing_reference": "report_unverified"},
            "limitations": ["No automatic full-song transcription or guaranteed sound match.",
            "Experimental project creation supports FL24 and Serum2.0.18 with a local saved Serum project as a wrapper template.",
            "Project builder imports notes and velocity; MIDI expression is not yet supported.",
            "Vocal tools preserve supplied audio; automatic vocal separation and native FL audio-clip insertion are not implemented.",
            "FL must be closed for batch rendering; the tool refuses to launch over an open session.",
            "Custom sample ingestion is not enabled; upstream edits may apply module defaults.",
            "Serum and FL Studio must be installed and licensed by the user."]}


@mcp.tool()
def serum_parameter_schema() -> dict:
    """Get the actual supported upstream preset schema before constructing a spec."""
    return presets.parameter_schema()


@mcp.tool()
def serum_create_preset(spec: dict, name: str) -> dict:
    """Create a unique Serum 2 preset. This does not load it into FL Studio."""
    job = _job("preset")
    return _save(job, presets.create_preset(spec, job, name))


@mcp.tool()
def serum_edit_preset(source: str, spec: dict, name: str) -> dict:
    """Create an edited candidate without overwriting the source. Inspect changed_raw_fields."""
    source_path = _input(source, (".serumpreset",))
    job = _job("preset-edit")
    return _save(job, presets.edit_preset(source_path, spec, job, name))


@mcp.tool()
def serum_describe_preset(path: str) -> dict:
    """Describe supported fields and asset references in an existing Serum 2 preset."""
    return presets.describe_preset(_input(path, (".serumpreset",)))


@mcp.tool()
def midi_create_phrase(notes: list[dict], bpm: float = 120) -> dict:
    """Create editable MIDI. Each note has start/end in seconds, pitch 0..127, velocity 1..127."""
    job = _job("midi")
    return _save(job, midi.make_phrase(job / "phrase.mid", notes, bpm))


@mcp.tool()
def midi_inspect(path: str) -> dict:
    """Inspect notes, tempo and expression in an existing MIDI file."""
    return midi.inspect_midi(_input(path, (".mid", ".midi")))


@mcp.tool()
def reconstruction_plan(parts: list[dict], reference_audio: str | None = None) -> dict:
    """Validate explicit instrument/vocal roles. Voices must remain audio; this is not transcription or fidelity verification."""
    result = workflow.create_reconstruction_plan(parts, reference_audio)
    return _save(_job("plan"), result)


@mcp.tool()
def midi_export_instrumental(source: str, track_roles: dict[str, str]) -> dict:
    """Exclude explicitly classified vocal MIDI. Classify every track as instrumental, vocal or metadata; mixed tracks are rejected."""
    source_path = _input(source, (".mid", ".midi"))
    job = _job("instrumental")
    return _save(job, workflow.export_instrumental_midi(source_path, track_roles, job))


@mcp.tool()
def audio_reference_excerpt(source: str, start_seconds: float, duration_seconds: float) -> dict:
    """Extract up to 120 seconds for a matching phrase test, preserving rate/channels/level."""
    source_path = _input(source)
    job = _job("reference")
    return _save(job, reference_audio.excerpt(source_path, job / "reference.wav", start_seconds, duration_seconds))


@mcp.tool()
def audio_compare(reference: str, candidate: str, max_shift_seconds: float = 0.1) -> dict:
    """Compare corresponding audio excerpts and export a level-matched A/B WAV."""
    reference_path, candidate_path = _input(reference), _input(candidate)
    job = _job("compare")
    result = audio.compare_audio(reference_path, candidate_path, job, max_shift_seconds)
    result["input_sha256"] = {key: hashlib.sha256(path.read_bytes()).hexdigest()
                              for key, path in (("reference", reference_path), ("candidate", candidate_path))}
    return _save(job, result)


@mcp.tool()
def audio_export_comparison(first: str, second: str, match_rms: bool = True) -> dict:
    """Export separate numbered WAVs, preserving stereo/timing. Optional RMS matching uses constant gains."""
    first_path, second_path = _input(first), _input(second)
    job = _job("listening")
    return _save(job, comparison.export_pair(first_path, second_path, job, match_rms))


@mcp.tool()
def audio_preserve_vocals(source: str, provenance: str, timeline_start_seconds: float = 0,
                          original_mix: str | None = None, separation_model: str | None = None) -> dict:
    """Copy vocal audio unchanged with provenance. Separated stems require original mix and model; no separation is performed."""
    source_path = _input(source)
    mix_path = _input(original_mix) if original_mix else None
    job = _job("vocals")
    result = vocals.preserve_vocals(source_path, job, provenance,
                 timeline_start_seconds, mix_path, separation_model)
    result["levels"] = levels.inspect_level(Path(result["path"]))
    return _save(job, result)


@mcp.tool()
def audio_assemble_recreation(instrumental: str, vocal_assets: list[dict], reference_mix: str | None = None) -> dict:
    """Mix an instrumental with preserved vocal manifests at explicit offsets. No pitch/time changes; same sample rate required."""
    instrumental_path = _input(instrumental)
    job = _job("recreation-mix")
    result = vocals.assemble_recreation(instrumental_path, vocal_assets, job)
    result["level_monitor"] = _monitor(Path(result["outputs"]["recreation"]["path"]), reference_mix, job)
    return _save(job, result)


def _monitor(candidate: Path, reference: str | None, job: Path) -> dict:
    measured = levels.inspect_level(candidate)
    if reference is None:
        return {"status": "reference_required", "candidate": measured,
                "target_achieved": False, "reason": "Supply the corresponding reference to verify level preservation."}
    try:
        result = levels.match_level(_input(reference), candidate, job / "level_matched.wav")
    except (ValueError, OSError) as exc:
        return {"status": "review_required", "candidate": measured, "target_achieved": False, "reason": str(exc)}
    return {"status": "matched" if result["target_achieved"] else "review_required", **result}


@mcp.tool()
def audio_inspect_levels(path: str) -> dict:
    """Measure full-file LUFS, RMS and sample/estimated true peaks. Does not alter the file."""
    return levels.inspect_level(_input(path))


@mcp.tool()
def audio_match_reference_level(reference: str, candidate: str, tolerance_db: float = 0.5,
                                max_gain_db: float = 24) -> dict:
    """Create a constant-gain copy matching corresponding reference loudness. Report clipping caps and unmet targets."""
    ref, cand = _input(reference), _input(candidate)
    job = _job("level-match")
    return _save(job, levels.match_level(ref, cand, job / "level_matched.wav", tolerance_db, max_gain_db))


@mcp.tool()
def audio_monitor_levels(pairs: list[dict]) -> dict:
    """Check all instrument and mix pairs. Each item needs name, reference and candidate; missing references remain unverified."""
    if not 1 <= len(pairs) <= 32:
        raise ValueError("Provide 1..32 named instrument/mix pairs")
    job = _job("level-monitor")
    results = []
    for index, pair in enumerate(pairs):
        if not isinstance(pair, dict) or not isinstance(pair.get("name"), str) or not pair["name"].strip():
            raise ValueError("Each pair needs a nonempty name")
        candidate = _input(pair["candidate"])
        folder = job / str(index);folder.mkdir()
        results.append({"name": pair["name"], **_monitor(candidate, pair.get("reference"), folder)})
    return _save(job, {"all_targets_achieved": all(r["target_achieved"] for r in results), "results": results,
                       "scope": "Only supplied pairs checked; no missing instruments inferred", "source_files_modified": False})


@mcp.tool()
def fl_create_serum_project(preset: str, midi_path: str, wrapper_project: str | None = None,
                            bpm: float = 120) -> dict:
    """Build an isolated Serum FLP from a patch and MIDI. Requires a saved FL24 Serum2.0.18 wrapper template."""
    wrapper = wrapper_project or os.environ.get("MIDIMCP_TEMPLATE_PROJECT")
    executable = os.environ.get("MIDIMCP_FL_EXECUTABLE") or fl.discover_fl()
    if not wrapper:
        raise ValueError("Provide wrapper_project or set MIDIMCP_TEMPLATE_PROJECT to a saved FL24 project containing Serum2.0.18 VST3")
    if not executable:
        raise ValueError("Set MIDIMCP_FL_EXECUTABLE to the installed FL64.exe")
    wrapper_path = _input(wrapper, (".flp",))
    preset_path = _input(preset, (".serumpreset", ".vstpreset"))
    phrase_path = _input(midi_path, (".mid", ".midi"))
    job = _job("fl-project")
    result = fl_project.build_serum_project(wrapper_path, preset_path, phrase_path, job, Path(executable).parent, bpm=bpm)
    result["input_sha256"] = {key: hashlib.sha256(path.read_bytes()).hexdigest()
                             for key, path in (("wrapper", wrapper_path), ("preset", preset_path), ("midi", phrase_path))}
    return _save(job, result)


@mcp.tool()
def fl_replace_channel_serum(project: str, channel_index: int, preset: str,
                             wrapper_project: str | None = None) -> dict:
    """Replace one instrument in a new FLP copy, preserving notes and routing. Old plugin automation is not remapped."""
    wrapper = wrapper_project or os.environ.get("MIDIMCP_TEMPLATE_PROJECT")
    executable = os.environ.get("MIDIMCP_FL_EXECUTABLE") or fl.discover_fl()
    if not wrapper or not executable:
        raise ValueError("Configure MIDIMCP_TEMPLATE_PROJECT and MIDIMCP_FL_EXECUTABLE, or provide wrapper_project")
    source = _input(project, (".flp",))
    patch = _input(preset, (".serumpreset", ".vstpreset"))
    wrapper_path = _input(wrapper, (".flp",))
    job = _job("fl-channel")
    return _save(job, fl_arrangement.replace_channel_serum(source, channel_index, patch, wrapper_path,
                                                           job, Path(executable).parent))


@mcp.tool()
def fl_render_project(project: str, timeout_seconds: float = 180, reference_audio: str | None = None) -> dict:
    """Render an existing saved FLP in a separate process. Export settings are inherited."""
    executable = os.environ.get("MIDIMCP_FL_EXECUTABLE") or fl.discover_fl()
    if not executable:
        raise ValueError("Set MIDIMCP_FL_EXECUTABLE to the installed FL64.exe")
    result = fl.render_project(_input(project, (".flp",)), _root(), Path(executable), timeout_seconds)
    if result["status"] == "ok":
        job = Path(result["job_dir"])
        result["level_monitor"] = _monitor(Path(result["audio"]["path"]), reference_audio, job)
        _save(job, result)
    return result


@mcp.tool()
def fl_render_and_compare(project: str, reference: str, timeout_seconds: float = 180,
                          max_shift_seconds: float = 0.1) -> dict:
    """Render a saved FLP and compare its output. Stops if rendering/validation fails."""
    reference_path = _input(reference)
    render = fl_render_project(project, timeout_seconds, str(reference_path))
    if render["status"] != "ok":
        return {"status": "error", "render": render, "comparison": None}
    comparison = audio_compare(str(reference_path), render["audio"]["path"], max_shift_seconds)
    return {"status": "ok", "render": render, "comparison": comparison,
            "warning": "A successful render does not establish perceptual similarity or patch identity."}


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
