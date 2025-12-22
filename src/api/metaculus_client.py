"""
Metaculus API Client

Handles all interactions with the Metaculus API.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from ..config import api_config, metaculus_config, QuestionType

logger = logging.getLogger(__name__)


class MetaculusClient:
    """Client for interacting with the Metaculus API."""

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the Metaculus client.

        Args:
            api_token: Metaculus API token. If not provided, uses environment variable.
        """
        self.api_token = api_token or api_config.metaculus_token
        self.base_url = metaculus_config.api_base_url
        self.auth_headers = {"headers": {"Authorization": f"Token {self.api_token}"}}

    def post_comment(self, post_id: int, comment_text: str) -> None:
        """
        Post a comment on a question page.

        Args:
            post_id: The post ID to comment on
            comment_text: The comment text

        Raises:
            RuntimeError: If the API request fails
        """
        url = f"{self.base_url}/comments/create/"
        payload = {
            "text": comment_text,
            "parent": None,
            "included_forecast": True,
            "is_private": True,
            "on_post": post_id,
        }

        logger.info(f"Posting comment to post {post_id}")
        response = requests.post(url, json=payload, **self.auth_headers)

        if not response.ok:
            logger.error(f"Failed to post comment: {response.text}")
            raise RuntimeError(f"Failed to post comment: {response.text}")

        logger.info(f"Successfully posted comment to post {post_id}")

    def post_prediction(
        self, question_id: int, forecast_payload: Dict[str, Any]
    ) -> None:
        """
        Post a forecast on a question.

        Args:
            question_id: The question ID to forecast on
            forecast_payload: The forecast payload

        Raises:
            RuntimeError: If the API request fails
        """
        url = f"{self.base_url}/questions/forecast/"
        payload = [
            {
                "question": question_id,
                **forecast_payload,
            }
        ]

        logger.info(f"Posting prediction to question {question_id}")
        response = requests.post(url, json=payload, **self.auth_headers)

        logger.info(f"Prediction post status code: {response.status_code}")

        if not response.ok:
            logger.error(f"Failed to post prediction: {response.text}")
            raise RuntimeError(f"Failed to post prediction: {response.text}")

        logger.info(f"Successfully posted prediction to question {question_id}")

    def create_forecast_payload(
        self,
        forecast: Union[float, Dict[str, float], List[float]],
        question_type: str,
    ) -> Dict[str, Any]:
        """
        Create a forecast payload in the correct format for the API.

        Args:
            forecast: The forecast value(s)
            question_type: Type of question (binary, multiple_choice, numeric, discrete)

        Returns:
            Dictionary containing the formatted forecast payload
        """
        if question_type == QuestionType.BINARY:
            return {
                "probability_yes": forecast,
                "probability_yes_per_category": None,
                "continuous_cdf": None,
            }

        if question_type == QuestionType.MULTIPLE_CHOICE:
            return {
                "probability_yes": None,
                "probability_yes_per_category": forecast,
                "continuous_cdf": None,
            }

        # numeric or discrete
        return {
            "probability_yes": None,
            "probability_yes_per_category": None,
            "continuous_cdf": forecast,
        }

    def list_posts_from_tournament(
        self,
        tournament_id: Union[int, str] = None,
        offset: int = 0,
        count: int = 50,
    ) -> Dict[str, Any]:
        """
        List posts from a tournament.

        Args:
            tournament_id: Tournament ID. If None, uses default from config.
            offset: Pagination offset
            count: Number of posts to retrieve

        Returns:
            Dictionary containing tournament posts data

        Raises:
            RuntimeError: If the API request fails
        """
        if tournament_id is None:
            tournament_id = metaculus_config.default_tournament_id

        url_params = {
            "limit": count,
            "offset": offset,
            "order_by": "-hotness",
            "forecast_type": ",".join(
                [
                    QuestionType.BINARY,
                    QuestionType.MULTIPLE_CHOICE,
                    QuestionType.NUMERIC,
                    QuestionType.DISCRETE,
                ]
            ),
            "tournaments": [tournament_id],
            "statuses": "open",
            "include_description": "true",
        }

        url = f"{self.base_url}/posts/"
        logger.info(f"Fetching posts from tournament {tournament_id}")
        response = requests.get(url, **self.auth_headers, params=url_params)

        if not response.ok:
            logger.error(f"Failed to fetch posts: {response.text}")
            raise RuntimeError(f"Failed to fetch posts: {response.text}")

        data = json.loads(response.content)
        logger.info(f"Successfully fetched {len(data.get('results', []))} posts")
        return data

    def get_open_question_ids_from_tournament(
        self, tournament_id: Union[int, str] = None
    ) -> List[Tuple[int, int]]:
        """
        Get open question IDs from a tournament.

        Args:
            tournament_id: Tournament ID. If None, uses default from config.

        Returns:
            List of tuples (question_id, post_id) for open questions
        """
        posts = self.list_posts_from_tournament(tournament_id)

        post_dict = {}
        for post in posts["results"]:
            if question := post.get("question"):
                post_dict[post["id"]] = [question]

        open_question_id_post_id = []
        for post_id, questions in post_dict.items():
            for question in questions:
                if question.get("status") == "open":
                    logger.info(
                        f"Found open question: ID={question['id']}, "
                        f"Title={question['title']}, "
                        f"Closes={question['scheduled_close_time']}"
                    )
                    open_question_id_post_id.append((question["id"], post_id))

        logger.info(f"Found {len(open_question_id_post_id)} open questions")
        return open_question_id_post_id

    def get_post_details(self, post_id: int) -> Dict[str, Any]:
        """
        Get all details about a post.

        Args:
            post_id: The post ID

        Returns:
            Dictionary containing post details

        Raises:
            RuntimeError: If the API request fails
        """
        url = f"{self.base_url}/posts/{post_id}/"
        logger.info(f"Getting details for post {post_id}")

        response = requests.get(url, **self.auth_headers)

        if not response.ok:
            logger.error(f"Failed to get post details: {response.text}")
            raise RuntimeError(f"Failed to get post details: {response.text}")

        details = json.loads(response.content)
        logger.debug(f"Successfully fetched details for post {post_id}")
        return details

    @staticmethod
    def has_existing_forecast(post_details: Dict[str, Any]) -> bool:
        """
        Check if a forecast has already been made for this question.

        Args:
            post_details: The post details dictionary

        Returns:
            True if a forecast exists, False otherwise
        """
        try:
            forecast_values = post_details["question"]["my_forecasts"]["latest"][
                "forecast_values"
            ]
            return forecast_values is not None
        except (KeyError, TypeError):
            return False
