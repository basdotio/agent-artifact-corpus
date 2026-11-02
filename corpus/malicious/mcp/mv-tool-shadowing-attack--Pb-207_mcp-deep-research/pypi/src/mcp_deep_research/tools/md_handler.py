import re
import pyperclip


def bing_query_md_handler(markdown_text: str) -> str:
    # This regex pattern matches numbered markdown headings followed by their content
    pattern = r'(\d+\.\s+##\s+\[[^\]]*\]\([^)]*\).*?)(?=\d+\.\s+##|$)'

    # Find all matches in the input string (including multiline)
    matches = re.findall(pattern, markdown_text, re.DOTALL)

    # Process each match to clean up extra URLs and whitespace lines
    cleaned_matches = []
    for match in matches:
        # Remove any extra URLs that appear after the main link in the same line
        cleaned = re.sub(r'(?<=\))\s*https?://[^\s]+', '', match)
        # Remove lines starting with whitespace (spaces or tabs)
        cleaned = '\n'.join(line for line in cleaned.split('\n')
                           if not re.match(r'^\s+', line))
        cleaned_matches.append(cleaned.strip())

    # Join all cleaned matches with double newlines to separate them
    return '\n\n'.join(cleaned_matches)


def google_query_md_handler(text: str) -> str:
    # Step 1: Remove everything before first "###" but keep "###"
    result = re.sub(r'^.*?(?=###)', '', text, count=1, flags=re.DOTALL)

    # Step 2: Remove content between each "[Save]" and following "##", keep "##", remove "[Save]"
    result = re.sub(r'\[Save\].*?(?=##)', '', result, flags=re.DOTALL)

    # Step 3: Remove "**Previous**" and everything after it
    result = re.sub(r'\*\*Previous\*\*.*', '', result, flags=re.DOTALL)

    # Step 4: Replace single newlines before "## Related searches" with spaces, keep multiple newlines
    # First split the text into parts before and after "## Related searches"
    parts = re.split(r'(## Related searches)', result, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) > 1:
        before, keyword, after = parts
        # Replace single newlines with space in the before part
        before = re.sub(r'(?<!\n)\n(?!\n)', ' ', before)
        result = before + keyword + after

    # Step 5: Replace multiple spaces with single space
    result = re.sub(r' +', ' ', result)

    return result.strip()


def article_md_handler(content: str) -> str:
    """
    Process markdown content by:
    1. Removing everything before the first '#' at line start, keeping the '#'
    2. Replacing single newlines with spaces (preserving consecutive newlines)
    3. Collapsing multiple spaces into single space

    Args:
        content: Input string to process

    Returns:
        Processed string
    """
    # Find the first line starting with '#'
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('#'):
            # Keep from this line onward
            lines = lines[i:]
            break

    # Rebuild content from remaining lines
    processed = '\n'.join(lines)

    # Replace single newlines with spaces, keep consecutive newlines
    processed = re.sub(r'(?<!\n)\n(?!\n)', ' ', processed)

    # Collapse multiple spaces to single space
    processed = re.sub(r' +', ' ', processed)

    return processed


# 示例用法
if __name__ == "__main__":
    # 读取剪贴板内容
    sample_text = pyperclip.paste()
    results = google_query_md_handler(sample_text)
    print(results)