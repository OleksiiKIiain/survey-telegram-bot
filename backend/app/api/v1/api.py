from fastapi import APIRouter, Depends

from app.api.deps import get_bot_access

from app.api.v1.endpoints import analytics, auth, export, public, respondents, responses, surveys, translation

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(surveys.router, prefix="/surveys", tags=["surveys"])
api_router.include_router(respondents.router, prefix="/respondents", tags=["respondents"])
api_router.include_router(responses.router, prefix="/responses", tags=["responses"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(public.router, prefix="/public", tags=["public"], dependencies=[Depends(get_bot_access)])
api_router.include_router(translation.router, prefix="/translate", tags=["translate"])
