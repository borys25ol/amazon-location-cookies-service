import json

import requests

from main.api.config import get_app_settings
from main.api.exceptions import CookiesNotFoundException
from main.api.schemas.common import Response, ScrapingRequest
from main.utils import add_query_params

settings = get_app_settings()


class AmazonLocationService:
    """
    Service to extract data from ScrapyRT service.
    """

    @staticmethod
    def get_cookies(data: ScrapingRequest) -> Response:
        """
        Get amazon cookies.
        """
        query_params = {
            "start_requests": "1",
            "spider_name": "amazon:location-session",
            "crawl_args": json.dumps(
                {"zip_code": data.zip_code, "country": data.country_code.lower()}
            ),
        }
        url = add_query_params(url=settings.scrapyrt_url, params=query_params)

        json_data = requests.get(url=url).json()

        if not json_data["items"][0]:
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
                "cookies": json_data["items"][0],
            },
            message=f"Cookies for zip code: `{data.zip_code}` extracted successfully",
        )
