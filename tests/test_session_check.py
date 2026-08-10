"""Tests for the session check endpoint.

The point of the endpoint is telling three outcomes apart: the session still
pins a location, it no longer does, or our own request was turned away and the
question cannot be answered. That last one is what makes a naive check useless,
so it gets the most attention here.
"""

import pytest
import requests

from main.api.exceptions import AmazonUnreachableException, SessionCheckFailedException
from main.api.schemas.common import SessionCheckRequest
from main.api.services import session_check
from main.api.services.session_check import (
    AmazonSessionCheckService,
    extract_location,
    matches_expected,
)

STOREFRONT = '<span id="glow-ingress-line2">Atlanta 30322&zwnj;</span>'
STOREFRONT_ZWNJ = '<span id="glow-ingress-line2">  Madrid 28010‌ </span>'
WAF_CHALLENGE = '<html><script>window.gokuProps = {"key":"..."}</script></html>'
AKAMAI_INTERSTITIAL = (
    '<html><meta http-equiv="refresh" content="5; URL=\'/?bm-verify=x\'"></html>'
)


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeSession:
    """Stands in for the requests session, answering with each page in turn."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.sent = {}
        self.urls = []

    def get(self, **kwargs):
        self.sent.update(kwargs)
        self.urls.append(kwargs.get("url"))
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return FakeResponse(answer)


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(
        session_check,
        "get_waf_session",
        lambda base_url: ({"aws-waf-token": "t"}, "Mozilla/5.0 (test)"),
    )
    return AmazonSessionCheckService()


@pytest.fixture
def answering(monkeypatch):
    """Make the service's session return `answer` (or raise it)."""

    def _answering(*answers):
        session = FakeSession(*answers)
        monkeypatch.setattr(session_check, "build_session", lambda: session)
        return session

    return _answering


def request_for(expected=None):
    return SessionCheckRequest(
        country_code="US", cookies={"session-id": "1"}, expected=expected
    )


class TestExtractLocation:
    def test_reads_the_glow_widget(self):
        assert extract_location(html=STOREFRONT) == "Atlanta 30322"

    @pytest.mark.parametrize("html", [STOREFRONT, STOREFRONT_ZWNJ])
    def test_strips_the_padding_in_either_form(self, html):
        """Amazon sends the non-joiner as a character or as an entity."""
        assert "zwnj" not in extract_location(html=html)
        assert "\u200c" not in extract_location(html=html)

    @pytest.mark.parametrize("html", [WAF_CHALLENGE, AKAMAI_INTERSTITIAL, ""])
    def test_no_widget_means_not_a_storefront(self, html):
        assert extract_location(html=html) is None


class TestMatchesExpected:
    def test_substring_match_is_case_insensitive(self):
        assert matches_expected(location="Atlanta 30322", expected="atlanta") is True

    def test_zip_code_matches(self):
        assert matches_expected(location="Atlanta 30322", expected="30322") is True

    def test_country_name_matches(self):
        assert matches_expected(location="Ukraine", expected="Ukraine") is True

    def test_mismatch_is_false(self):
        assert matches_expected(location="Atlanta 30322", expected="90210") is False

    def test_no_expectation_yields_no_opinion(self):
        assert matches_expected(location="Atlanta 30322", expected=None) is None


class TestCheckSession:
    def test_live_session_reports_the_location(self, service, answering):
        answering(STOREFRONT_ZWNJ)

        response = service.check_session(data=request_for(expected="28010"))

        assert response.data["location"] == "Madrid 28010"
        assert response.data["valid"] is True
        assert response.message == "Session is alive"

    def test_stale_session_is_reported_as_such(self, service, answering):
        answering(STOREFRONT_ZWNJ)

        response = service.check_session(data=request_for(expected="90210"))

        assert response.data["valid"] is False
        assert response.message == "Session is stale"

    @pytest.mark.parametrize("html", [WAF_CHALLENGE, AKAMAI_INTERSTITIAL])
    def test_bot_check_is_not_reported_as_a_dead_session(
        self, service, answering, html
    ):
        answering(html)

        with pytest.raises(SessionCheckFailedException) as error:
            service.check_session(data=request_for(expected="30322"))

        assert error.value.status_code == 409

    def test_network_failure_surfaces_as_bad_gateway(self, service, answering):
        answering(requests.ConnectionError("no route"))

        with pytest.raises(AmazonUnreachableException) as error:
            service.check_session(data=request_for())

        assert error.value.status_code == 502

    def test_the_check_carries_a_waf_token(self, service, answering):
        session = answering(STOREFRONT_ZWNJ)

        service.check_session(data=request_for())

        assert session.sent["cookies"]["aws-waf-token"] == "t"
        assert session.sent["cookies"]["session-id"] == "1"
        assert session.sent["headers"]["user-agent"] == "Mozilla/5.0 (test)"


class TestAkamaiInterstitial:
    """Akamai answers a stub that meta-refreshes to the real storefront."""

    def test_the_interstitial_is_followed(self, service, answering):
        session = answering(AKAMAI_INTERSTITIAL, STOREFRONT_ZWNJ)

        response = service.check_session(data=request_for(expected="28010"))

        assert response.data["location"] == "Madrid 28010"
        assert session.urls == [
            "https://www.amazon.com",
            "https://www.amazon.com/?bm-verify=x",
        ]

    def test_a_storefront_is_not_followed_anywhere(self, service, answering):
        session = answering(STOREFRONT_ZWNJ)

        service.check_session(data=request_for())

        assert session.urls == ["https://www.amazon.com"]

    def test_retrying_after_the_interstitial_can_still_win(self, service, answering):
        """Clearing the interstitial sets ak_bmsc; asking again then works."""
        session = answering(AKAMAI_INTERSTITIAL, AKAMAI_INTERSTITIAL, STOREFRONT_ZWNJ)

        response = service.check_session(data=request_for(expected="28010"))

        assert response.data["valid"] is True
        assert len(session.urls) == 3

    def test_persistent_blocking_gives_up(self, service, answering):
        answering(AKAMAI_INTERSTITIAL, AKAMAI_INTERSTITIAL, AKAMAI_INTERSTITIAL)

        with pytest.raises(SessionCheckFailedException):
            service.check_session(data=request_for())

    def test_no_refresh_target_means_no_second_request(self, service, answering):
        session = answering(WAF_CHALLENGE)

        with pytest.raises(SessionCheckFailedException):
            service.check_session(data=request_for())

        assert session.urls == ["https://www.amazon.com"]

    def test_every_hop_carries_the_callers_cookies(self, service, answering):
        """Without them Amazon reports the IP's location and the session reads dead."""
        session = answering(AKAMAI_INTERSTITIAL, STOREFRONT_ZWNJ)

        service.check_session(data=request_for())

        assert session.sent["cookies"]["session-id"] == "1"
        assert session.sent["cookies"]["aws-waf-token"] == "t"
