"""Home-screen figures for finance and today's classes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.domain.actor import Actor, BranchScope
from app.schemas.operations import FinanceDashboard, TodayDashboard
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/finance", response_model=FinanceDashboard)
def finance(
    db: DbSession,
    actor: Actor = Depends(require_permission("reports:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> FinanceDashboard:
    """Outstanding invoices, overdue money, and what was collected this month."""
    return DashboardService(db).finance(scope)


@router.get("/today", response_model=TodayDashboard)
def today(
    db: DbSession,
    actor: Actor = Depends(require_permission("timetable:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> TodayDashboard:
    """Sessions scheduled for today. Teachers see only their own batches."""
    return DashboardService(db).today(actor, scope)
