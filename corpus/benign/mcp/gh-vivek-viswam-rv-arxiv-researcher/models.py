from pydantic import BaseModel

class Article(BaseModel):
    article_id: str
    title: str
    authors: list[str]
    summary: str
    published: str
    pdf_url: str

class SearchResponse(BaseModel):
    results: list[Article]

class DownloadResponse(BaseModel):
    article_id: str
    title: str
    path: str
    pdf_url: str
