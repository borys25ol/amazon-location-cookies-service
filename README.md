Amazon Location Cookies
====================

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Pre-commit: enabled](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=flat)](https://github.com/pre-commit/pre-commit)

## Description

This project can be used to get Amazon location cookies from specific Amazon `zip-code` and country-specific domains like `.de`, `.co.uk`, etc.

It will be very helpful when you are using random geolocation proxies for scraping data from Amazon because Amazon returns content based on user IP.

Tested location at the moment:
- US (30322)
- ES (28010)
- UK (E1 6AN)
- DE (80686)
- IT (20162)
- FR (75001)

Also, there is the ability to change `delivery country` (ship outside the current county) for example delivery from the US (`.com`) to the France (`FR`).

There no restrictions for choosing "outside country". You can choose whatever you want (if it available on Amazon).

How it works
------------

Each crawl walks the same three requests Amazon's own "Deliver to" widget makes:

1. `GET /` — read the `glowValidationToken` out of the storefront HTML.
2. `GET /portal-migration/hz/glow/get-rendered-address-selections` — read the `CSRF_TOKEN`.
3. `POST /portal-migration/hz/glow/address-change` — set the location and keep the resulting cookies.

### Getting past the AWS WAF challenge

Amazon fronts its storefronts with an AWS WAF Bot Control challenge. A plain HTTP
client never reaches step 1: it gets `202` with an `x-amzn-waf-action: challenge`
header and a ~2KB stub page that loads `challenge.js`, instead of the storefront.
Neither browser-like headers nor TLS fingerprint impersonation are enough on their
own — the challenge script has to actually run.

So a headless Chromium runs it once. The browser is handed an `aws-waf-token`
cookie that stays valid for roughly four days and is fully replayable from an
ordinary HTTP client, so the token is harvested, cached on disk, and attached to
the spider's requests. Only a cache miss pays for a browser launch; everything
after that is a normal Scrapy request.

Three consequences worth knowing about:

- **The user agent is part of the deal.** The token is issued against the browser
  that solved the challenge, and replaying it under a different user agent gets
  challenged again. Every request in the flow reuses the harvested user agent,
  which is why spiders build headers through `build_headers()` instead of using
  `HEADERS` directly.
- **Cached tokens go stale unpredictably.** The cookie advertises a ~4 day
  expiry, but Amazon stops honouring tokens well before that — sometimes within
  the hour. A crawl that gets challenged therefore throws its token away,
  harvests a new one and asks again, up to three times, rather than failing. This
  retry is what actually keeps things working; the cache TTL is only there to
  avoid pointless browser launches.
- **Not every visit goes through the WAF.** Some sessions land on an Akamai Bot
  Manager edge instead, which answers `200` with a ~2KB interstitial that sets
  `ak_bmsc` and meta-refreshes to `/?bm-verify=...`. Scrapy's
  `MetaRefreshMiddleware` follows that redirect and usually ends up on the real
  storefront; if it does not, the interstitial is treated as a challenge and
  retried like any other. The harvest itself prefers the WAF branch, because that
  is the one that produces a token worth caching.

### WAF token cache

Tokens live in `.waf_cache/<host>.json` (gitignored) and are refreshed after an
hour. Point `WAF_CACHE_DIR` somewhere else to relocate them, or force a fresh
harvest with:

```shell
rm -rf .waf_cache
```

A cold cache costs about 5 seconds of browser time per storefront; warm crawls
finish in about 2 seconds.

Developing
-----------

Install pre-commit hooks to ensure code quality checks and style checks

```shell
make install_hooks
```

Run the tests. They cover the bot-challenge handling, which is awkward to
exercise against the live site because Amazon only challenges intermittently:

```shell
make test
```

Then see `Configuration` section

Configuration
--------------

Replace `.env.example` with real `.env`, changing placeholders

```
SECRET_KEY=changeme
SCRAPYRT_URL=http://127.0.0.1:7800/crawl.json
```

`SCRAPYRT_URL` above is for running the API on the host. Docker Compose overrides
it with the `scrapyrt` service hostname, so the same `.env` works for both.

Local install
-------------

Setup and activate a python3 virtualenv via your preferred method. e.g. and install production requirements:

```shell
make ve
```

This also downloads the Chromium build that Playwright uses to solve the WAF
challenge. Installing requirements without `make ve` needs it done explicitly:

```shell
pip install -r requirements.txt
playwright install chromium
```

For remove virtualenv:

```shell
make clean
```

Local run
-------------

For changing location:

```shell
scrapy crawl amazon:location-delivery-session -a country=US -a zip_code=30322
```

For changing country:

```shell
scrapy crawl amazon:outside-delivery-session -a country=US -a delivery_country=FR
```

The first crawl against a given storefront launches a browser to solve the WAF
challenge and takes a few seconds longer than the ones that follow.

Run using local ScrapyRT service:

```shell
scrapyrt --ip 0.0.0.0 --port 7800

curl -X 'GET' \
 'http://0.0.0.0:7800/crawl.json?start_requests=1&spider_name=amazon:location-delivery-session&crawl_args={"zip_code":"30332","country":"US"}'

curl -X 'GET' \
 'http://0.0.0.0:7800/crawl.json?start_requests=1&spider_name=amazon:outside-delivery-session&crawl_args={"delivery_country":"FR","country":"US"}'
```

ScrapyRT response example:

```json
{
    "status": "ok",
    "items": [
        {
            "session-id": "136-1132730-6579246",
            "session-id-time": "2082787201l",
            "i18n-prefs": "USD",
            "sp-cdn": "L5Z9:UA",
            "skin": "noskin"
        }
    ],
    "items_dropped": [],
    "stats": {
        "downloader/request_bytes": 2433,
        "downloader/request_count": 3,
        "downloader/request_method_count/GET": 2,
        "downloader/request_method_count/POST": 1,
        "downloader/response_bytes": 110566,
        "downloader/response_count": 3,
        "downloader/response_status_count/200": 3,
        "elapsed_time_seconds": 2.278885,
        "finish_reason": "finished",
        "finish_time": "2024-02-23 15:50:15",
        "httpcompression/response_bytes": 379835,
        "httpcompression/response_count": 3,
        "item_scraped_count": 1,
        "log_count/DEBUG": 4,
        "log_count/INFO": 9,
        "log_count/WARNING": 1,
        "memusage/max": 86364160,
        "memusage/startup": 86364160,
        "request_depth_max": 2,
        "response_received_count": 3,
        "scheduler/dequeued": 3,
        "scheduler/dequeued/memory": 3,
        "scheduler/enqueued": 3,
        "scheduler/enqueued/memory": 3,
        "start_time": "2024-02-23 15:50:13"
    },
    "spider_name": "amazon:location-session"
}
```

Run the API on the host, in a second shell, with ScrapyRT already running:

```shell
make runserver
```

Swagger UI is served at the root, `http://127.0.0.1:8000/`. Note that
`country_code` is validated against `US`, `UK`, `GB`, `DE`, `ES`, `IT`, `FR` and
must be uppercase — lowercase returns `422`.

#### Run in Docker:

Run docker containers:

```shell
make docker_build
```

`make docker_up` is enough once the images are built.

The image ships a Chromium headless shell for the WAF challenge, which puts it at
roughly 1.1GB — most of that is the browser itself. It is built on `python:3.12-slim`
with `playwright install --only-shell`; using the full `python:3.12` and the full
Chromium build instead costs about 1.7GB more, for an X11 and GTK stack that a
headless run never touches. Alpine is not an option here: Playwright's browser
builds are linked against glibc.

The `.waf_cache` directory lives inside the container and is lost on
`docker compose down`, so the first request per storefront pays for a browser run
again — mount it as a volume if that matters.

Run using dockerized API service:

```shell
curl -X 'GET' \
  'http://127.0.0.1:8000/api/v1/locations/cookies?zip_code=30322&country_code=US' \
  -H 'accept: application/json'

curl -X 'GET' \
  'http://127.0.0.1:8000/api/v1/countries/cookies?delivery_country_code=FR&country_code=US' \
  -H 'accept: application/json'
```

Docker API response example for changed **location**:

```json
{
  "success": true,
  "data": {
    "zip_code": "30322",
    "country_code": "US",
    "cookies": {
      "session-id": "138-7674092-2025337",
      "session-id-time": "2082787201l",
      "i18n-prefs": "USD",
      "sp-cdn": "L5Z9:UA",
      "skin": "noskin"
    }
  },
  "message": "Cookies for zip code: `30322` extracted successfully",
  "errors": []
}
```

Docker API response example for changed **country**:

```json
{
  "success": true,
  "data": {
    "delivery_country_code": "FR",
    "country_code": "US",
    "cookies": {
      "session-id": "138-7674092-2025337",
      "session-id-time": "2082787201l",
      "i18n-prefs": "USD",
      "sp-cdn": "L5Z9:UA",
      "skin": "noskin"
    }
  },
  "message": "Cookies for delivery country: `FR` extracted successfully",
  "errors": []
}
```

How to use?
-------------

The cookies below are replayed against Amazon by a plain `requests` client. That
client is subject to the same bot defences described in
[How it works](#how-it-works): the returned session cookies usually pass on their
own, but a request that gets challenged comes back as a `202` with an
`x-amzn-waf-action` header, or as a ~2KB page with no `glow-ingress-line2` in it.
Treat both as "retry", not as "the location did not stick".

Check extracted amazon location cookies from python script:

```python
import re
from time import sleep
from typing import Dict

import requests

API_URL = "http://127.0.0.1:8000/api/v1/location/cookies?zip_code={zip_code}&country_code={country_code}"

HEADERS = {"user-agent": "user-agent"}

LOCATIONS_CONFIG = {
    "US": {"zip_code": "30322", "amazon_url": "https://amazon.com"},
    "ES": {"zip_code": "28010", "amazon_url": "https://amazon.es"},
    "UK": {"zip_code": "E1 6AN", "amazon_url": "https://amazon.co.uk"},
    "DE": {"zip_code": "80686", "amazon_url": "https://amazon.de"},
    "IT": {"zip_code": "20162", "amazon_url": "https://amazon.it"},
    "FR": {"zip_code": "75001", "amazon_url": "https://amazon.fr"},
}

LOCATION_REGEX = r'(?s)glow-ingress-line2">(.+?)<'


def get_location_cookies(country: str, zip_code: str) -> Dict[str, str]:
    """
    Make request to Amazon Location Cookies service for getting location cookies.
    """
    api_url = API_URL.format(zip_code=zip_code, country_code=country)
    json_data = requests.get(url=api_url).json()
    cookies = json_data["data"]["cookies"]
    return cookies


def check_location_cookies(amazon_url: str, cookies: Dict[str, str]) -> str:
    """
    Make request to country specific Amazon url with location cookies.
    """
    amazon_response = requests.get(url=amazon_url, cookies=cookies, headers=HEADERS)
    location = re.search(LOCATION_REGEX, amazon_response.text)
    return location.group(1).strip()


def main() -> None:
    """
    Project entry point.
    """
    for country in LOCATIONS_CONFIG:
        print("Check cookies for country: ", country)
        amazon_url = LOCATIONS_CONFIG[country]["amazon_url"]
        zip_code = LOCATIONS_CONFIG[country]["zip_code"]

        # Extract cookies via Amazon Location Service.
        cookies = get_location_cookies(country=country, zip_code=zip_code)
        print("Got Amazon cookies: ", cookies)

        # Check response using location cookies.
        response = check_location_cookies(amazon_url=amazon_url, cookies=cookies)
        print("Amazon response: ", response)
        sleep(5)


if __name__ == '__main__':
    main()

```

Script response:

```text
Check cookies for country:  US
Got Amazon cookies:  {'session-id': '145-9152803-6066337'}
Amazon response:  Atlanta 30322&zwnj;


Check cookies for country:  ES
Got Amazon cookies:  {'session-id': '258-6822533-6748349'}
Amazon response:  Madrid 28010&zwnj;
```


Check extracted amazon outside delivery cookies from python script:

```python
import re
from time import sleep
from typing import Dict

import requests

API_URL = "http://127.0.0.1:8000/api/v1/countries/cookies?delivery_country_code={delivery_country}&country_code={country_code}"

HEADERS = {"user-agent": "user-agent"}

COUNTRIES_CONFIG = {
    "US": {"delivery_country": "CL", "amazon_url": "https://www.amazon.com"},
    "ES": {"delivery_country": "PE", "amazon_url": "https://amazon.es"},
    "UK": {"delivery_country": "UA", "amazon_url": "https://amazon.co.uk"},
    "DE": {"delivery_country": "MX", "amazon_url": "https://amazon.de"},
    "IT": {"delivery_country": "ES", "amazon_url": "https://amazon.it"},
}

LOCATION_REGEX = r'(?s)glow-ingress-line2">(.+?)<'


def get_location_cookies(country: str, delivery_country: str) -> Dict[str, str]:
    """
    Make request to Amazon Location Cookies service for getting location cookies.
    """
    api_url = API_URL.format(delivery_country=delivery_country, country_code=country)
    json_data = requests.get(url=api_url).json()
    cookies = json_data["data"]["cookies"]
    return cookies


def check_location_cookies(amazon_url: str, cookies: Dict[str, str]) -> str:
    """
    Make request to country specific Amazon url with location cookies.
    """
    amazon_response = requests.get(url=amazon_url, cookies=cookies, headers=HEADERS)
    location = re.search(LOCATION_REGEX, amazon_response.text)
    return location.group(1).strip()


def main() -> None:
    """
    Project entry point.
    """
    for country in COUNTRIES_CONFIG:
        print("Check cookies for country: ", country)
        amazon_url = COUNTRIES_CONFIG[country]["amazon_url"]
        delivery_country = COUNTRIES_CONFIG[country]["delivery_country"]

        # Extract cookies via Amazon Location Service.
        cookies = get_location_cookies(country=country, delivery_country=delivery_country)
        print("Got Amazon cookies: ", cookies)

        # Check response using location cookies.
        response = check_location_cookies(amazon_url=amazon_url, cookies=cookies)
        print("Amazon response: ", response)
        sleep(5)


if __name__ == '__main__':
    main()

```
Script response:

```text
Check cookies for country:  UK
Got Amazon cookies:  {'session-id': '262-8205108-4515828', 'session-id-time': '2082787201l', 'i18n-prefs': 'GBP', 'sp-cdn': 'L5Z9:UA'}
Amazon response:  Ukraine

Check cookies for country:  ES
Got Amazon cookies:  {'session-id': '260-1914639-0616257', 'session-id-time': '2082787201l', 'i18n-prefs': 'EUR'}
Amazon response:  Perú
```
