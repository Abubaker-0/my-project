"""HTTP routers. They parse input, call a service, and return a schema."""

from fastapi import APIRouter

from app.routers import (
    academics,
    attendance,
    audit,
    auth,
    billing,
    branches,
    dashboard,
    enrollments,
    health,
    inquiries,
    organization,
    roles,
    students,
    timetable,
    users,
)
from app.schemas.common import ErrorBody

api_router = APIRouter(
    responses={401: {"model": ErrorBody}, 403: {"model": ErrorBody}, 422: {"model": ErrorBody}}
)
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(branches.router)
api_router.include_router(organization.router)
api_router.include_router(academics.router)
api_router.include_router(students.router)
api_router.include_router(inquiries.router)
api_router.include_router(enrollments.router)
api_router.include_router(timetable.router)
api_router.include_router(attendance.router)
api_router.include_router(billing.plans)
api_router.include_router(billing.invoices)
api_router.include_router(billing.payments)
api_router.include_router(dashboard.router)
api_router.include_router(audit.router)
