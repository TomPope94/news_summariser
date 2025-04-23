import json

from core.logging import logger
from scraping.scraper import NewsScraper, NewsSource


def main():
    logger.info("Initiating BBC news scraper...")
    bbc_news = NewsScraper(NewsSource.BBCNEWS)

    logger.info("Scraping BBC news...")
    articles = bbc_news.scrape()

    with open("articles.json", "w") as f:
        json.dump([article.model_dump() for article in articles], f, indent=4, default=str)


if __name__ == "__main__":
    main()
