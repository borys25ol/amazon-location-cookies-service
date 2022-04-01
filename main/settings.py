BOT_NAME = "amazon-locations"

SPIDER_MODULES = ["main.spiders"]
NEWSPIDER_MODULE = "main.spiders"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/99.0.4844.83 Safari/537.36"
)

HEADERS = {
    "sec-fetch-site": "none",
    "sec-fetch-dest": "document",
    "accept-language": "ru-RU,ru;q=0.9",
    "connection": "close",
    "user-agent": DEFAULT_USER_AGENT,
}
