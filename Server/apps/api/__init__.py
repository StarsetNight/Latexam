from fastapi import APIRouter

from .login import login_api
from .exam import exam_api

api = APIRouter(prefix="/api/v1")
api.include_router(login_api)
api.include_router(exam_api)