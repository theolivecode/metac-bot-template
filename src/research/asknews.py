"""
AskNews Research Provider

Uses AskNews SDK for news-based research.
"""
import logging
from typing import Any, Dict, Optional

from asknews_sdk import AskNewsSDK

from .base import ResearchProvider
from ..config import api_config

logger = logging.getLogger(__name__)


class AskNewsResearchProvider(ResearchProvider):
    """Research provider using AskNews SDK."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        hot_articles_count: int = 6,
        historical_articles_count: int = 10,
    ):
        """
        Initialize the AskNews research provider.

        Args:
            client_id: AskNews client ID. If None, uses config.
            client_secret: AskNews client secret. If None, uses config.
            hot_articles_count: Number of latest articles to fetch.
            historical_articles_count: Number of historical articles to fetch.
        """
        self.client_id = client_id or api_config.asknews_client_id
        self.client_secret = client_secret or api_config.asknews_secret
        self.hot_articles_count = hot_articles_count
        self.historical_articles_count = historical_articles_count

        self.client = AskNewsSDK(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=set(["news"]),
        )

    async def conduct_research(
        self, question: str, question_details: Dict[str, Any] = None
    ) -> str:
        """
        Conduct research using AskNews SDK.

        Args:
            question: The question to research
            question_details: Optional additional details

        Returns:
            Formatted research findings from news articles
        """
        logger.info(f"Using AskNews for research question: {question}")
        logger.info("Running research...")

        try:
            # Get latest news (past 48 hours)
            hot_response = self.client.news.search_news(
                query=question,
                n_articles=self.hot_articles_count,
                return_type="both",
                strategy="latest news",
            )

            # Get historical news (past 60 days)
            historical_response = self.client.news.search_news(
                query=question,
                n_articles=self.historical_articles_count,
                return_type="both",
                strategy="news knowledge",
            )

            formatted_articles = self._format_articles(
                hot_response.as_dicts,
                historical_response.as_dicts,
            )

            logger.info("\n======Research Start======")
            logger.info(formatted_articles)
            logger.info("\n======Research End========")

            return formatted_articles

        except Exception as e:
            logger.error(f"AskNews research failed: {e}")
            return f"Research could not be completed: {str(e)}"

    def _format_articles(self, hot_articles, historical_articles) -> str:
        """
        Format articles into a readable string.

        Args:
            hot_articles: List of recent articles
            historical_articles: List of historical articles

        Returns:
            Formatted string of articles
        """
        formatted = "Here are the relevant news articles:\n\n"

        if hot_articles:
            hot_articles = [article.__dict__ for article in hot_articles]
            hot_articles = sorted(hot_articles, key=lambda x: x["pub_date"], reverse=True)

            for article in hot_articles:
                pub_date = article["pub_date"].strftime("%B %d, %Y %I:%M %p")
                formatted += (
                    f"**{article['eng_title']}**\n"
                    f"{article['summary']}\n"
                    f"Original language: {article['language']}\n"
                    f"Publish date: {pub_date}\n"
                    f"Source:[{article['source_id']}]({article['article_url']})\n\n"
                )

        if historical_articles:
            historical_articles = [article.__dict__ for article in historical_articles]
            historical_articles = sorted(
                historical_articles, key=lambda x: x["pub_date"], reverse=True
            )

            for article in historical_articles:
                pub_date = article["pub_date"].strftime("%B %d, %Y %I:%M %p")
                formatted += (
                    f"**{article['eng_title']}**\n"
                    f"{article['summary']}\n"
                    f"Original language: {article['language']}\n"
                    f"Publish date: {pub_date}\n"
                    f"Source:[{article['source_id']}]({article['article_url']})\n\n"
                )

        if not hot_articles and not historical_articles:
            formatted += "No articles were found.\n\n"

        return formatted
