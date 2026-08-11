Amazon Location Cookies
====================

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

[![CI](https://github.com/borys25ol/amazon-location-cookies-service/actions/workflows/ci.yaml/badge.svg)](https://github.com/borys25ol/amazon-location-cookies-service/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Pre-commit: enabled](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=flat)](https://github.com/pre-commit/pre-commit)

## Description

This service gets Amazon cookies that set a delivery location. You give it a zip
code or a delivery country. It gives you the cookies.

Amazon shows different content for different locations. Amazon selects the
location from the IP address of the client. If you use proxy servers in other
countries, these cookies set the location that Amazon uses.

These sites and locations are tested:

| Country code | Amazon site     | Example zip code |
|--------------|-----------------|------------------|
| `US`         | `amazon.com`    | 30322            |
| `UK`, `GB`   | `amazon.co.uk`  | E1 6AN           |
| `DE`         | `amazon.de`     | 80686            |
| `ES`         | `amazon.es`     | 28010            |
| `IT`         | `amazon.it`     | 20162            |
| `FR`         | `amazon.fr`     | 75001            |

The service can also set a delivery country that is different from the country
of the site. For example, it can set delivery from the US site to France. You
can use all the countries that Amazon delivers to.

How the service operates
------------------------

For each location, the service sends the same three requests as the
"Deliver to" control of Amazon:

1. `GET /` — the service reads the `glowValidationToken` value from the HTML.
2. `GET /portal-migration/hz/glow/get-rendered-address-selections` — the service
   reads the `CSRF_TOKEN` value.
3. `POST /portal-migration/hz/glow/address-change` — the service sets the
   location. Then it keeps the cookies from the response.

### How the service gets through the AWS WAF challenge

Amazon protects each site with an AWS WAF Bot Control challenge. A usual HTTP
client cannot complete step 1. Amazon sends a `202` response with an
`x-amzn-waf-action: challenge` header. The response contains a small page of
approximately 2 KB that loads `challenge.js`. Amazon does not send the site page.

Browser headers are not sufficient. TLS fingerprint impersonation is also not
sufficient. A program must execute the challenge script.

Therefore the service starts a headless Chromium browser one time. Amazon gives
an `aws-waf-token` cookie to that browser. A usual HTTP client can then use this
cookie. The service keeps the cookie on the disk. Only the first request starts
a browser. All the subsequent requests are usual Scrapy requests.

Three effects of this design are important:

- **The token operates with one user agent only.** Amazon gives the token to the
  browser that completed the challenge. If you send the token with a different
  user agent, Amazon sends the challenge again. Thus all the requests use the
  same user agent. The spiders make their headers with `build_headers()`. Do not
  use `HEADERS` directly.
- **A token becomes invalid at an unknown time.** The cookie shows an expiry
  time of approximately 4 days. But Amazon frequently refuses the token much
  sooner, sometimes in less than one hour. If Amazon sends a challenge, the
  spider discards the token, gets a new token, and sends the request again. The
  spider does this two times as a maximum. This procedure keeps the service
  operational. The cache time limit only prevents unnecessary browser starts.
- **Amazon does not use the WAF for all the requests.** Some sessions go to an
  Akamai Bot Manager server. That server sends a `200` response with a small
  page of approximately 2 KB. The page sets an `ak_bmsc` cookie and has a meta
  refresh to `/?bm-verify=...`. The `MetaRefreshMiddleware` of Scrapy obeys the
  refresh and usually gets the correct page. If it does not, the spider uses the
  same retry procedure. The browser procedure tries to get a WAF token, because
  only a WAF token is useful in the cache.

### The WAF token cache

The service keeps the tokens in `.waf_cache/<host>.json`. Git ignores this
directory. The service gets a new token after one hour.

To keep the tokens in a different directory, set the `WAF_CACHE_DIR` variable.
To remove all the tokens, use this command:

```shell
rm -rf .waf_cache
```

If the cache is empty, each site needs approximately 5 seconds more for the
browser. If the cache contains a token, a request needs approximately 2 seconds.

Development
-----------

To install the pre-commit hooks, use this command:

```shell
make install_hooks
```

To run the tests, use this command:

```shell
make test
```

The tests examine the bot challenge procedures. It is difficult to examine these
procedures against the Amazon sites, because Amazon does not send a challenge
for all the requests.

Then read the `Configuration` section.

Configuration
-------------

Copy `.env.example` to `.env` and replace the values:

```
SECRET_KEY=changeme
SCRAPYRT_URL=http://127.0.0.1:7800/crawl.json
```

This `SCRAPYRT_URL` value is correct for the API on your computer. Docker
Compose replaces the value with the name of the `scrapyrt` service. Thus the
same `.env` file is correct for the two conditions.

Installation on your computer
-----------------------------

To make the virtual environment and install the requirements, use this command:

```shell
make ve
```

This command needs [uv](https://docs.astral.sh/uv/getting-started/installation/).
uv reads the Python version from `.python-version`. If your computer does not
have that version, uv gets it. Thus your environment agrees with the Docker
image. It does not use the version that `python3` refers to. The command also
gets the Chromium browser for Playwright.

If you do not use `make ve`, do the two steps manually:

```shell
pip install -r requirements.txt
playwright install chromium
```

To remove the virtual environment, use this command:

```shell
make clean
```

How to run the service on your computer
---------------------------------------

To set a location, use this command:

```shell
scrapy crawl amazon:location-delivery-session -a country=US -a zip_code=30322
```

To set a delivery country, use this command:

```shell
scrapy crawl amazon:outside-delivery-session -a country=US -a delivery_country=FR
```

The first request to each site starts a browser for the WAF challenge. Thus the
first request needs some seconds more than the subsequent requests.

To use the local ScrapyRT service, use these commands:

```shell
scrapyrt --ip 0.0.0.0 --port 7800

curl -X 'GET' \
 'http://0.0.0.0:7800/crawl.json?start_requests=1&spider_name=amazon:location-delivery-session&crawl_args={"zip_code":"30332","country":"US"}'

curl -X 'GET' \
 'http://0.0.0.0:7800/crawl.json?start_requests=1&spider_name=amazon:outside-delivery-session&crawl_args={"delivery_country":"FR","country":"US"}'
```

This is an example of a ScrapyRT response:

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

ScrapyRT must be in operation before you start the API. Start the API in a
second shell with this command:

```shell
make runserver
```

The Swagger UI is at the root address, `http://127.0.0.1:8000/`. The
`country_code` value must be `US`, `UK`, `GB`, `DE`, `ES`, `IT` or `FR`. Use
capital letters only. Small letters cause a `422` error.

#### How to run the service in Docker

To make the images and start the containers, use this command:

```shell
make docker_build
```

If the images exist already, `make docker_up` is sufficient.

The image contains a Chromium headless shell for the WAF challenge. Thus the
image is approximately 1.1 GB, and the browser is the largest part. The image
uses `python:3.14-slim` and the `playwright install --only-shell` command. The
full `python:3.14` image and the full Chromium browser add approximately 1.7 GB.
That additional space contains an X11 and GTK stack that a headless browser does
not use. Alpine Linux is not possible, because the Playwright browsers need
glibc.

The `.waf_cache` directory is inside the container. Docker deletes the directory
with the `docker compose down` command. Thus the first request to each site
starts a browser again. To keep the tokens, attach the directory as a volume.

To use the API in Docker, use these commands:

```shell
curl -X 'GET' \
  'http://127.0.0.1:8000/api/v1/locations/cookies?zip_code=30322&country_code=US' \
  -H 'accept: application/json'

curl -X 'GET' \
  'http://127.0.0.1:8000/api/v1/countries/cookies?delivery_country_code=FR&country_code=US' \
  -H 'accept: application/json'
```

This is an example of a response for a **location**:

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

This is an example of a response for a **delivery country**:

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

How to use the cookies
----------------------

Send two requests. First, ask the service for the cookies. Then send the cookies
to Amazon.

```python
import re

import requests

API_URL = "http://127.0.0.1:8000/api/v1/locations/cookies"
AMAZON_URL = "https://www.amazon.com"

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)
PROXIES = {"https": "http://user:password@proxy.example.com:10080"}

# 1. Ask the service for cookies that set a location.
response = requests.get(
    url=API_URL, params={"zip_code": "30322", "country_code": "US"}
)
cookies = response.json()["data"]["cookies"]

# 2. Send the cookies. Amazon shows the location in its "Deliver to" control.
page = requests.get(
    url=AMAZON_URL, cookies=cookies, headers={"user-agent": BROWSER_UA}, proxies=PROXIES
)
location = re.search(r'(?s)glow-ingress-line2">(.+?)<', page.text)
print(location.group(1).replace("&zwnj;", "").strip())
```

```text
Atlanta 30322
```

This is the full procedure. Use a loop only if you need more than one location.
The service does not need a loop.

### What you can change

| To change this               | Change this value                                   |
|------------------------------|-----------------------------------------------------|
| The location                 | `zip_code`, and `country_code` for the correct site |
| The Amazon site              | `AMAZON_URL`, for the same `country_code`           |
| The apparent location of the client | `PROXIES`                                    |
| A delivery country in place of a zip code | Read the next section              |

Send the cookies to the same site that supplied them. Cookies from `amazon.de`
are not applicable to `amazon.com`.

The proxy server is optional, but it is the primary reason for this service.
Amazon selects content by IP address. A proxy server in the correct country and
these cookies together set the two conditions. Amazon sends a challenge to an
address that makes many requests. Then the procedure in the next section fails,
and the quality of the cookies is not important.

### Delivery to a different country

The procedure is the same, but the endpoint is different. Give a destination
country in place of a zip code:

```python
response = requests.get(
    url="http://127.0.0.1:8000/api/v1/countries/cookies",
    params={"delivery_country_code": "UA", "country_code": "UK"},
)
```

These cookies cause `amazon.co.uk` to show delivery to Ukraine. The control then
shows `Ukraine` and not a zip code. You can use all the countries that Amazon
delivers to.

### If you do not get a location

The value of `location` is `None` for all the pages that are not the site page.
This does not always mean that the cookies are too old. If you make that
assumption, you get incorrect results. Examine the response and find the
applicable condition:

- **A `202` status, or an `x-amzn-waf-action` header.** This is an AWS WAF
  challenge. Amazon refused your client before it read the cookies. Send the
  request again, if possible from a different address.
- **A page of approximately 2 KB that contains `bm-verify`.** This is an Akamai
  page. It contains a `<meta http-equiv="refresh">` element with the address of
  the site page. Obey that refresh one time. Use the same session and the same
  cookies:

  ```python
  from urllib.parse import urljoin

  headers = {"user-agent": BROWSER_UA}
  session = requests.Session()

  page = session.get(url=AMAZON_URL, cookies=cookies, headers=headers, proxies=PROXIES)
  if "bm-verify" in page.text:
      target = re.search(r"""URL=['"]?([^'"]+)""", page.text).group(1)
      page = session.get(
          url=urljoin(AMAZON_URL, target),
          cookies=cookies,
          headers=headers,
          proxies=PROXIES,
      )
  ```

- **A complete site page with an incorrect location.** The cookies are too old.
  Ask the service for new cookies.

The service can also do this examination. Send a `POST` request to
`/api/v1/sessions/check` with `country_code`, `cookies` and an optional
`expected` value. The service replies with the location that it finds and a
result. If a bot challenge prevents the examination, the service replies with a
`409` status and does not make an assumption. The service examines the cookies
from its own address. That address can be different from your address.
