from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class Article(BaseModel):
    title: Optional[str] = None
    contents: Optional[str] = None
    date: Optional[datetime] = None
    url: str
    linked_articles: list[str]
    scraped: bool = False
