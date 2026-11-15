"""HTTP routers. They parse input, call a service, and return a schema."""

from fastapi import APIRouter

from app.routers import audit, auth, branches, health, roles, users
from app.schemas.common import ErrorBody

api_router = APIRouter(
    responses={401: {"model": ErrorBody}, 403: {"model": ErrorBody}, 422: {"model": ErrorBody}}
)
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(branches.router)
api_router.include_router(audit.router)
