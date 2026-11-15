"""Role and permission routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.core.deps import DbSession, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor
from app.models.rbac import Role
from app.schemas.common import Page
from app.schemas.role import PermissionPublic, RoleCreate, RolePermissionsUpdate, RolePublic
from app.services.role_service import RoleService

router = APIRouter(tags=["roles"])

_SORT = {"name": Role.name, "label": Role.label, "created_at": Role.created_at}


@router.get("/permissions", response_model=list[PermissionPublic])
def list_permissions(
    db: DbSession,
    actor: Actor = Depends(require_permission("permissions:read")),
) -> list[PermissionPublic]:
    """Return the permission catalog."""
    del actor
    return RoleService(db).list_permissions()


@router.get("/roles", response_model=Page[RolePublic])
def list_roles(
    db: DbSession,
    actor: Actor = Depends(require_permission("roles:read")),
    page=Depends(get_page_params),
) -> Page[RolePublic]:
    """List roles."""
    del actor
    return RoleService(db).list_roles(
        q=page.q,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _SORT, "name"),
    )


@router.post("/roles", response_model=RolePublic, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("roles:create")),
) -> RolePublic:
    """Create a custom role."""
    return RoleService(db).create_role(actor, payload)


@router.put("/roles/{role_id}/permissions", response_model=RolePublic)
def set_permissions(
    role_id: int,
    payload: RolePermissionsUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("permissions:assign")),
) -> RolePublic:
    """Replace the permissions on a role. The change is written to the audit log."""
    return RoleService(db).set_permissions(actor, role_id, payload.permission_ids)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("roles:delete")),
) -> Response:
    """Soft-delete a custom role that nobody holds."""
    RoleService(db).delete_role(actor, role_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
