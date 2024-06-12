Amazon Location Cookies
====================

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Pre-commit: enabled](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=flat)](https://github.com/pre-commit/pre-commit)

## Description

This project can be used to get Amazon location cookies from specific Amazon `Zip-Code` and country-specific domains like `.de`, `.co.uk`, etc.

It will be very helpful when you are using random geolocation proxies for scraping data from Amazon because Amazon returns content based on user IP.

Tested location at the moment:
- US (30322)
- ES (28010)
- UK (E1 6AN)
- DE (80686)
- IT (20162)
- FR (75001)

Developing
-----------

Install pre-commit hooks to ensure code quality checks and style checks

```shell
make install_hooks
```

Then see `Configuration` section

Configuration
--------------

Replace `.env.example` with real `.env`, changing placeholders

```
SECRET_KEY=changeme
SCRAPYRT_URL=http://scrapyrt:7800/crawl.json
```

Local install
-------------

Setup and activate a python3 virtualenv via your preferred method. e.g. and install production requirements:

```shell
make ve
```

For remove virtualenv:

```shell
make clean
```

Local run
-------------
Run spider locally:

```shell
scrapy crawl amazon:location-session -a country=US -a zip_code=30322
```

Run using local ScrapyRT service:

```shell
scrapyrt --ip 0.0.0.0 --port 7800

curl -X 'GET' \
 'http://0.0.0.0:7800/crawl.json?start_requests=1&spider_name=amazon:location-session&crawl_args={"zip_code":"30332","country":"US"}'
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
#### Run in Docker:

Run docker containers:

```shell
make docker_up
```

Run using dockerized API service:

```shell
curl -X 'GET' \
  'http://127.0.0.1:8000/api/v1/cookies?zip_code=30322&country_code=US' \
  -H 'accept: application/json'
```

Docker API response example:

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

#### Check extracted amazon location cookies from python script:
```python
import re
from time import sleep
from typing import Dict

import requests

API_URL = "http://127.0.0.1:8000/api/v1/cookies?zip_code={zip_code}&country_code={country_code}"

HEADERS = {"user-agent": "user-agent"}

COUNTRY_CONFIG = {
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
    for country in COUNTRY_CONFIG:
        print("Check cookies for country: ", country)
        amazon_url = COUNTRY_CONFIG[country]["amazon_url"]
        zip_code = COUNTRY_CONFIG[country]["zip_code"]

        # Extract cookies via Amazon Location Service.
        cookies = get_location_cookies(country=country, zip_code=zip_code)
        print("Got Amazon cookies: ", cookies)

        # Check response using location cookies.
        response = check_location_cookies(amazon_url=amazon_url, cookies=cookies)
        print("Amazon response: ", response)
        sleep(5)

```
