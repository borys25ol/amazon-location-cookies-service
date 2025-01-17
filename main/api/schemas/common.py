import re
from enum import Enum

from pydantic import BaseModel, field_validator


class AmazonCountryCode(str, Enum):
    US = "US"
    UK = "UK"
    GB = "GB"
    DE = "DE"
    ES = "ES"
    IT = "IT"
    FR = "FR"


class SuccessModel(BaseModel):
    success: bool = True


class Response(SuccessModel):
    data: dict | None = {}
    message: str | None
    errors: list | None = []


class ScrapingLocationRequest(BaseModel):
    country_code: AmazonCountryCode
    zip_code: str

    class Config:
        use_enum_values = True

    @field_validator("zip_code")
    def valid_zip_code(cls, value: str) -> str:
        if not re.match(
            "^[0-9]{5}(?:-[0-9]{4})?|[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}$", value
        ):
            raise ValueError("- Invalid zip code ")
        return value


class ScrapingCountryRequest(BaseModel):
    country_code: AmazonCountryCode
    delivery_country_code: str

    class Config:
        use_enum_values = True
