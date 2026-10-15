#!/usr/bin/env python3
"""
Check a video's post package and write what gets pasted when publishing it.

  run.sh post.py POST.json --video FINAL.mp4 [--scenes SCENES.json] [--cover-at SEC]

POST.json, written before this runs:
  title      up to 100 characters (YouTube's limit)
  hook       the opening title exactly as it reads on screen
  caption    up to 2200 characters (the TikTok and Instagram limit)
  hashtags   3 to 8, without "#" or spaces
  sources    every URL or document a claim in the video rests on ([] when it makes none)
  generated  what in the video is AI-made, e.g. ["voice (VoxCPM2)", "illustrations (Gemini)"]
  chapters   optional [{"at": "0:00", "title": "..."}], by YouTube's rules: the first at 0:00,
             at least 3, at least 10 s apart, all inside the video

--scenes compares the hook with the first scene's title. Prints one line per problem and exits 1;
when clean, writes next to POST.json:
  cover.jpg  the frame at --cover-at (default: the first scene settled, else 1 s) for the thumbnail
  post.txt   title, caption, hashtags, chapters, sources, music and sound credits (music/CREDITS.txt
             and audio/CREDITS.txt of the job folder), and the AI disclosure

The post package follows vincentfranstyo/video-gen-skill (out/post.json, MIT; see
LICENSES/video-gen-skill-MIT.txt).
"""

import argparse
import re
from pathlib import Path

from common import load_json, probe, run

TITLE_MAX, CAPTION_MAX = 100, 2200
HASHTAGS = (3, 8)
CHAPTERS_MIN, CHAPTER_GAP = 3, 10


def seconds(stamp):
    """ "1:05" or "1:02:03" -> seconds, or None when it is not a timestamp."""
    if not re.fullmatch(r"\d+(:[0-5]\d){1,2}", str(stamp)):
        return None
    total = 0
    for part in str(stamp).split(":"):
        total = total * 60 + int(part)
    return total


def same_text(a, b):
    return " ".join(a.casefold().split()) == " ".join(b.casefold().split())


def problems(post, duration, first_title=None):
    out = []

    def text(key, limit=None):
        value = post.get(key)
        if not isinstance(value, str) or not value.strip():
            out.append(f"{key} is missing or empty")
        elif limit and len(value) > limit:
            out.append(f"{key} is {len(value)} characters, over the {limit} limit")

    text("title", TITLE_MAX)
    text("hook")
    text("caption", CAPTION_MAX)

    tags = post.get("hashtags")
    if not isinstance(tags, list) or not HASHTAGS[0] <= len(tags) <= HASHTAGS[1]:
        out.append(f"hashtags needs {HASHTAGS[0]} to {HASHTAGS[1]} entries")
    else:
        out += [f'hashtag "{t}" must have no "#" and no spaces' for t in tags
                if not isinstance(t, str) or not re.fullmatch(r"[^\s#]+", t)]

    for key in ("sources", "generated"):
        if not isinstance(post.get(key), list):
            out.append(f"{key} must be a list (empty when there is nothing to list)")

    if first_title is not None and isinstance(post.get("hook"), str) and not same_text(post["hook"], first_title):
        out.append(f'hook is "{post["hook"]}" but the first scene reads "{first_title}"')

    chapters = post.get("chapters")
    if chapters is not None:
        times = [seconds(c.get("at")) if isinstance(c, dict) else None for c in chapters] if isinstance(chapters, list) else [None]
        if None in times or any(not str(c.get("title", "")).strip() for c in chapters):
            out.append('each chapter needs "at" as m:ss and a title')
        else:
            if len(times) < CHAPTERS_MIN:
                out.append(f"chapters needs at least {CHAPTERS_MIN} entries, or none")
            if times and times[0] != 0:
                out.append("the first chapter must be at 0:00")
            out += [f'chapter "{c["title"]}" starts under {CHAPTER_GAP} s after the one before it'
                    for c, a, b in zip(chapters[1:], times, times[1:]) if b - a < CHAPTER_GAP]
            out += [f'chapter "{c["title"]}" at {c["at"]} is past the end of the video ({duration:.0f} s)'
                    for c, t in zip(chapters, times) if t >= duration]
    return out


def post_text(post, credits):
    parts = [post["title"], post["caption"], " ".join("#" + t for t in post["hashtags"])]
    if post.get("chapters"):
        parts.append("\n".join(["Chapters"] + [f'{c["at"]} {c["title"]}' for c in post["chapters"]]))
    if post["sources"]:
        parts.append("\n".join(["Sources"] + [f"- {s}" for s in post["sources"]]))
    parts += [f"Credits\n{c}" for c in credits]
    if post["generated"]:
        parts.append("AI-generated: " + ", ".join(post["generated"]))
    return "\n\n".join(parts) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("post")
    ap.add_argument("--video", required=True)
    ap.add_argument("--scenes", help="scenes.json of an explainer: the hook must match its first title")
    ap.add_argument("--cover-at", type=float, help="seconds into the video for cover.jpg")
    a = ap.parse_args()

    path = Path(a.post).resolve()
    post = load_json(path)
    duration = probe(a.video)["duration"]
    first = load_json(a.scenes)[0] if a.scenes else None
    found = problems(post, duration, first and first["title"])
    if found:
        raise SystemExit("\n".join(found))

    job = path.parent
    credits = [f.read_text().strip() for f in (job / "music" / "CREDITS.txt", job / "audio" / "CREDITS.txt") if f.exists()]
    (job / "post.txt").write_text(post_text(post, credits))
    at = a.cover_at if a.cover_at is not None else min(first["start"] + 1.5, first["end"] - 0.5) if first else 1.0
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, min(at, duration - 0.1)):.3f}", "-i", a.video,
         "-frames:v", "1", "-q:v", "2", job / "cover.jpg"])
    print(f"-> {job / 'post.txt'}\n-> {job / 'cover.jpg'} (frame at {at:.2f} s)")


if __name__ == "__main__":
    main()
