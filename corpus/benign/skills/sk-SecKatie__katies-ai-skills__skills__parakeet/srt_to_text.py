#!/usr/bin/env python3
"""
Convert SRT subtitle files to plain text.

Strips subtitle numbers, timestamps, and formatting to produce clean text
suitable for further processing (e.g., LLM cleanup into article format).

Usage:
    python srt_to_text.py <input.srt> [--output <output.txt>]
    cat input.srt | python srt_to_text.py

Examples:
    python srt_to_text.py podcast.srt
    python srt_to_text.py interview.srt --output interview.txt
    python srt_to_text.py podcast.srt | llm -m gpt-5.2 "Clean this up"
"""

import argparse
import re
import sys
from pathlib import Path


def parse_srt(content: str) -> list[str]:
    """
    Parse SRT content and extract text lines.

    SRT format:
        1
        00:00:00,000 --> 00:00:03,500
        Text content here

        2
        00:00:03,500 --> 00:00:08,200
        More text content
    """
    lines = []

    # Pattern to match subtitle numbers (just digits on their own line)
    number_pattern = re.compile(r'^\d+$')

    # Pattern to match timestamps (00:00:00,000 --> 00:00:00,000)
    timestamp_pattern = re.compile(
        r'^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}$'
    )

    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines, subtitle numbers, and timestamps
        if not line:
            continue
        if number_pattern.match(line):
            continue
        if timestamp_pattern.match(line):
            continue

        # This is actual subtitle text
        lines.append(line)

    return lines


def srt_to_text(content: str, paragraph_gap: int = 0) -> str:
    """
    Convert SRT content to plain text.

    Args:
        content: Raw SRT file content
        paragraph_gap: Number of blank lines between subtitle blocks (0 = single space)

    Returns:
        Plain text with subtitle content joined together
    """
    lines = parse_srt(content)

    if paragraph_gap > 0:
        # Join with paragraph breaks
        separator = '\n' * (paragraph_gap + 1)
        return separator.join(lines)
    else:
        # Join with single spaces, treating each subtitle as a continuation
        return ' '.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Convert SRT subtitle files to plain text',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'input',
        nargs='?',
        help='Input SRT file (reads from stdin if not provided)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file (prints to stdout if not provided)'
    )
    parser.add_argument(
        '--paragraphs', '-p',
        action='store_true',
        help='Preserve subtitle blocks as separate paragraphs'
    )

    args = parser.parse_args()

    # Read input
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        content = input_path.read_text(encoding='utf-8')
    else:
        # Read from stdin
        if sys.stdin.isatty():
            print("Error: No input file provided and no stdin", file=sys.stderr)
            parser.print_help()
            sys.exit(1)
        content = sys.stdin.read()

    # Convert
    paragraph_gap = 1 if args.paragraphs else 0
    text = srt_to_text(content, paragraph_gap)

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(text, encoding='utf-8')
        print(f"Written to: {args.output}", file=sys.stderr)
    else:
        print(text)


if __name__ == '__main__':
    main()
