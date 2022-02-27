from fastapi import APIRouter

from main.api.routes import locations

router = APIRouter()

router.include_router(router=locations.router, tags=["Locations"])
