from fastapi import APIRouter

from main.api.schemas.common import Response, ScrapingLocationRequest
from main.api.services.sessions import AmazonSessionService

router = APIRouter()

service = AmazonSessionService()


@router.get("/cookies", response_model=Response)
def get_cookies(zip_code: str, country_code: str) -> Response:
    """
    Get Amazon cookies base on `zip_code` and `country_code`.
    """
    data = ScrapingLocationRequest(zip_code=zip_code, country_code=country_code)
    return service.get_location_cookies(data=data)
