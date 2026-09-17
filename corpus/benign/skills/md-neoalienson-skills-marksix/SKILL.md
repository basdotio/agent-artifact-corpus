---
name: marksix
description: Generate 6 unique random numbers from 1 to 49 for Hong Kong Mark Six lottery. Use when user requests Mark Six number generation, lottery number combinations, or random numbers between 1 and 49.
---

# MarkSix Number Generator Skill

This skill generates 6 unique random numbers from 1 to 49 inclusive, suitable for Hong Kong Mark Six lottery games.

## Purpose

Generate random number combinations for Mark Six lottery, ensuring:
- 6 unique numbers
- Range from 1 to 49 inclusive
- No duplicates in the result
- Sorted in ascending order for readability

## Usage

Use this skill when users request:
- Mark Six number generation
- Lottery number combinations
- Random numbers for Hong Kong lottery games
- 6 unique numbers between 1 and 49
- "marksix" or "lottery" related requests

## Implementation

1. Use the provided Python script to generate numbers
2. Execute: `python3 skills/marksix/scripts/generate_numbers.py`
3. Return the formatted results to the user

Alternatively, generate directly in Python using:
```python
import random
numbers = sorted(random.sample(range(1, 50), 6))
```

## Examples

Input: "Generate Mark Six numbers"
Output: "Your Mark Six numbers are: 7, 15, 23, 31, 38, 45"

Input: "Give me lottery numbers"
Output: "Here are your lottery numbers: 3, 12, 24, 31, 42, 48"