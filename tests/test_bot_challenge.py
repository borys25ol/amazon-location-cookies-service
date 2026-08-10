"""Tests for recovering from Amazon's bot checks.

These cover the paths that are hard to trigger on demand against the live site:
whether a challenged response is recognised, and whether the spider answers it by
harvesting a new WAF token instead of failing the crawl.
"""

import pytest
from scrapy import Request
from scrapy.http import HtmlResponse

from main.spiders import base
from main.spiders.base import MAX_CHALLENGE_RETRIES
from main.spiders.locations import AmazonLocationSessionSpider

BASE_URL = "https://www.amazon.com"

STOREFRONT_BODY = b'<html><input id="glowValidationToken" value="token"/></html>'
AKAMAI_BODY = (
    b'<html><head><meta http-equiv="refresh" '
    b"content=\"5; URL='/?bm-verify=AAQAAAAN'\" /></head></html>"
)
WAF_BODY = b'<html><script>window.gokuProps = {"key":"..."}</script></html>'


@pytest.fixture
def spider():
    # A concrete subclass, since the base spider deliberately has no name.
    return AmazonLocationSessionSpider(country="us", zip_code="30322")


@pytest.fixture
def fresh_token(monkeypatch):
    """Stub the browser harvest and record which hosts were invalidated."""
    invalidated = []
    monkeypatch.setattr(
        base, "invalidate_waf_session", lambda base_url: invalidated.append(base_url)
    )
    monkeypatch.setattr(
        base,
        "get_waf_session",
        lambda base_url: ({"aws-waf-token": "fresh"}, "Mozilla/5.0 (harvested)"),
    )
    return invalidated


def make_response(body: bytes, status: int = 200, headers=None, retries: int = 0):
    request = Request(url=BASE_URL, meta={"challenge_retry": retries})
    return HtmlResponse(
        url=BASE_URL, status=status, body=body, headers=headers or {}, request=request
    )


class TestTokenWasRejected:
    def test_waf_status_means_the_token_is_dead(self, spider):
        assert spider._token_was_rejected(response=make_response(WAF_BODY, status=202))

    def test_waf_header_means_the_token_is_dead(self, spider):
        response = make_response(WAF_BODY, headers={"x-amzn-waf-action": "challenge"})
        assert spider._token_was_rejected(response=response)

    def test_akamai_interstitial_does_not_blame_the_token(self, spider):
        assert not spider._token_was_rejected(response=make_response(AKAMAI_BODY))


class TestRetryStart:
    @pytest.mark.parametrize(
        ("body", "status"),
        [
            (WAF_BODY, 202),
            (AKAMAI_BODY, 200),
            # An unrecognised page with no glow widget must be retried too.
            (b"<html><body>nothing useful here</body></html>", 200),
        ],
    )
    def test_anything_but_a_storefront_is_retried(
        self, spider, fresh_token, body, status
    ):
        retry = spider.parse_ajax_token(response=make_response(body, status=status))

        assert isinstance(retry, Request)
        assert retry.url == BASE_URL
        assert retry.cookies == {"aws-waf-token": "fresh"}
        assert retry.meta["challenge_retry"] == 1
        assert retry.dont_filter is True

    def test_waf_rejection_drops_the_cached_token(self, spider, fresh_token):
        spider.parse_ajax_token(response=make_response(WAF_BODY, status=202))

        assert fresh_token == [BASE_URL]

    def test_other_blocks_keep_the_cached_token(self, spider, fresh_token):
        spider.parse_ajax_token(response=make_response(AKAMAI_BODY))

        assert fresh_token == []

    def test_retry_reuses_the_newly_harvested_user_agent(self, spider, fresh_token):
        retry = spider.parse_ajax_token(response=make_response(WAF_BODY, status=202))

        assert spider.waf_user_agent == "Mozilla/5.0 (harvested)"
        assert retry.headers[b"User-Agent"] == b"Mozilla/5.0 (harvested)"

    def test_retries_are_capped(self, spider, fresh_token):
        response = make_response(WAF_BODY, status=202, retries=MAX_CHALLENGE_RETRIES)

        with pytest.raises(ValueError, match="No usable page from"):
            spider.parse_ajax_token(response=response)

    def test_storefront_is_parsed_instead_of_retried(self, spider, fresh_token):
        request = spider.parse_ajax_token(response=make_response(STOREFRONT_BODY))

        assert request.headers[b"anti-csrftoken-a2z"] == b"token"
        assert fresh_token == []


class TestCsrfStep:
    """The second step of the flow gets bot-checked too."""

    CSRF_BODY = b'<html><script>var x = { CSRF_TOKEN : "csrf-value" };</script></html>'

    def test_csrf_page_builds_the_address_change_request(self, spider, fresh_token):
        request = spider.parse_cookies(
            response=make_response(self.CSRF_BODY), cookies={"session-id": "1"}
        )

        assert request.method == "POST"
        assert request.headers[b"anti-csrftoken-a2z"] == b"csrf-value"
        assert b'"zipCode": "30322"' in request.body
        assert fresh_token == []

    def test_missing_csrf_token_restarts_the_flow(self, spider, fresh_token):
        retry = spider.parse_cookies(
            response=make_response(AKAMAI_BODY), cookies={"session-id": "1"}
        )

        assert retry.url == BASE_URL
        assert retry.callback == spider.parse_ajax_token
        assert retry.meta["challenge_retry"] == 1
