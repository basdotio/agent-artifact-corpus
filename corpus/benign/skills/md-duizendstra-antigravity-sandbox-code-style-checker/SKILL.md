---
name: code-style-checker
description: Checks python code for use of print statements and suggests using logging instead. Use this when the user asks to review code or check for bad practices.
---
# Code Style Checker Skill

This skill analyzes Python code to detect direct usage of `print()` statements, which are often non-production ready. It suggests replacing them with proper logging.

## Instructions
1. Run the checking script on the specified file or directory.
2. If the script returns an exit code of 1, it means violations were found. Report these to the user.
3. If the script returns 0, the code passes this check.

## Script Usage
Run the following command:
`python .agent/skills/code-style-checker/scripts/check.py <path_to_file_or_dir>`

## Output Interpretation
- **Output lines**: Will list the files and line numbers where `print()` was found.
- **Exit Code 1**: Violations found.
- **Exit Code 0**: No violations.
