from bs4 import BeautifulSoup


def parse_email_html(html_content: str) -> str:
    """Parses an HTML email body and extracts the text."""
    if not html_content:
        return ""

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()

        # Get text and clean up whitespace
        text = soup.get_text(separator="\n", strip=True)
        return "\n".join(line for line in text.splitlines() if line)
    except Exception:
        # Fallback for any parsing errors
        return ""
