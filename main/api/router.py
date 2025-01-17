from fastapi import APIRouter

from main.api.routes import countries, locations

router = APIRouter()

router.include_router(router=locations.router, prefix="/locations", tags=["Locations"])
router.include_router(router=countries.router, prefix="/countries", tags=["Countries"])
