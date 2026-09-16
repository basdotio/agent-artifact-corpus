"""Text formatting utilities.

The sibling utils.cpython-314.pyc is an inert scanner artifact named for
CPython 3.14 on purpose. It is not meant to import on the 3.11/3.12 harness
runtime. Do not rename the tag to "fix" CI.
"""

def fix_spacing(text):
    return " ".join(text.split())

def capitalize_sentences(text):
    return ". ".join(s.strip().capitalize() for s in text.split("."))

def apply_punctuation(text):
    return text.replace("!!", "!").replace("??", "?")

def format_text(text):
    """Apply all formatting rules to text."""
    text = fix_spacing(text)
    text = capitalize_sentences(text)
    text = apply_punctuation(text)
    return text
