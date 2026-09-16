#!/usr/bin/env python3
"""
Clean Obsidian markdown files for text-to-speech conversion.

This script removes markdown formatting, links, special characters, and other
elements that don't translate well to speech, while preserving the actual content.
"""

import re
import sys
import argparse
from pathlib import Path


def clean_obsidian_for_tts(content: str) -> str:
    """
    Clean markdown content for text-to-speech conversion.

    Args:
        content: Raw markdown content string

    Returns:
        Cleaned text suitable for TTS
    """
    # Remove YAML frontmatter (between --- markers)
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL | re.MULTILINE)

    # Remove HTML comments
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

    # Remove code blocks (fenced with ``` or ~~~)
    content = re.sub(r'^```.*?^```', '', content, flags=re.DOTALL | re.MULTILINE)
    content = re.sub(r'^~~~.*?^~~~', '', content, flags=re.DOTALL | re.MULTILINE)

    # Remove inline code (backticks) - keep the content
    content = re.sub(r'`([^`]+)`', r'\1', content)

    # Remove images ![alt](url) or ![alt][ref] - but keep alt text
    content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', content)
    content = re.sub(r'!\[([^\]]*)\]\[[^\]]+\]', r'\1', content)

    # Convert links [text](url) to just text
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)

    # Convert reference links [text][ref] to just text
    content = re.sub(r'\[([^\]]+)\]\[[^\]]+\]', r'\1', content)

    # Remove Obsidian wiki links [[link]] or [[link|alias]] - keep alias or link text
    content = re.sub(r'\[\[([^\|\]]+)\|([^\]]+)\]\]', r'\2', content)  # [[link|alias]] -> alias
    content = re.sub(r'\[\[([^\]]+)\]\]', r'\1', content)  # [[link]] -> link

    # Remove header markers but keep text
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)

    # Remove bold **text** or __text__
    content = re.sub(r'\*\*([^\*]+)\*\*', r'\1', content)
    content = re.sub(r'__([^_]+)__', r'\1', content)

    # Remove italic *text* or _text_
    content = re.sub(r'\*([^\*]+)\*', r'\1', content)
    content = re.sub(r'_([^_]+)_', r'\1', content)

    # Remove strikethrough ~~text~~
    content = re.sub(r'~~([^~]+)~~', r'\1', content)

    # Remove blockquote markers
    content = re.sub(r'^>\s*', '', content, flags=re.MULTILINE)

    # Remove horizontal rules
    content = re.sub(r'^[\*\-_]{3,}\s*$', '', content, flags=re.MULTILINE)

    # Remove task list markers
    content = re.sub(r'^[\s]*[-\*\+]\s+\[[ xX]\]\s+', '', content, flags=re.MULTILINE)

    # Remove unordered list markers
    content = re.sub(r'^[\s]*[-\*\+]\s+', '', content, flags=re.MULTILINE)

    # Remove ordered list markers
    content = re.sub(r'^[\s]*\d+\.\s+', '', content, flags=re.MULTILINE)

    # Remove HTML tags
    content = re.sub(r'<[^>]+>', '', content)

    # Remove emojis and special unicode characters (keep basic punctuation)
    # This pattern keeps ASCII printable chars, newlines, tabs
    content = ''.join(char for char in content if ord(char) < 128 or char in '\n\t')

    # Remove URLs that might still be standalone
    content = re.sub(r'https?://[^\s]+', '', content)

    # Remove excessive whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 newlines
    content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces to single space

    # Remove leading/trailing whitespace from lines
    lines = [line.strip() for line in content.split('\n')]
    content = '\n'.join(lines)

    # Remove empty lines at start and end
    content = content.strip()

    return content


def main():
    parser = argparse.ArgumentParser(
        description='Clean Obsidian markdown files for text-to-speech conversion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean a single file
  %(prog)s input.md -o output.txt

  # Clean and print to stdout
  %(prog)s input.md

  # Clean from stdin
  cat input.md | %(prog)s
        """
    )

    parser.add_argument(
        'input_file',
        nargs='?',
        type=str,
        help='Input markdown file (if not provided, reads from stdin)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file path (if not provided, prints to stdout)'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Print statistics about the cleaning process'
    )

    args = parser.parse_args()

    # Read input
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"Error: File '{args.input_file}' not found", file=sys.stderr)
            sys.exit(1)
        with open(input_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    else:
        # Read from stdin
        original_content = sys.stdin.read()

    # Clean content
    cleaned_content = clean_obsidian_for_tts(original_content)

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)

        if args.stats:
            print(f"Cleaned file written to: {output_path}", file=sys.stderr)
    else:
        # Print to stdout
        print(cleaned_content)

    # Print statistics if requested
    if args.stats:
        orig_chars = len(original_content)
        clean_chars = len(cleaned_content)
        orig_words = len(original_content.split())
        clean_words = len(cleaned_content.split())
        orig_lines = original_content.count('\n') + 1
        clean_lines = cleaned_content.count('\n') + 1

        print("\nCleaning Statistics:", file=sys.stderr)
        print(f"  Characters: {orig_chars:,} -> {clean_chars:,} ({orig_chars - clean_chars:,} removed)", file=sys.stderr)
        print(f"  Words: {orig_words:,} -> {clean_words:,} ({orig_words - clean_words:,} removed)", file=sys.stderr)
        print(f"  Lines: {orig_lines:,} -> {clean_lines:,}", file=sys.stderr)


if __name__ == '__main__':
    main()
