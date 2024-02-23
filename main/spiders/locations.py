import json
from collections.abc import Iterator

from scrapy import Request, Spider
from scrapy.http import HtmlResponse

from main.settings import HEADERS
from main.utils import extract_response_cookies


class AmazonLocationSessionSpider(Spider):
    """Amazon spider for extracting location cookies."""

    name = "amazon:location-session"

    address_change_endpoint = (
        "/portal-migration/hz/glow/address-change?actionSource=glow"
    )
    csrf_token_endpoint = (
        "/portal-migration/hz/glow/get-rendered-address-selections?deviceType=desktop"
        "&pageType=Search&storeContext=NoStoreName&actionSource=desktop-modal"
    )
    countries_base_urls = {
        "US": "https://www.amazon.com",
        "GB": "https://www.amazon.co.uk",
        "UK": "https://www.amazon.co.uk",
        "DE": "https://www.amazon.de",
        "ES": "https://www.amazon.es",
        "IT": "https://www.amazon.it",
    }

    def __init__(
        self, country: str, zip_code: str, *args: tuple, **kwargs: dict
    ) -> None:
        super().__init__(*args, **kwargs)
        self.country = country.upper()
        self.zip_code = zip_code

    def start_requests(self) -> Iterator[Request]:
        """
        Make start request to main Amazon country page.
        """
        if self.countries_base_urls.get(self.country):
            yield Request(
                url=self.countries_base_urls[self.country],
                headers=HEADERS,
                callback=self.parse_ajax_token,
            )
        else:
            raise ValueError(f"Invalid country code: {self.country}")

    def parse_ajax_token(self, response: HtmlResponse) -> Request:
        """
        Parse ajax token from response.
        """
        headers = {
            **HEADERS,
            "anti-csrftoken-a2z": self._get_ajax_token(response=response),
        }
        response_cookies = extract_response_cookies(response=response)
        return response.request.replace(
            url=self.countries_base_urls[self.country] + self.csrf_token_endpoint,
            headers=headers,
            cookies=response_cookies,
            callback=self.parse_cookies,
            cb_kwargs={"cookies": response_cookies},
        )

    def parse_cookies(self, response: HtmlResponse, cookies: dict[str, str]) -> Request:
        """
        Parse CSRF token from response and make request to change Amazon location.
        """
        payload = {
            "locationType": "LOCATION_INPUT",
            "zipCode": self.zip_code.replace("+", " "),
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

    @staticmethod
    def parse_result(response: HtmlResponse, cookies: dict[str, str]) -> dict:
        """
        Check if confirmation string exists in Amazon response.
        If `isValidAddress` equal to 1 it means that location changed successfully.
        """
        return {} if '"isValidAddress":1' not in response.text else cookies

    @staticmethod
    def _get_ajax_token(response: HtmlResponse) -> str:
        """
        Extract ajax token from response.
        """
        selector = "//input[@id='glowValidationToken']/@value"
        if data := response.xpath(selector).get():
            return data
        raise ValueError("Invalid page content")

    @staticmethod
    def _get_csrf_token(response: HtmlResponse) -> str:
        """
        Extract CSRF token from response.
        """
        selector, regex = "script", r'CSRF_TOKEN : "(.+?)"'
        if csrf_token := response.css(selector).re_first(regex):
            return csrf_token
        raise ValueError("CSRF token not found")
