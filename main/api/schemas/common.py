from typing import Optional

from pydantic import BaseModel


class SuccessModel(BaseModel):
    success: bool


class Response(SuccessModel):
    data: Optional[dict] = {}
    message: Optional[str]
    errors: Optional[list] = []
