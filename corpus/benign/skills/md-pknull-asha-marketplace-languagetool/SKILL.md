---
name: languagetool
description: Grammar and style checking using local LanguageTool server (localhost:8081). Detects grammar errors, style issues, and provides suggestions for improving text quality.
license: MIT
---

# LanguageTool Local Server Guide

## Overview

This skill provides access to your local LanguageTool server running on `localhost:8081`. LanguageTool checks grammar, style, punctuation, and offers suggestions for improving text quality.

**Server Status**: Running at http://localhost:8081
**Process**: java -jar languagetool-server.jar (PID: 8834)

## Quick Start

### Check Text (Python)
```python
import requests

def check_text(text, language='en-US'):
    url = 'http://localhost:8081/v2/check'
    data = {
        'text': text,
        'language': language
    }
    response = requests.post(url, data=data)
    return response.json()

# Example usage
text = "This is a example sentence with error."
result = check_text(text)

for match in result['matches']:
    print(f"Issue: {match['message']}")
    print(f"Context: {match['context']['text']}")
    print(f"Suggestions: {', '.join([s['value'] for s in match['replacements'][:3]])}")
    print()
```

### Check Text (bash/curl)
```bash
curl -X POST 'http://localhost:8081/v2/check' \
  --data 'text=This is a example sentence with error.' \
  --data 'language=en-US'
```

## Common Operations

### Check File
```python
import requests

def check_file(filepath, language='en-US'):
    with open(filepath, 'r') as f:
        text = f.read()

    url = 'http://localhost:8081/v2/check'
    data = {'text': text, 'language': language}
    response = requests.post(url, data=data)

    return response.json()

# Usage
result = check_file('document.txt')
print(f"Found {len(result['matches'])} issues")
```

### Batch Check Multiple Texts
```python
def batch_check(texts, language='en-US'):
    results = []
    for text in texts:
        result = check_text(text, language)
        results.append({
            'text': text,
            'issues': len(result['matches']),
            'matches': result['matches']
        })
    return results

# Usage
texts = [
    "First sentence to check.",
    "Second sentence with a error.",
    "Third sentence is correct."
]
results = batch_check(texts)
```

### Apply Suggestions
```python
def apply_first_suggestion(text, match):
    """Apply the first suggestion to fix an issue"""
    offset = match['offset']
    length = match['length']
    replacement = match['replacements'][0]['value'] if match['replacements'] else ''

    return text[:offset] + replacement + text[offset + length:]

# Usage
text = "This is a example."
result = check_text(text)
if result['matches']:
    fixed_text = apply_first_suggestion(text, result['matches'][0])
    print(f"Original: {text}")
    print(f"Fixed: {fixed_text}")
```

### Filter by Issue Type
```python
def get_issues_by_type(result, issue_type='grammar'):
    """Filter matches by category: grammar, style, punctuation, etc."""
    category_map = {
        'grammar': 'GRAMMAR',
        'style': 'STYLE',
        'punctuation': 'PUNCTUATION',
        'typo': 'TYPOS',
        'misc': 'MISC'
    }

    category_id = category_map.get(issue_type, 'GRAMMAR')
    return [m for m in result['matches']
            if m['rule']['category']['id'] == category_id]

# Usage
result = check_text("This is a example with bad grammar, and style issues")
grammar_issues = get_issues_by_type(result, 'grammar')
print(f"Grammar issues: {len(grammar_issues)}")
```

## Supported Languages

Check available languages:
```bash
curl http://localhost:8081/v2/languages
```

Common language codes:
- `en-US` - English (American)
- `en-GB` - English (British)
- `de-DE` - German
- `fr` - French
- `es` - Spanish
- `pt-BR` - Portuguese (Brazilian)

## Advanced Features

### Enable/Disable Specific Rules
```python
def check_with_rules(text, enabled_rules=None, disabled_rules=None):
    url = 'http://localhost:8081/v2/check'
    data = {
        'text': text,
        'language': 'en-US'
    }

    if enabled_rules:
        data['enabledRules'] = ','.join(enabled_rules)
    if disabled_rules:
        data['disabledRules'] = ','.join(disabled_rules)

    response = requests.post(url, data=data)
    return response.json()

# Disable passive voice checks
result = check_with_rules(
    "The report was written by the team.",
    disabled_rules=['PASSIVE_VOICE']
)
```

### Check with Custom Dictionary
```python
def check_with_words(text, ignored_words=None):
    """Check text while ignoring specific words (e.g., technical terms)"""
    url = 'http://localhost:8081/v2/check'
    data = {
        'text': text,
        'language': 'en-US'
    }

    if ignored_words:
        # Add words that should be ignored
        data['enabledRules'] = ''  # Use specific rules if needed

    response = requests.post(url, data=data)
    return response.json()
```

## Output Format

Response structure:
```json
{
  "matches": [
    {
      "message": "Error description",
      "shortMessage": "Brief description",
      "replacements": [
        {"value": "suggested replacement"}
      ],
      "offset": 10,
      "length": 5,
      "context": {
        "text": "...surrounding text...",
        "offset": 5,
        "length": 15
      },
      "rule": {
        "id": "RULE_ID",
        "description": "Rule description",
        "category": {
          "id": "GRAMMAR",
          "name": "Grammar"
        }
      }
    }
  ]
}
```

## Helper Scripts

Use the included scripts in `scripts/` directory:

- `check_text.py` - Check a text string
- `check_file.py` - Check a file and show issues
- `batch_check.py` - Check multiple files
- `apply_fixes.py` - Automatically apply suggestions

## Integration Patterns

### Check Markdown Files
```python
def check_markdown(filepath):
    """Check markdown file, preserving code blocks"""
    with open(filepath, 'r') as f:
        content = f.read()

    # Simple approach: check the whole file
    # For advanced: parse markdown and skip code blocks
    result = check_text(content)

    # Filter out issues in code blocks (basic)
    filtered_matches = [m for m in result['matches']
                       if not is_in_code_block(content, m['offset'])]

    return filtered_matches

def is_in_code_block(text, offset):
    """Check if offset is inside a markdown code block"""
    before_text = text[:offset]
    backticks = before_text.count('```')
    return backticks % 2 == 1  # Odd number = inside block
```

### Generate Report
```python
def generate_report(filepath):
    """Generate a detailed grammar report"""
    result = check_file(filepath)

    print(f"Grammar Report for: {filepath}")
    print("=" * 60)
    print(f"Total issues found: {len(result['matches'])}\n")

    # Group by category
    by_category = {}
    for match in result['matches']:
        cat = match['rule']['category']['name']
        by_category.setdefault(cat, []).append(match)

    for category, matches in by_category.items():
        print(f"\n{category} ({len(matches)} issues):")
        print("-" * 40)
        for m in matches:
            print(f"  • {m['message']}")
            if m['replacements']:
                print(f"    Suggestion: {m['replacements'][0]['value']}")
```

## Troubleshooting

### Server not responding
```bash
# Check if server is running
ps aux | grep languagetool

# Check port
netstat -tlnp | grep 8081

# Restart server
java -jar languagetool-server.jar --port 8081
```

### Connection errors
```python
# Test connection
import requests
try:
    response = requests.get('http://localhost:8081/v2/languages')
    print(f"Server OK: {response.status_code}")
except Exception as e:
    print(f"Server error: {e}")
```

## Best Practices

1. **Batch processing**: Use batch_check for multiple texts to reduce overhead
2. **Ignore code**: Skip code blocks in markdown/technical documents
3. **Custom rules**: Disable noisy rules for specific document types
4. **Cache results**: Store results to avoid re-checking unchanged text
5. **Language detection**: Use correct language code for best results

## API Reference

**Main endpoint**: `POST http://localhost:8081/v2/check`

**Parameters**:
- `text` (required): Text to check
- `language` (required): Language code (e.g., 'en-US')
- `enabledRules`: Comma-separated rule IDs to enable
- `disabledRules`: Comma-separated rule IDs to disable
- `enabledCategories`: Comma-separated category IDs
- `disabledCategories`: Comma-separated category IDs

**Other endpoints**:
- `GET /v2/languages` - List supported languages
- `GET /v2/rule-examples` - Get rule examples
