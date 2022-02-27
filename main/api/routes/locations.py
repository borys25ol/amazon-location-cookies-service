from fastapi import APIRouter

from main.api.schemas.common import Response
from main.api.services.locations import AmazonLocationService

router = APIRouter()

service = AmazonLocationService()


@router.get("/cookies", response_model=Response)
def get_cookies(zip_code: str, country_code: str) -> Response:
    """
    Get Amazon cookies base on `zip_code` and `country_code`.
    """
    return service.get_cookies(zip_code=zip_code, country_code=country_code)
