#!/bin/bash
# Sort PR comments into folder structure matching file tree
# Usage: ./sort_comments_by_filetree.sh INPUT_FILE [REPO_PATH]
# Example: ./sort_comments_by_filetree.sh backend_inline_comments.ndjson /path/to/backend

INPUT="${1:?Usage: $0 INPUT_FILE}"

# Output to .claude/pr-review-comments/sorted/
OUTPUT_DIR=".claude/pr-review-comments/sorted"

# Find jq - use full path
JQ_CMD="/c/Users/ItamarZand/bin/jq.exe"
if [ ! -f "$JQ_CMD" ]; then
    JQ_CMD="jq"
    if ! command -v jq &> /dev/null; then
        echo "Error: jq not found. Install it first."
        exit 1
    fi
fi

if [ ! -f "$INPUT" ]; then
    echo "Error: Input file '$INPUT' not found"
    exit 1
fi

echo "Sorting comments from: $INPUT"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Clean and create output directory
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Count total comments
TOTAL_COMMENTS=$("$JQ_CMD" -s 'length' "$INPUT")
echo "Total comments: $TOTAL_COMMENTS"

# Get unique file count
TOTAL_FILES=$("$JQ_CMD" -sr '[.[].file] | unique | length' "$INPUT")
echo "Total files with comments: $TOTAL_FILES"
echo ""

# Create summary file
echo "Creating summary..."
"$JQ_CMD" -s '
{
  generated_at: now | todate,
  source_file: $input_file,
  summary: {
    total_comments: length,
    total_files: ([.[].file] | unique | length),
    directories: ([.[].file | split("/") | .[:-1] | join("/")] | unique | length)
  },
  by_directory: (
    group_by(.file | split("/") | .[:-1] | join("/")) |
    map({
      directory: (.[0].file | split("/") | .[:-1] | join("/")),
      comment_count: length,
      files: ([.[].file] | unique)
    }) |
    sort_by(.directory)
  ),
  by_author: (
    group_by(.author) |
    map({
      author: .[0].author,
      comment_count: length
    }) |
    sort_by(-.comment_count)
  ),
  by_file: (
    group_by(.file) |
    map({
      file: .[0].file,
      comment_count: length
    }) |
    sort_by(-.comment_count) |
    .[0:20]
  )
}
' --arg input_file "$INPUT" "$INPUT" > "$OUTPUT_DIR/summary.json"

echo "Created: $OUTPUT_DIR/summary.json"

# Create directory structure and save comments per directory
echo ""
echo "Creating folder structure..."

# Get directories into temp file (strip Windows line endings)
TMPFILE=$(mktemp)
"$JQ_CMD" -sr '[.[].file | split("/") | .[:-1] | join("/")] | unique | .[]' "$INPUT" | tr -d '\r' > "$TMPFILE"

# Read into array from temp file
mapfile -t DIRECTORIES < "$TMPFILE"
rm -f "$TMPFILE"

echo "Processing ${#DIRECTORIES[@]} directories..."

for dir in "${DIRECTORIES[@]}"; do
    if [ -n "$dir" ]; then
        # Create directory
        mkdir -p "$OUTPUT_DIR/$dir"

        # Filter comments where file's DIRECT parent matches this directory
        "$JQ_CMD" -s --arg dir "$dir" '
        [.[] | select((.file | split("/") | .[:-1] | join("/")) == $dir)] |
        if length > 0 then
        {
          directory: $dir,
          generated_at: now | todate,
          comment_count: length,
          files: ([.[].file] | unique | sort),
          comments: (
            group_by(.file) |
            map({
              file: .[0].file,
              filename: (.[0].file | split("/") | .[-1]),
              comments: (. | sort_by(.created_at) | map({
                pr_number,
                author,
                body,
                line,
                original_line,
                diff_hunk,
                created_at,
                url
              }))
            }) |
            sort_by(.file)
          )
        }
        else empty end
        ' "$INPUT" > "$OUTPUT_DIR/$dir/comments.json"

        # Check if file was created and has content
        if [ -s "$OUTPUT_DIR/$dir/comments.json" ]; then
            COUNT=$("$JQ_CMD" '.comment_count' "$OUTPUT_DIR/$dir/comments.json")
            echo "  $dir/ ($COUNT comments)"
        else
            rm -f "$OUTPUT_DIR/$dir/comments.json"
        fi
    fi
done

# Create root-level comments file for files without directory
"$JQ_CMD" -s '
[.[] | select(.file | contains("/") | not)] |
if length > 0 then
{
  directory: "(root)",
  generated_at: now | todate,
  comment_count: length,
  files: ([.[].file] | unique | sort),
  comments: (
    group_by(.file) |
    map({
      file: .[0].file,
      filename: .[0].file,
      comments: (. | sort_by(.created_at) | map({
        pr_number,
        author,
        body,
        line,
        original_line,
        diff_hunk,
        created_at,
        url
      }))
    }) |
    sort_by(.file)
  )
}
else empty end
' "$INPUT" > "$OUTPUT_DIR/root_comments.json"

if [ -s "$OUTPUT_DIR/root_comments.json" ]; then
    COUNT=$("$JQ_CMD" '.comment_count' "$OUTPUT_DIR/root_comments.json")
    echo "  (root)/ ($COUNT comments)"
else
    rm -f "$OUTPUT_DIR/root_comments.json"
fi

echo ""
echo "=== Summary ==="
"$JQ_CMD" -r '"Total comments: \(.summary.total_comments)"' "$OUTPUT_DIR/summary.json"
"$JQ_CMD" -r '"Files with comments: \(.summary.total_files)"' "$OUTPUT_DIR/summary.json"
"$JQ_CMD" -r '"Directories created: \(.summary.directories)"' "$OUTPUT_DIR/summary.json"
echo ""
echo "=== Top commented files ==="
"$JQ_CMD" -r '.by_file[:5][] | "  \(.file): \(.comment_count) comments"' "$OUTPUT_DIR/summary.json"
echo ""
echo "=== Comments by author ==="
"$JQ_CMD" -r '.by_author[] | "  \(.author): \(.comment_count) comments"' "$OUTPUT_DIR/summary.json"
echo ""
echo "Done! Output saved to: $OUTPUT_DIR/"
echo ""
echo "Structure:"
echo "  $OUTPUT_DIR/"
echo "  ├── summary.json"
find "$OUTPUT_DIR" -name "comments.json" -type f 2>/dev/null | sort | while read f; do
    rel_path="${f#$OUTPUT_DIR/}"
    echo "  ├── $rel_path"
done
