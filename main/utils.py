import shlex
import subprocess
from http.cookies import BaseCookie, SimpleCookie

from furl import furl
from scrapy.http import HtmlResponse


def extract_response_cookies(response: HtmlResponse) -> dict:
    """
    Extract cookies from response object and return it in valid format.
    """
    cookies = {}
    cookie_headers = response.headers.getlist("Set-Cookie", [])
    for cookie_str in cookie_headers:
        cookie: BaseCookie = SimpleCookie()
        cookie.load(cookie_str.decode("utf-8"))
        for key, raw_value in cookie.items():
            if key not in cookies and raw_value.value != "-":
                cookies[key] = raw_value.value
    return cookies


def execute_curl_command(curl_command: str) -> str:
    """
    Make curl request via dedicated process.
    """
    args = shlex.split(curl_command)
    process = subprocess.Popen(
        args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    return stdout.decode("utf-8")


def add_query_param(url: str, name: str, value: str) -> str:
    """
    Add GET query parameter to `url`.
    """
    return furl(url=url).add({name: value}).url


def add_query_params(url: str, params: dict) -> str:
    """
    Add query params based on ``params`` dict.
    """
    for param, value in params.items():
        url = add_query_param(url=url, name=param, value=value)
    return url
