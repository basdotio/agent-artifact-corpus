#!/usr/bin/env python3
"""
Code Review CLI - Collects commit data with diffs in TOON format
"""

import subprocess
import sys
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class CommitInfo:
    """Represents a single commit"""
    hash: str
    author: str
    date: str
    subject: str
    body: Optional[str]
    files_changed: int


def run_git(args: List[str]) -> str:
    """Run a git command and return output"""
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Git not found.", file=sys.stderr)
        sys.exit(1)


def get_commits_in_range(start_hash: str) -> List[str]:
    """Get list of commit hashes from start_hash to HEAD (oldest first)"""
    # Get commits from start_hash to HEAD, one per line
    output = run_git([
        'log',
        '--format=%H',
        '--reverse',
        f'{start_hash}^..HEAD'
    ])
    return [h.strip() for h in output.strip().split('\n') if h.strip()]


def get_commit_info(commit_hash: str) -> CommitInfo:
    """Get commit metadata and diff"""
    # Get commit metadata
    format_str = '%H%n%an%n%ai%n%s%n%b'
    output = run_git(['show', '-s', f'--format={format_str}', commit_hash])
    lines = output.split('\n')

    full_hash = lines[0] if len(lines) > 0 else commit_hash
    author = lines[1] if len(lines) > 1 else ''
    date_full = lines[2] if len(lines) > 2 else ''
    subject = lines[3] if len(lines) > 3 else ''
    body = '\n'.join(lines[4:]).strip() or None

    # Extract just the date part (YYYY-MM-DD)
    date = date_full.split()[0] if date_full else ''

    # Get file count
    files_output = run_git(['show', '--name-only', '--format=', commit_hash])
    files_changed = len([f for f in files_output.strip().split('\n') if f.strip()])

    return CommitInfo(
        hash=full_hash,
        author=author,
        date=date,
        subject=subject,
        body=body,
        files_changed=files_changed
    )


def get_commit_diff(commit_hash: str) -> str:
    """Get diff for a single commit"""
    return run_git(['show', '--patch', '--stat', '--color=never', commit_hash])


def escape_toon(s: Optional[str]) -> str:
    """Escape a string for TOON format"""
    if s is None:
        return 'null'

    # Always quote strings with special characters
    needs_quote = any(c in s for c in [',', ':', '"', '\\', '\n', '\r', '\t', '[', ']', '{', '}'])

    if needs_quote or not s:
        # Escape special characters
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('\n', '\\n')
        s = s.replace('\r', '\\r')
        s = s.replace('\t', '\\t')
        return f'"{s}"'
    return s


def format_commits_as_toon(commits: List[CommitInfo], branch: str, commit_range: str) -> str:
    """Format commits as TOON output"""
    lines = []

    # Header with schema
    lines.append(f'commits[{len(commits)}]{{hash,author,date,subject,body,filesChanged}}:')

    for commit in commits:
        fields = [
            commit.hash,
            commit.author,
            commit.date,
            escape_toon(commit.subject),
            escape_toon(commit.body) if commit.body else 'null',
            str(commit.files_changed)
        ]
        lines.append(f'  {",".join(fields)}')

    # Add metadata
    commit_list = ','.join(c.hash for c in commits)
    lines.append(f'commitList[{len(commits)}]: {commit_list}')
    lines.append(f'branch: {branch}')
    lines.append(f'commitRange: {commit_range}')
    lines.append(f'totalCommits: {len(commits)}')

    return '\n'.join(lines)


def get_current_branch() -> str:
    """Get current branch name"""
    try:
        output = run_git(['rev-parse', '--abbrev-ref', 'HEAD'])
        return output.strip()
    except Exception:
        return 'HEAD'


def print_usage():
    print("""
Code Review CLI

Usage:
  cli.py prepare <commit-hash>
  cli.py get-diff <commit-hash>

Commands:
  prepare <commit-hash>
    Collect commit metadata from the specified commit to HEAD

  get-diff <commit-hash>
    Get the diff for a single commit

Examples:
  cli.py prepare abc123
  cli.py get-diff abc123
""", file=sys.stderr)


def main():
    args = sys.argv[1:]

    if not args or '--help' in args or '-h' in args:
        print_usage()
        sys.exit(0)

    command = args[0]

    if command == 'prepare':
        if len(args) < 2:
            print("Error: commit hash is required", file=sys.stderr)
            print("Usage: cli.py prepare <commit-hash>", file=sys.stderr)
            sys.exit(1)

        commit_hash = args[1]

        # Get commits in range
        commit_hashes = get_commits_in_range(commit_hash)

        if not commit_hashes:
            print(f"Error: No commits found from {commit_hash} to HEAD", file=sys.stderr)
            sys.exit(1)

        # Collect commit info with diffs
        commits = []
        for h in commit_hashes:
            commits.append(get_commit_info(h))

        # Get metadata
        branch = get_current_branch()
        commit_range = f'{commit_hash}^..HEAD'

        # Output TOON format
        print(format_commits_as_toon(commits, branch, commit_range))

    elif command == 'get-diff':
        if len(args) < 2:
            print("Error: commit hash is required", file=sys.stderr)
            print("Usage: cli.py get-diff <commit-hash>", file=sys.stderr)
            sys.exit(1)

        commit_hash = args[1]
        print(get_commit_diff(commit_hash))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Run with --help to see available commands", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
