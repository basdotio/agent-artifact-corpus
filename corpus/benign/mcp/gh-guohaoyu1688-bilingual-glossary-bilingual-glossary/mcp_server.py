"""Official MCP stdio adapter; every tool is read-only."""

from mcp.server.fastmcp import FastMCP

from .cli import ok
from .core.checker import Checker
from .core.store import Glossary, GlossError


def create_server(glossary: Glossary) -> FastMCP:
    server = FastMCP("Bilingual Glossary")
    checker = Checker(glossary)

    def invoke(function, *args):
        try:
            return ok(function(*args))
        except GlossError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": str(exc)}}

    @server.tool()
    def lookup_term(query: str, lang: str | None = None) -> dict:
        """Read fuzzy Chinese, English, abbreviation or pinyin-initial matches."""
        return invoke(glossary.search, query, None, lang)

    @server.tool()
    def check_text(text: str, lang: str | None = None, domain: str | None = None) -> dict:
        """Read terminology issues using approved terms; no files are changed."""
        return invoke(checker.check_text, text, lang, domain)

    @server.tool()
    def check_pair(
        source: str, target: str, source_lang: str = "zh", target_lang: str = "en"
    ) -> dict:
        """Check prescribed canonical translations in one aligned pair."""
        return invoke(checker.check_pair, source, target, source_lang, target_lang)

    @server.tool()
    def glossary_for_text(text: str, domain: str | None = None) -> dict:
        """Return only approved terms found in supplied text and an English instruction fragment."""
        return invoke(checker.prompt, text, domain)

    return server
