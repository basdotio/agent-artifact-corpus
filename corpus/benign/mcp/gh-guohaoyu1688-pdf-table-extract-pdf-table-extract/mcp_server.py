"""Official FastMCP stdio tools sharing the extraction API."""

from mcp.server.fastmcp import FastMCP

from .core.errors import PDFError, failure, success
from .core.extract import extract_tables as extract
from .core.extract import inspect_pdf as inspect


def build_server() -> FastMCP:
    mcp = FastMCP("pdf-table-extract")

    @mcp.tool()
    def inspect_pdf(path: str) -> dict:
        """Read local PDF page dimensions, text-layer presence and detected table counts."""
        try:
            return success(inspect(path))
        except PDFError as exc:
            return failure(exc)

    @mcp.tool()
    def extract_tables(
        path: str,
        pages: str | None = None,
        format: str = "json",
        merge_pages: bool = False,
        out: str | None = None,
        engine: str = "auto",
        ocr: bool = False,
        header_rows: int = 1,
        fill_merged: str = "none",
        area: list[float] | None = None,
        columns: list[float] | None = None,
    ) -> dict:
        """Extract local tables. Side effect: if out is given, writes/replaces exports there.

        pages uses 1-3,7 syntax. Area uses PDF points with top-left origin.
        OCR is optional and local; no network downloads are initiated.
        """
        try:
            return success(
                extract(
                    path,
                    pages=pages,
                    format=format,
                    merge_pages=merge_pages,
                    out=out,
                    engine=engine,
                    ocr=ocr,
                    header_rows=header_rows,
                    fill_merged=fill_merged,
                    area=area,
                    columns=columns,
                )
            )
        except PDFError as exc:
            return failure(exc)

    return mcp


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
