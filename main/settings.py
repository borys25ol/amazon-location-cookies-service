BOT_NAME = "amazon-locations"

SPIDER_MODULES = ["main.spiders"]
NEWSPIDER_MODULE = "main.spiders"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Amazon's Akamai edge fingerprints the TLS handshake, and Scrapy's default
# cipher list is distinctive enough to get non-US storefronts blocked outright:
# amazon.co.uk answers a 4KB block page instead of the storefront, while the same
# request from a plain `requests` client sails through. Offering Chrome's cipher
# suite in Chrome's order is what makes the difference -- the effect is easy to
# miss locally, since it depends on the OpenSSL build underneath.
DOWNLOADER_CLIENT_TLS_CIPHERS = (
    "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:"
    "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:"
    "ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:"
    "ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:"
    "AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA:AES256-SHA"
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/99.0.4844.83 Safari/537.36"
)

# Shared by the spiders and by the API's session check, which talks to Amazon
# directly and should not have to import a spider to learn the storefront URLs.
COUNTRY_BASE_URLS = {
    "US": "https://www.amazon.com",
    "GB": "https://www.amazon.co.uk",
    "UK": "https://www.amazon.co.uk",
    "DE": "https://www.amazon.de",
    "ES": "https://www.amazon.es",
    "IT": "https://www.amazon.it",
    "FR": "https://www.amazon.fr",
}

HEADERS = {
    "sec-fetch-site": "none",
    "sec-fetch-dest": "document",
    "accept-language": "ru-RU,ru;q=0.9",
    "connection": "close",
    "user-agent": DEFAULT_USER_AGENT,
}
