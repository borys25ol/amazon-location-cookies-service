from main.spiders.base import AmazonBaseSessionSpider


class AmazonLocationSessionSpider(AmazonBaseSessionSpider):
    """Amazon spider for extracting location cookies."""

    name = "amazon:location-delivery-session"

    def build_payload(self) -> dict:
        """
        Build the payload that pins delivery to a zip code.
        """
        if not (zip_code := self.kwargs.get("zip_code")):
            raise ValueError("You must specify a zip code")

        return {
            "locationType": "LOCATION_INPUT",
            "zipCode": zip_code.replace("+", " "),
            "storeContext": "generic",
            "deviceType": "web",
            "pageType": "Gateway",
            "actionSource": "glow",
        }
