"""Turn an actor plus the optional branch header into a repository scope."""

from __future__ import annotations

from app.core.exceptions import AppException
from app.domain.actor import Actor, BranchScope


def scope_for(actor: Actor, branch_id: int | None) -> BranchScope:
    """Resolve the branch filter for this request.

    A selected branch is an intersection, never an expansion. Callers outside
    their grants receive 403 rather than an empty list so the mistake is visible.
    """
    if branch_id is not None:
        if not actor.all_branches and branch_id not in actor.branch_ids:
            raise AppException(403, "FORBIDDEN", "That branch is outside your access")
        return BranchScope(unrestricted=False, branch_ids=(branch_id,))
    if actor.all_branches:
        return BranchScope(unrestricted=True, branch_ids=())
    return BranchScope(unrestricted=False, branch_ids=tuple(sorted(actor.branch_ids)))
