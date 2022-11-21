from typing import Any, Dict, Generator

from scrapy import Request, Spider
from scrapy.http import HtmlResponse

from main.settings import DEFAULT_USER_AGENT, HEADERS
from main.utils import execute_curl_command, extract_response_cookies


class AmazonLocationSessionSpider(Spider):
    """
    Amazon spider for extracting location cookies.
    """

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

    curl_command = """
        curl '{base_url}/{endpoint}' \
        -H 'anti-csrftoken-a2z: {csrf_token}' \
        -H 'user-agent: {user_agent}' \
        -H 'cookie: session-id={session_id}' \
        --data-raw 'locationType=LOCATION_INPUT&zipCode={zip_code}&storeContext=generic&
        deviceType=web&pageType=Gateway&actionSource=glow&almBrandId=undefined' \
        --compressed
    """

    def __init__(self, country: str, zip_code: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.country = country.upper()
        self.zip_code = zip_code

    def start_requests(self) -> Generator:
        """
        Make start request to main Amazon country page.
        """
        base_url = self.countries_base_urls.get(self.country)

        if not base_url:
            raise ValueError(f"Invalid country code: {self.country}")

        request = Request(
            url=self.countries_base_urls[self.country],
            headers=HEADERS,
            callback=self.parse_ajax_token,
        )
        yield request

    def parse_ajax_token(self, response: HtmlResponse) -> Request:
        """
        Parse ajax token from response.
        """
        response_cookies = extract_response_cookies(response=response)

        headers = {
            **HEADERS,
            "anti-csrftoken-a2z": self._get_ajax_token(response=response),
        }
        return response.request.replace(
            url=self.countries_base_urls[self.country] + self.csrf_token_endpoint,
            headers=headers,
            cookies=response_cookies,
            callback=self.parse_cookies,
            cb_kwargs={"cookies": response_cookies},
        )

    def parse_cookies(self, response: HtmlResponse, cookies: Dict[str, str]) -> dict:
        """
        Parse CSRF token from response and make request to change Amazon location.
        """
        curl_command = self.curl_command.format(
            base_url=self.countries_base_urls[self.country],
            endpoint=self.address_change_endpoint,
            csrf_token=self._get_csrf_token(response=response),
            user_agent=DEFAULT_USER_AGENT,
            zip_code=self.zip_code,
            session_id=cookies["session-id"],
        )
        curl_response = execute_curl_command(curl_command=curl_command).strip()

        # Check if this string exists in Amazon response.
        # If `isValidAddress` equal to 1 it means that location changed successfully.
        if '"isValidAddress":1' not in curl_response:
            return {}
        return cookies

    @staticmethod
    def _get_ajax_token(response: HtmlResponse) -> str:
        """
        Extract ajax token from response.
        """
        data = response.xpath("//input[@id='glowValidationToken']/@value").get()
        if not data:
            raise ValueError("Invalid page content")
        return data

    @staticmethod
    def _get_csrf_token(response: HtmlResponse) -> str:
        """
        Extract CSRF token from response.
        """
        csrf_token = response.css("script").re_first(r'CSRF_TOKEN : "(.+?)"')
        if not csrf_token:
            raise ValueError("CSRF token not found")
        return csrf_token
