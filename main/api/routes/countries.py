from fastapi import APIRouter

from main.api.schemas.common import Response, ScrapingCountryRequest
from main.api.services.sessions import AmazonSessionService

router = APIRouter()

service = AmazonSessionService()


@router.get("/cookies", response_model=Response)
def get_cookies(delivery_country_code: str, country_code: str) -> Response:
    """
    Get Amazon cookies base on `delivery_country_code` and `country_code`.
    """
    data = ScrapingCountryRequest(
        delivery_country_code=delivery_country_code, country_code=country_code
    )
    return service.get_country_cookies(data=data)
