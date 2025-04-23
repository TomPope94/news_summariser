from core.logging import logger
from scraping.models import Article

from typing import List
from datetime import datetime

from enum import Enum

import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class NewsSource(Enum):
    BBCNEWS = "BBCNews"
    BBCSPORT = "BBCSport"
    GUARDIAN = "Guardian"
    REUTERS = "Reuters"


news_rss_map = {
    NewsSource.BBCNEWS: "https://feeds.bbci.co.uk/news/rss.xml",
    NewsSource.BBCSPORT: "https://feeds.bbci.co.uk/sport/rss.xml",
    NewsSource.GUARDIAN: "https://www.theguardian.com/uk/rss",
    NewsSource.REUTERS: "https://news.google.com/rss/search?q=site%3Areuters.com&hl=en-US&gl=US&ceid=US%3Aen",  # Using Google News RSS as workaround
}


class NewsScraper():
    def __init__(self, source: NewsSource):
        self.source = source
        self.rss_feed = news_rss_map[source]

        # Set up Selenium WebDriver
        options = Options()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)

    def __del__(self):
        # Ensure driver is closed when the scraper is done
        if hasattr(self, 'driver'):
            self.driver.quit()

    def scrape(self, limit=50):
        """
        First, scrape the RSS feed to get all the articles that need to be scraped.
        Second, scrape the articles collected

        Args:
            limit: Maximum number of articles to scrape
            max_depth: Maximum link depth to follow
            url: Optional URL to start scraping from
        """
        all_articles = {}  # Dictionary to track articles by URL

        logger.debug("Getting articles from RSS feed...")
        to_scrape = self.get_articles_from_rss()

        while to_scrape and len(all_articles) < limit:
            current_article = to_scrape.pop(0)
            current_url = current_article.url

            # Skip if we've already scraped this URL
            if current_url in all_articles and all_articles[current_url].scraped:
                continue

            logger.info(f"Scraping: {current_url}")
            self.driver.get(current_url)
            time.sleep(1.5)  # Wait for the page to load

            html = self.driver.page_source
            logger.debug("Parsing HTML content...")

            article_data = self.parse_article_page(html, current_url)

            # Store or update the article
            if current_url not in all_articles:
                all_articles[current_url] = article_data
            else:
                # Update existing article with content
                all_articles[current_url].contents = article_data.contents
                all_articles[current_url].title = article_data.title
                all_articles[current_url].linked_articles = article_data.linked_articles
                all_articles[current_url].date = article_data.date

            # Mark as scraped
            all_articles[current_url].scraped = True

            # Add linked articles to the queue
            for link in article_data.linked_articles:
                full_url = f"https://www.bbc.com{link}" if not link.startswith("http") else link
                if full_url not in all_articles and len(all_articles) < limit:
                    # Create a new article placeholder
                    new_article = Article(
                        url=full_url,
                        linked_articles=[],
                        scraped=False
                    )
                    all_articles[full_url] = new_article
                    to_scrape.append(new_article)

        # After the main loop acquires n articles, need to finish scraping them
        while to_scrape and len(all_articles) >= limit:
            # Remove the last article from the list
            current_article = to_scrape.pop(0)
            current_url = current_article.url

            # Skip if we've already scraped this URL
            if current_url in all_articles and all_articles[current_url].scraped:
                continue

            logger.info(f"Scraping: {current_url}")
            self.driver.get(current_url)
            time.sleep(1.5)  # Wait for the page to load

            html = self.driver.page_source
            logger.debug("Parsing HTML content...")

            article_data = self.parse_article_page(html, current_url)

            # Store or update the article
            if current_url not in all_articles:
                all_articles[current_url] = article_data
            else:
                # Update existing article with content
                all_articles[current_url].contents = article_data.contents
                all_articles[current_url].title = article_data.title
                all_articles[current_url].linked_articles = article_data.linked_articles

                # Mark as scraped
                all_articles[current_url].scraped = True

        logger.debug(f"to_scrape: {len(to_scrape)}")
        logger.debug(f"all_articles: {len(all_articles)}")
        return list(all_articles.values())

    def get_articles_from_rss(self) -> List[Article]:
        """
        Get articles from the RSS feed.
        """
        response = requests.get(self.rss_feed)
        if response.status_code != 200:
            logger.error(f"Failed to fetch RSS feed: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'xml')
        articles = []

        for item in soup.find_all('item'):
            title = item.title.text
            link = item.link.text
            date = item.pubDate.text

            if link.startswith("https://www.bbc.com/news/articles"):
                articles.append(Article(
                    title=title,
                    url=link,
                    date=datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %Z"),
                    linked_articles=[],
                    scraped=False
                ))

        return articles

    def parse_article_page(self, html_content, url) -> Article:
        """
        Parse an article page to extract title, content, and linked articles.
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract title
        title_element = soup.find('h1')
        title = title_element.get_text().strip() if title_element else ""

        # Extract content
        content_elements = soup.select('article p, article h2')
        content = "\n".join([elem.get_text().strip() for elem in content_elements])

        # Extract date
        date_element = soup.find('time')

        date = None
        if date_element and 'datetime' in date_element.attrs:
            date = datetime.fromisoformat(date_element['datetime'])

        # Find linked articles within the article
        linked_articles = []
        for link in soup.select('a[href^="/news/articles"]'):
            href = link.get('href')
            if href and href not in linked_articles:
                linked_articles.append(href)

        return Article(
            title=title,
            contents=content,
            date=date,
            url=url,
            linked_articles=linked_articles,
            scraped=True
        )
