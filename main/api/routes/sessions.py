from fastapi import APIRouter

from main.api.schemas.common import Response, SessionCheckRequest
from main.api.services.session_check import AmazonSessionCheckService

router = APIRouter()

service = AmazonSessionCheckService()


@router.post("/check", response_model=Response)
def check_session(data: SessionCheckRequest) -> Response:
    """
    Check whether `cookies` still pin a delivery location on Amazon.

    Takes a body rather than query parameters: cookies are session credentials
    and have no business sitting in a URL, where they end up in logs and proxies.
    """
    return service.check_session(data=data)
