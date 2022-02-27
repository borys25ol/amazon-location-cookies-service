BOT_NAME = "amazon-locations"

SPIDER_MODULES = ["main.spiders"]
NEWSPIDER_MODULE = "main.spiders"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/527  "
    "(KHTML like Gecko Safari/419.3) Arora/0.6 (Change: );;"
)
