import json

from scrapy import Request
from scrapy.http import HtmlResponse

from main.settings import HEADERS
from main.spiders.base import AmazonBaseSessionSpider


class AmazonLocationSessionSpider(AmazonBaseSessionSpider):
    """Amazon spider for extracting location cookies."""

    name = "amazon:location-delivery-session"

    def parse_cookies(self, response: HtmlResponse, cookies: dict[str, str]) -> Request:
        """
        Parse CSRF token from response and make request to change Amazon location.
        """
        if not (zip_code := self.kwargs.get("zip_code")):
            raise ValueError("You must specify a zip code")

        payload = {
            "locationType": "LOCATION_INPUT",
            "zipCode": zip_code.replace("+", " "),
            "storeContext": "generic",
            "deviceType": "web",
            "pageType": "Gateway",
            "actionSource": "glow",
        }
        headers = {
            **HEADERS,
            "content-type": "application/json",
            "anti-csrftoken-a2z": self._get_csrf_token(response=response),
        }
        return Request(
            url=self.countries_base_urls[self.country] + self.address_change_endpoint,
            method="POST",
            body=json.dumps(payload),
            headers=headers,
            cookies=cookies,
            callback=self.parse_result,
            cb_kwargs={"cookies": cookies},
        )
