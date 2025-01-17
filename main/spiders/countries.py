import json

from scrapy import Request
from scrapy.http import HtmlResponse

from main.settings import HEADERS
from main.spiders.base import AmazonBaseSessionSpider


class AmazonCountrySessionSpider(AmazonBaseSessionSpider):
    """Amazon spider for extracting country delivery cookies."""

    name = "amazon:outside-delivery-session"

    def parse_cookies(self, response: HtmlResponse, cookies: dict[str, str]) -> Request:
        """
        Parse CSRF token from response and make request to change Amazon delivery country.
        """
        if not (delivery_country := self.kwargs.get("delivery_country")):
            raise ValueError("You must specify the outside delivery country")

        payload = {
            "locationType": "COUNTRY",
            "district": delivery_country.upper(),
            "countryCode": delivery_country.upper(),
            "deviceType": "web",
            "storeContext": "hpc",
            "pageType": "Search",
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
