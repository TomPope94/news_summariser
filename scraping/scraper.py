from core.logging import logger
from scraping.models import Article

from typing import List
from datetime import datetime

from enum import Enum

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class NewsSource(Enum):
    BBC = "BBC"


news_url_map = {
    NewsSource.BBC: "https://www.bbc.com/news"
}


class NewsScraper():
    def __init__(self, source: NewsSource):
        self.source = source
        self.homepage = news_url_map[source]

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
        Start scraping from the initial URL and follow links up to max_depth.

        Args:
            limit: Maximum number of articles to scrape
            max_depth: Maximum link depth to follow
            url: Optional URL to start scraping from
        """
        all_articles = {}  # Dictionary to track articles by URL
        to_scrape = [self.homepage]  # URLs to scrape

        while to_scrape and len(all_articles) < limit:
            current_url = to_scrape.pop(0)

            # Skip if we've already scraped this URL
            if current_url in all_articles and all_articles[current_url].scraped:
                continue

            logger.info(f"Scraping: {current_url}")
            self.driver.get(current_url)

            html = self.driver.page_source
            logger.debug("Parsing HTML content...")

            # If it's the main page, get linked articles
            if current_url == self.homepage:
                logger.debug("Homepage detected, parsing main page...")
                linked_articles = self.parse_main_page(html)

                for article in linked_articles:
                    full_url = f"https://www.bbc.com{article.url}" if not article.url.startswith("http") else article.url
                    if full_url not in all_articles:
                        all_articles[full_url] = article
                        to_scrape.append(full_url)
            else:
                # It's an article page
                logger.debug("Article page detected, parsing article...")
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
                        all_articles[full_url] = Article(
                            url=full_url,
                            linked_articles=[],
                            scraped=False
                        )
                        to_scrape.append(full_url)

        # After the main loop acquires n articles, need to finish scraping them
        while to_scrape and len(all_articles) >= limit:
            # Remove the last article from the list
            current_url = to_scrape.pop(0)
            # Skip if we've already scraped this URL
            if current_url in all_articles and all_articles[current_url].scraped:
                continue

            logger.info(f"Scraping: {current_url}")
            self.driver.get(current_url)

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

    def parse_main_page(self, html_content) -> List[Article]:
        """
        Parse the main page HTML content and extract article links.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        articles = []

        for item in soup.find_all('a'):
            if item.get('href') is None:
                continue

            link = item['href']

            # Only want links to /news/articles
            if not link.startswith("/news/articles"):
                continue

            title = item.get_text().strip()
            if not title:  # Skip empty titles
                continue

            class_names = item.get('class', [])

            # Only want classes that include PromoLink
            if not any("PromoLink" in c for c in class_names):
                continue

            parsed_article = Article(
                title=title,
                url=link,
                linked_articles=[],
                scraped=False
            )

            articles.append(parsed_article)

        logger.debug(f"Found {len(articles)} articles on the main page.")
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
