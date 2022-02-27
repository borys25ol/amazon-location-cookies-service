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

Developing
-----------

Install pre-commit hooks to ensure code quality checks and style checks


    $ make install_hooks

Then see `Configuration` section

You can also use these commands during dev process:

- to run mypy checks


      $ make types


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


    $ make ve

For remove virtualenv:


    $ make clean


Local run
-------------
Run spider locally:

    
    $  scrapy crawl amazon:location-session -a country=US -a zip_code=30322


Run using local ScrapyRT service:

    $  scrapyrt --ip 0.0.0.0 --port 7800
    $  curl http://0.0.0.0:7800/crawl.json?start_requests=1&spider_name=amazon:location-session&crawl_args={"zip_code":"30332","country":"US"}


Run docker containers:

    $  make docker_up


Check extracted amazon location cookies from python script:
```python
import re

import requests


def main():
    # E1 6AN - London postal code
    api_url = "http://127.0.0.1:8000/api/v1/cookies?zip_code=E1+6AN&country_code=UK"
    amazon_url = "https://amazon.co.uk/"
    default_headers = {"user-agent": "user-agent"}

    json_data = requests.get(url=api_url).json()
    cookies = json_data["data"]["cookies"]

    amazon_response = requests.get(
        url=amazon_url, cookies=cookies, headers=default_headers
    )
    location = re.search(r'(?s)glow-ingress-line2">(.+?)<', amazon_response.text)
    print(location.group(1).strip())


if __name__ == "__main__":
    main()


```
