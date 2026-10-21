"""CLI: extract structured JSON from a .docx file via the local model.

Usage:
    py extract_docx.py <docx_path> <schema_json_path> <output_json_path>

schema_json_path points to a JSON file mapping field names to type strings
(string/integer/number/boolean/array/object), the same schema format
local_llm.extract.extract_json expects.

SIZE CAP: this CLI caps .docx extraction at CLI_MAX_BYTES (384,000 bytes),
CLI_MAX_RATIO (100:1 compression) and CLI_MAX_TEXT_CHARS (384,000 characters
of extracted text).

WHAT THE MEMBER CAPS APPLY TO, stated narrowly because the narrow form is what
ships: the byte and ratio caps screen the archive members this tool PARSES OR
DECOMPRESSES -- in practice word/document.xml, plus the .xml and .rels members
swept on the way to it. A member that is never opened -- an embedded image, for
instance -- is NOT screened and may legitimately exceed these caps. Screening
is PER MEMBER, not cumulative: a document is not refused for the sum of its
parts.

All three constants are declared HERE as literals rather than imported from
docx_text, so a change to that module's defaults cannot silently change what
this CLI accepts. The values happen to match the MCP tools' caps because this
CLI feeds the same single extract_json model call, so the same bound applies
for the same reason -- but it is an independent decision, not an alias.
Documents whose parsed content passes a cap are REJECTED, not truncated --
split the document or extract a section.
"""

import json
import sys

from local_llm.docx_text import extract_text
from local_llm.extract import extract_json

CLI_MAX_BYTES = 384000
CLI_MAX_RATIO = 100
CLI_MAX_TEXT_CHARS = 384000


def main():
    if len(sys.argv) != 4:
        print("Usage: py extract_docx.py <docx_path> <schema_json_path> <output_json_path>")
        sys.exit(1)
    docx_path, schema_path, output_path = sys.argv[1:4]

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    text = extract_text(docx_path, max_bytes=CLI_MAX_BYTES,
                        max_ratio=CLI_MAX_RATIO,
                        max_text_chars=CLI_MAX_TEXT_CHARS)
    if not text.strip():
        # Nothing was read from the body of word/document.xml; do not send
        # an empty document to the model as if it were the content.
        raise ValueError(
            "the .docx has no extractable text in the body of "
            "word/document.xml (images, headers, footers, footnotes and "
            "comments are not read): " + docx_path)
    result = extract_json(text, schema)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("Wrote", output_path)


if __name__ == "__main__":
    main()
