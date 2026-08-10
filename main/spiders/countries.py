from main.spiders.base import AmazonBaseSessionSpider


class AmazonCountrySessionSpider(AmazonBaseSessionSpider):
    """Amazon spider for extracting country delivery cookies."""

    name = "amazon:outside-delivery-session"

    def build_payload(self) -> dict:
        """
        Build the payload that pins delivery to a country outside the storefront.
        """
        if not (delivery_country := self.kwargs.get("delivery_country")):
            raise ValueError("You must specify the outside delivery country")

        return {
            "locationType": "COUNTRY",
            "district": delivery_country.upper(),
            "countryCode": delivery_country.upper(),
            "deviceType": "web",
            "storeContext": "hpc",
            "pageType": "Search",
            "actionSource": "glow",
        }
