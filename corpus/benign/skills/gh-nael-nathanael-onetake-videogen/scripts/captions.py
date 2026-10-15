"""Word-level "pop" captions as an ASS subtitle file (burned in by ffmpeg/libass)."""

import re
from pathlib import Path

MAX_WORDS = 6
PORTRAIT_MAX_WORDS = 4
FONT = "Plus Jakarta Sans ExtraBold"
PAPER = "&H00F7FDFF"  # caption text colour (ASS &HAABBGGRR), same as the Pop style


def _ass_time(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def group_lines(words, max_words=MAX_WORDS):
    """Short caption lines, broken on punctuation, pauses and length."""
    lines, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if (len(cur) >= max_words or re.search(r"[.,!?;:]$", w["text"])
                or not nxt or nxt["start"] - w["end"] > 0.35):
            lines.append(cur)
            cur = []
    return lines


def write_ass(words, path, accent="&H0000B3FF", width=1280, height=720):
    """
    words: [{"text", "start", "end"}] on the OUTPUT timeline.
    accent: ASS colour &HAABBGGRR for the active word (default warm yellow #FFB300).
    Type is sized from the short side. A portrait frame gets shorter lines, narrower margins and
    captions raised clear of the controls a phone app draws over the bottom of the video.
    """
    portrait = height > width
    short = min(width, height)
    size, box = round(short * 0.065), round(short / 60)
    side = round(short * (56 if portrait else 80) / 720)
    bottom = round(height * (0.19 if portrait else 0.075))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,{FONT},{size},&H00F7FDFF,&H00F7FDFF,&H001F1414,&H001F1414,0,0,0,0,100,100,0,0,3,{box},0,2,{side},{side},{bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    lines = group_lines(words, PORTRAIT_MAX_WORDS if portrait else MAX_WORDS)
    for n, line in enumerate(lines):
        # Linger after the last word, but never overlap the next line.
        line_end = line[-1]["end"] + 0.25
        if n + 1 < len(lines):
            line_end = min(line_end, lines[n + 1][0]["start"])
        for k, w in enumerate(line):
            start = line[0]["start"] if k == 0 else w["start"]
            end = line[k + 1]["start"] if k + 1 < len(line) else line_end
            parts = []
            for j, x in enumerate(line):
                t = _esc(x["text"])
                if j == k:
                    # active word: colour eases in with a brief pop that settles back to 100%
                    # (the opaque box is drawn per word, so a held scale would leave a step in it)
                    parts.append(r"{\t(0,70,0.5,\c" + accent + r"&\fscx110\fscy110)\t(70,200,\fscx100\fscy100)}" + t + r"{\r}")
                elif j == k - 1:
                    # previous word's colour eases back instead of snapping
                    parts.append(r"{\c" + accent + r"&\t(0,150,\c" + PAPER + r"&)}" + t + r"{\r}")
                else:
                    parts.append(t)
            fx = r"{\fad(120,0)}" if k == 0 else ""
            events.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Pop,,0,0,0,,{fx}{' '.join(parts)}")
    Path(path).write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return path


def ass_filter(ass_path, fonts_dir):
    """ffmpeg filter string that burns the ASS file with the bundled fonts."""
    esc = lambda p: str(p).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return f"subtitles=filename='{esc(ass_path)}':fontsdir='{esc(fonts_dir)}'"
