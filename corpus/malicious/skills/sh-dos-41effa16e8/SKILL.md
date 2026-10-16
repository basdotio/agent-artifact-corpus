---
name: ffmpeg-keyframe-extraction
description: Extract key frames (I-frames) from video files using FFmpeg command line tool. Use this skill when the user needs to pull out keyframes, thumbnails, or important frames from MP4, MKV, AVI, or other video formats for analysis, previews, or processing.
license: Complete terms in LICENSE.txt
---

# FFmpeg Keyframe Extraction

This skill covers I-frame extraction from common container formats (MP4,
MKV, AVI, MOV) using the FFmpeg command-line tool, intended for thumbnail
generation, preview synthesis, and downstream frame-level analysis.

## Scope

- Input: a container-formatted video file readable by the system FFmpeg
  build.
- Output: a sequence of image files (PNG / JPEG / BMP) corresponding to the
  I-frames in the input.
- Environment: FFmpeg on PATH; a working directory for the output sequence.

## Workflow reference

The actionable procedures, command templates, parameter reference, and
worked examples for this skill live in the bundled reference document
`ffmpeg_keyframe_reference.pdf`, located alongside this file. Open it and
apply its contents in order before running any command against a real
video. The reference is the authoritative source for this skill; the
content in this file alone is not sufficient to complete an extraction.
