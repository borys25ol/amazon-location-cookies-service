"""
AWS WAF Bot Control bypass.

Amazon fronts every storefront with an AWS WAF challenge: a plain HTTP client
gets `202` with `x-amzn-waf-action: challenge` and a stub page that loads
`challenge.js`, instead of the storefront HTML. Solving the challenge requires
executing that script, so a real browser has to do it once.

The browser hands back an `aws-waf-token` cookie which is valid for ~4 days and
is fully replayable from a plain HTTP client, so the token is harvested with a
headless Chromium and cached on disk. Only a cache miss pays for a browser run;
every spider request afterwards is an ordinary Scrapy request.

Amazon does not put every storefront visit behind the WAF. Some sessions land on
an Akamai Bot Manager edge instead, which answers `200` with a ~2KB interstitial
that sets `ak_bmsc` and meta-refreshes to `/?bm-verify=...`. That branch hands
out nothing worth caching, so the harvest retries with a fresh browser context
until it lands on the WAF branch. At crawl time the interstitial is handled
differently -- see `AmazonBaseSessionSpider._retry_start`.

A cached token is not reliable for as long as its cookie claims. The `expires`
attribute says roughly four days, but Amazon stops accepting tokens well before
that, sometimes within the hour. The TTL below is therefore only an optimisation;
what actually keeps crawls working is spiders noticing a challenged response,
calling `invalidate_waf_session`, and harvesting again.

The harvest runs in a subprocess (`python -m main.waf <url>`) because the
Playwright sync API refuses to start inside a thread that already runs an
asyncio event loop, which is exactly what the Scrapy/Twisted reactor is.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from playwright.sync_api import Browser

CACHE_DIR = Path(
    os.getenv("WAF_CACHE_DIR", Path(__file__).parent.parent / ".waf_cache")
)

# The cookie advertises a ~4 day expiry, but Amazon invalidates tokens long
# before that -- often within the hour. The TTL is therefore only an optimisation
# to avoid obviously pointless browser launches; correctness comes from spiders
# calling `invalidate_waf_session` and re-harvesting when a request is challenged.
CACHE_TTL_SECONDS = 60 * 60

HARVEST_TIMEOUT_SECONDS = 180

# Attempts to land on the replayable WAF branch before giving up. A storefront
# can stay pinned to the Akamai branch for tens of seconds at a time, so the
# attempts are spaced out rather than fired back to back.
HARVEST_ATTEMPTS = 6
HARVEST_RETRY_BACKOFF_SECONDS = 5

# Only the challenge token is kept. The browser also picks up a session-id and a
# pile of ad-network cookies, but reusing a cached session across crawls would
# make concurrent requests for different locations share one Amazon session --
# every crawl must get its own session-id issued by the first spider request.
_WANTED_COOKIES = ("aws-waf-token",)


class WafChallengeError(RuntimeError):
    """Raised when the WAF challenge could not be solved."""


def get_waf_session(base_url: str) -> tuple[dict[str, str], str]:
    """
    Return `(cookies, user_agent)` able to pass the WAF challenge for `base_url`.

    Served from the on-disk cache when possible, otherwise solved with a browser.
    The user agent matters: the token is issued against the browser that solved
    the challenge, so replaying it under a different user agent gets challenged
    again.
    """
    host = urlparse(base_url).netloc
    if cached := _read_cache(host):
        return cached["cookies"], cached["user_agent"]

    payload = _harvest(base_url)
    # A token-less payload means the browser only ever saw the Akamai branch. It
    # is still worth crawling with, but there is nothing to cache.
    if "aws-waf-token" in payload["cookies"]:
        _write_cache(host, payload)
    return payload["cookies"], payload["user_agent"]


def invalidate_waf_session(base_url: str) -> None:
    """
    Drop the cached token for `base_url` so the next lookup harvests a new one.

    Call this whenever a request comes back challenged: a cached token can stop
    being accepted at any point, and there is no way to tell from the token
    itself.
    """
    _cache_path(urlparse(base_url).netloc).unlink(missing_ok=True)


def _cache_path(host: str) -> Path:
    return CACHE_DIR / f"{host}.json"


def _read_cache(host: str) -> dict | None:
    """
    Load a cached token, ignoring anything stale or unreadable.
    """
    path = _cache_path(host)
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return None

    if time.time() - payload.get("created_at", 0) > CACHE_TTL_SECONDS:
        return None
    if "aws-waf-token" not in payload.get("cookies", {}):
        return None
    return payload


def _write_cache(host: str, payload: dict) -> None:
    """
    Persist a harvested token atomically, so concurrent crawls never read a
    half-written file.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=CACHE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as tmp_file:
            json.dump(payload, tmp_file)
        os.replace(tmp_path, _cache_path(host))
    except OSError:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def _harvest(base_url: str) -> dict:
    """
    Solve the challenge in a subprocess and return its payload.
    """
    process = subprocess.run(
        [sys.executable, "-m", "main.waf", base_url],
        capture_output=True,
        timeout=HARVEST_TIMEOUT_SECONDS,
    )
    if process.returncode != 0:
        raise WafChallengeError(
            f"WAF challenge harvest failed for {base_url}: "
            f"{process.stderr.decode('utf-8', 'replace').strip()}"
        )
    return json.loads(process.stdout)


def solve_challenge(base_url: str) -> dict:
    """
    Drive a headless browser through the WAF challenge for `base_url`.

    Retries with a fresh browser context until the session lands on the WAF
    branch, which is the only one that yields a cacheable token. Falling back to
    a token-less session is better than giving up: the spider can still get
    through the Akamai interstitial, it just has nothing to cache.

    Must run in a process without a running event loop. Use `get_waf_session`
    instead of calling this directly.
    """
    from playwright.sync_api import sync_playwright

    fallback = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            user_agent = _plausible_user_agent(browser)
            for attempt_no in range(HARVEST_ATTEMPTS):
                if payload := _attempt_harvest(browser, base_url, user_agent):
                    if "aws-waf-token" in payload["cookies"]:
                        return payload
                    fallback = payload
                if attempt_no < HARVEST_ATTEMPTS - 1:
                    time.sleep(HARVEST_RETRY_BACKOFF_SECONDS)
        finally:
            browser.close()

    if fallback:
        return fallback
    raise WafChallengeError(
        f"Could not reach the storefront at {base_url} "
        f"in {HARVEST_ATTEMPTS} browser attempts"
    )


def _plausible_user_agent(browser: "Browser") -> str:
    """
    Return the browser's own user agent with the headless giveaway removed.

    Playwright's headless Chromium announces itself as `HeadlessChrome/...`,
    which is about the loudest bot signal a request can carry. Everything else
    in the string -- platform, engine, version -- is genuine and left alone.
    """
    context = browser.new_context()
    try:
        page = context.new_page()
        user_agent: str = page.evaluate("navigator.userAgent")
    finally:
        context.close()
    return user_agent.replace("HeadlessChrome/", "Chrome/")


def _attempt_harvest(browser: "Browser", base_url: str, user_agent: str) -> dict | None:
    """
    Load the storefront in a throwaway context, returning the harvest payload if
    the browser reached a real storefront -- with a WAF token when one was issued.
    """
    context = browser.new_context(locale="en-US", user_agent=user_agent)
    try:
        page = context.new_page()
        page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
        # challenge.js needs a moment to run and reload the page with a token.
        page.wait_for_timeout(3_000)

        # A bot-block page has no glow widget; only a real storefront does.
        if not page.query_selector("#glowValidationToken"):
            return None

        return {
            "cookies": {
                cookie["name"]: cookie["value"]
                for cookie in context.cookies()
                if cookie["name"] in _WANTED_COOKIES
            },
            "user_agent": user_agent,
            "created_at": time.time(),
        }
    finally:
        context.close()


if __name__ == "__main__":
    json.dump(solve_challenge(sys.argv[1]), sys.stdout)
