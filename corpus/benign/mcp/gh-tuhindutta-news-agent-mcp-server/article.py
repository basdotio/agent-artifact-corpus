from typing import Optional
from pydantic import BaseModel


class Article(BaseModel):
    article_id: Optional[str] = None
    link: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    creator: Optional[list[str]] = None
    country: Optional[list[str]] = None
    category: Optional[list[str]] = None
    pubDate: Optional[str] = None
    image_url: Optional[str] = None
    source_url: Optional[str] = None