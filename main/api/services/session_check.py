"""
Replay a caller's cookies against Amazon and report what location they produce.

Unlike the extraction endpoints, this talks to Amazon directly rather than going
through ScrapyRT: the check is a single GET, and the storefront's own "Deliver
to" widget is the answer.
"""

import re
from urllib.parse import urljoin

import requests

from main.api.exceptions import AmazonUnreachableException, SessionCheckFailedException
from main.api.schemas.common import Response, SessionCheckRequest
from main.settings import COUNTRY_BASE_URLS, HEADERS
from main.waf import get_waf_session

REQUEST_TIMEOUT_SECONDS = 30

LOCATION_REGEX = r'(?s)glow-ingress-line2">(.+?)<'

# Akamai answers with a small interstitial that meta-refreshes to a bm-verify
# URL; following it lands on the real storefront. Scrapy gets this for free from
# its MetaRefreshMiddleware, a plain HTTP client has to do it by hand.
META_REFRESH_REGEX = (
    r"""<meta\s+http-equiv=["']?refresh["']?[^>]*content=["'][^"']*URL=['"]?([^'"]+)"""
)

# Amazon pads the rendered location with a zero-width non-joiner, which arrives
# either as the character itself or as the HTML entity.
_PADDING = ("‌", "&zwnj;")


def build_session() -> requests.Session:
    """
    Build the HTTP session used to talk to Amazon.
    """
    return requests.Session()


class AmazonSessionCheckService:
    """Service to tell whether a set of cookies still pins a location."""

    def check_session(self, data: SessionCheckRequest) -> Response:
        """
        Fetch the storefront with `data.cookies` and read the location back.
        """
        base_url = COUNTRY_BASE_URLS[data.country_code]
        response = self._fetch_storefront(base_url=base_url, cookies=data.cookies)

        location = extract_location(html=response.text)
        if location is None:
            # Our own request was turned away, which says nothing about the
            # caller's session -- reporting it as expired would be a lie.
            raise SessionCheckFailedException(
                message=(
                    f"A bot check answered instead of {base_url}, "
                    f"so the session could not be checked"
                ),
                status_code=409,
            )

        valid = matches_expected(location=location, expected=data.expected)
        return Response(
            data={
                "country_code": data.country_code,
                "location": location,
                "valid": valid,
            },
            message="Session is alive" if valid is not False else "Session is stale",
        )

    @staticmethod
    def _fetch_storefront(base_url: str, cookies: dict) -> requests.Response:
        """
        Request the storefront, carrying a WAF token so our own check is not the
        thing that gets challenged, and stepping through Akamai's interstitial
        when one answers instead.
        """
        waf_cookies, user_agent = get_waf_session(base_url=base_url)
        headers = {**HEADERS, "user-agent": user_agent}
        # The caller's cookies are the thing under test and must ride along on
        # every hop: without them Amazon falls back to the location it infers
        # from our IP, which would read as "the session is stale".
        jar = {**cookies, **waf_cookies}
        session = build_session()

        def fetch(url: str) -> requests.Response:
            return session.get(
                url=url, cookies=jar, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
            )

        try:
            response = fetch(base_url)
            if extract_location(html=response.text) is not None:
                return response

            if not (target := find_meta_refresh(html=response.text)):
                return response

            response = fetch(urljoin(base_url, target))
            if extract_location(html=response.text) is not None:
                return response

            # Clearing the interstitial leaves an `ak_bmsc` cookie on the
            # session, and asking again with it usually lands on the storefront.
            return fetch(base_url)
        except requests.RequestException as error:
            raise AmazonUnreachableException(
                message=f"Could not reach {base_url}: {error}", status_code=502
            ) from error


def extract_location(html: str) -> str | None:
    """
    Pull the delivery location out of the storefront's glow widget.

    Returns `None` when the widget is absent, which means this was not a
    storefront: a WAF challenge, an Akamai interstitial or a block page.
    """
    if not (match := re.search(LOCATION_REGEX, html)):
        return None

    location = match.group(1)
    for padding in _PADDING:
        location = location.replace(padding, "")
    return location.strip()


def find_meta_refresh(html: str) -> str | None:
    """
    Return the URL an interstitial wants the browser to go to next, if any.
    """
    match = re.search(META_REFRESH_REGEX, html, re.IGNORECASE)
    return match.group(1) if match else None


def matches_expected(location: str, expected: str | None) -> bool | None:
    """
    Compare the location Amazon shows against what the caller expected.

    Returns `None` when the caller expected nothing, to keep "no opinion"
    distinct from "does not match".
    """
    if expected is None:
        return None
    return expected.strip().casefold() in location.casefold()
