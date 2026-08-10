import json
from collections.abc import AsyncIterator

from scrapy import Request, Spider
from scrapy.http import HtmlResponse

from main.settings import HEADERS
from main.utils import extract_response_cookies
from main.waf import get_waf_session, invalidate_waf_session

# A cached WAF token can stop being accepted at any time, and Amazon also swaps
# in an Akamai Bot Manager interstitial for some sessions. Both are recoverable:
# drop the token, harvest a new one, ask again. Each retry runs a browser, so the
# budget is kept small enough that a crawl stays inside the API's timeout.
MAX_CHALLENGE_RETRIES = 2


class AmazonBaseSessionSpider(Spider):
    """Base Amazon spider for extracting delivery cookies."""

    name = ""

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
        "FR": "https://www.amazon.fr",
    }

    def __init__(self, country: str, *args: tuple, **kwargs: str) -> None:
        super().__init__(*args, **kwargs)
        self.country = country.upper()
        self.args = args
        self.kwargs = kwargs
        # Replaced in `start` by the user agent the WAF token belongs to.
        self.waf_user_agent = HEADERS["user-agent"]

    def build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """
        Build request headers pinned to the user agent the WAF token was issued to.

        Every request in the flow must reuse it: replaying `aws-waf-token` under a
        different user agent gets challenged again.
        """
        return {**HEADERS, "user-agent": self.waf_user_agent, **(extra or {})}

    async def start(self) -> AsyncIterator[Request]:
        """
        Make start request to main Amazon country page.

        The storefront sits behind an AWS WAF challenge, so the request carries a
        browser-issued `aws-waf-token` and the user agent it was issued to.

        Scrapy 2.13 replaced `start_requests` with this method and 2.17 dropped
        the old name entirely -- a spider still defining it is simply never asked
        for any requests, and the crawl finishes with no items and no error.
        """
        base_url = self.countries_base_urls.get(self.country)
        if not base_url:
            raise ValueError(f"Invalid country code: {self.country}")

        waf_cookies, self.waf_user_agent = get_waf_session(base_url=base_url)
        yield Request(
            url=base_url,
            headers=self.build_headers(),
            cookies=waf_cookies,
            callback=self.parse_ajax_token,
        )

    def parse_ajax_token(self, response: HtmlResponse) -> Request:
        """
        Parse ajax token from response, retrying if the storefront never arrived.
        """
        ajax_token = self._get_ajax_token(response=response)
        if ajax_token is None:
            return self._retry_start(response=response)

        headers = self.build_headers({"anti-csrftoken-a2z": ajax_token})
        response_cookies = extract_response_cookies(response=response)
        return response.request.replace(
            url=self.countries_base_urls[self.country] + self.csrf_token_endpoint,
            headers=headers,
            cookies=response_cookies,
            callback=self.parse_cookies,
            cb_kwargs={"cookies": response_cookies},
        )

    def build_payload(self) -> dict:
        """
        Build the address-change payload (implemented by child classes).
        """
        raise NotImplementedError

    def parse_cookies(self, response: HtmlResponse, cookies: dict[str, str]) -> Request:
        """
        Read the CSRF token and post the location change.

        This step gets bot-checked just like the first one, so a response without
        a CSRF token restarts the flow instead of failing the crawl.
        """
        csrf_token = self._get_csrf_token(response=response)
        if csrf_token is None:
            return self._retry_start(response=response)

        headers = self.build_headers(
            {"content-type": "application/json", "anti-csrftoken-a2z": csrf_token}
        )
        return Request(
            url=self.countries_base_urls[self.country] + self.address_change_endpoint,
            method="POST",
            body=json.dumps(self.build_payload()),
            headers=headers,
            cookies=cookies,
            callback=self.parse_result,
            cb_kwargs={"cookies": cookies},
        )

    @staticmethod
    def _token_was_rejected(response: HtmlResponse) -> bool:
        """
        Say whether the WAF turned the request away, as opposed to some other
        bot check. AWS WAF answers `202` and sets `x-amzn-waf-action`; only that
        means the cached token itself is worthless and has to be replaced.
        """
        return bool(response.status == 202 or response.headers.get("x-amzn-waf-action"))

    def _retry_start(self, response: HtmlResponse) -> Request:
        """
        Start the whole flow over after a bot check answered in place of a page.

        Amazon serves those in several shapes -- a WAF challenge, an Akamai
        interstitial, occasionally a plain page missing the token being read --
        and they come and go, so any unusable response is retried rather than
        picked apart. Both steps of the flow can be hit, and either way the
        session is suspect, so the retry restarts from the storefront. Only a WAF
        rejection costs a new token; the rest reuse the cached one.
        """
        attempt = response.meta.get("challenge_retry", 0) + 1
        base_url = self.countries_base_urls[self.country]

        if attempt > MAX_CHALLENGE_RETRIES:
            raise ValueError(
                f"No usable page from {base_url} after {MAX_CHALLENGE_RETRIES} "
                f"retries (last: {response.url}, HTTP {response.status}, "
                f"{len(response.body)} bytes)"
            )

        if self._token_was_rejected(response=response):
            self.logger.info(f"WAF rejected the token for {base_url}, harvesting anew")
            invalidate_waf_session(base_url=base_url)

        self.logger.info(
            f"Bot check instead of {response.url} (HTTP {response.status}, "
            f"{len(response.body)} bytes), retry {attempt}/{MAX_CHALLENGE_RETRIES}"
        )
        waf_cookies, self.waf_user_agent = get_waf_session(base_url=base_url)
        return Request(
            url=base_url,
            headers=self.build_headers(),
            cookies=waf_cookies,
            callback=self.parse_ajax_token,
            dont_filter=True,
            meta={"challenge_retry": attempt},
        )

    @staticmethod
    def parse_result(response: HtmlResponse, cookies: dict[str, str]) -> dict:
        """
        Check if confirmation string exists in Amazon response.
        If `isValidAddress` equal to 1 it means that location changed successfully.
        """
        return {} if '"isValidAddress":1' not in response.text else cookies

    @staticmethod
    def _get_ajax_token(response: HtmlResponse) -> str | None:
        """
        Extract ajax token from response, or `None` if this is not a storefront.
        """
        selector = "//input[@id='glowValidationToken']/@value"
        return response.xpath(selector).get()

    @staticmethod
    def _get_csrf_token(response: HtmlResponse) -> str | None:
        """
        Extract CSRF token from response, or `None` if the page does not carry one.
        """
        selector, regex = "script", r'CSRF_TOKEN : "(.+?)"'
        return response.css(selector).re_first(regex)
