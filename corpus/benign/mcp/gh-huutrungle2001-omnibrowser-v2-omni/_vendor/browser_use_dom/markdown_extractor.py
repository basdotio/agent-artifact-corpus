"""Reader-only markdown functions from browser-use; MIT, see LICENSE."""
import json
import re

def convert_html_to_markdown(page_html: str, extract_images: bool = False) -> tuple[str, int, int]:
	"""Convert serialized page HTML to filtered markdown.

	Returns:
	    tuple: (filtered_markdown, initial_markdown_chars, chars_filtered)
	"""
	from markdownify import markdownify as md

	# 'td', 'th', and headings are the only elements where markdownify sets the _inline context,
	# which causes img elements to be stripped to just alt text when keep_inline_images_in=[]
	_keep_inline_images_in = ['td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'] if extract_images else []
	content = md(
		page_html,
		heading_style='ATX',  # Use # style headings
		strip=['script', 'style'],  # Remove these tags
		bullets='-',  # Use - for unordered lists
		code_language='',  # Don't add language to code blocks
		escape_asterisks=False,  # Don't escape asterisks (cleaner output)
		escape_underscores=False,  # Don't escape underscores (cleaner output)
		escape_misc=False,  # Don't escape other characters (cleaner output)
		autolinks=False,  # Don't convert URLs to <> format
		default_title=False,  # Don't add default title attributes
		keep_inline_images_in=_keep_inline_images_in,  # Include image src URLs when extract_images=True
	)

	initial_markdown_length = len(content)

	# Apply light preprocessing to clean up excessive whitespace
	content, chars_filtered = _preprocess_markdown_content(content)

	return content, initial_markdown_length, chars_filtered


def _preprocess_markdown_content(content: str, max_newlines: int = 3) -> tuple[str, int]:
	"""
	Light preprocessing of markdown output - minimal cleanup with JSON blob removal.

	Args:
	    content: Markdown content to lightly filter
	    max_newlines: Maximum consecutive newlines to allow

	Returns:
	    tuple: (filtered_content, chars_filtered)
	"""
	original_length = len(content)

	# Remove JSON blobs (common in SPAs like LinkedIn, Facebook, etc.)
	# These are often embedded as `{"key":"value",...}` and can be massive
	# Match JSON objects/arrays that are at least 100 chars long
	# This catches SPA state/config data without removing small inline JSON
	content = re.sub(r'`\{["\w].*?\}`', '', content, flags=re.DOTALL)  # Remove JSON in code blocks
	content = re.sub(r'\{"\$type":[^}]{100,}\}', '', content)  # Remove JSON with $type fields (common pattern)
	content = re.sub(r'\{"[^"]{5,}":\{[^}]{100,}\}', '', content)  # Remove nested JSON objects

	# Compress consecutive newlines (4+ newlines become max_newlines)
	content = re.sub(r'\n{4,}', '\n' * max_newlines, content)

	# Remove lines that are only whitespace
	lines = content.split('\n')
	filtered_lines = []
	for line in lines:
		stripped = line.strip()
		# Keep all non-empty lines
		if stripped:
			# Skip long lines that actually parse as JSON (SPA state blobs). A prefix
			# check alone is not enough: markdown links/images also start with '['.
			if len(stripped) > 100 and stripped[0] in '{[':
				try:
					json.loads(stripped)
					continue
				except ValueError:
					pass
			filtered_lines.append(line)

	content = '\n'.join(filtered_lines)
	content = content.strip()

	chars_filtered = original_length - len(content)
	return content, chars_filtered
