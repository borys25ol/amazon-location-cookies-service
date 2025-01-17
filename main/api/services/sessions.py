import json

import requests

from main.api.config import get_app_settings
from main.api.exceptions import CookiesNotFoundException
from main.api.schemas.common import (
    Response,
    ScrapingCountryRequest,
    ScrapingLocationRequest,
)
from main.utils import add_query_params

settings = get_app_settings()


class AmazonSessionService:
    """Service to extract Amazon cookies data from ScrapyRT service."""

    def get_location_cookies(self, data: ScrapingLocationRequest) -> Response:
        """
        Get amazon cookies from ScrapyRT service.
        """
        query_params = {
            "start_requests": "1",
            "spider_name": "amazon:location-delivery-session",
            "crawl_args": json.dumps(
                {"zip_code": data.zip_code, "country": data.country_code.lower()}
            ),
        }
        cookies = self._make_api_request(params=query_params)

        if not cookies:
            raise CookiesNotFoundException(
                message=(
                    f"Cookies for zip code: `{data.zip_code}` "
                    f"and region: `{data.country_code}` not found"
                ),
                status_code=404,
            )

        return Response(
            data={
                "zip_code": data.zip_code,
                "country_code": data.country_code,
                "cookies": cookies,
            },
            message=f"Cookies for zip code: `{data.zip_code}` extracted successfully",
        )

    def get_country_cookies(self, data: ScrapingCountryRequest) -> Response:
        """
        Get amazon cookies from ScrapyRT service.
        """
        query_params = {
            "start_requests": "1",
            "spider_name": "amazon:outside-delivery-session",
            "crawl_args": json.dumps(
                {
                    "delivery_country": data.delivery_country_code.upper(),
                    "country": data.country_code.lower(),
                }
            ),
        }
        cookies = self._make_api_request(params=query_params)

        if not cookies:
            raise CookiesNotFoundException(
                message=(
                    f"Cookies for delivery country: `{data.delivery_country_code}` "
                    f"and region: `{data.country_code}` not found"
                ),
                status_code=404,
            )

        return Response(
            data={
                "delivery_country_code": data.delivery_country_code,
                "country_code": data.country_code,
                "cookies": cookies,
            },
            message=f"Cookies for delivery country: `{data.delivery_country_code}` extracted successfully",
        )

    @staticmethod
    def _make_api_request(params: dict) -> dict | None:
        """
        Make a GET request to ScrapyRT service.
        """
        url = add_query_params(url=settings.scrapyrt_url, params=params)
        json_data = requests.get(url=url, timeout=30).json()
        items = json_data["items"]
        return items[0] if items else None
