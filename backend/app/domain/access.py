"""Row ownership beyond the branch filter.

Branch scope answers "which campus?". This module answers "which rows inside
that campus?". A campus role sees the whole branch. A teacher is limited to
assigned batches, a parent to linked children, and a student login to itself.
When one person holds more than one of those roles, the visible set is the
union.
"""

from __future__ import annotations

from app.domain.actor import Actor

BROAD_ROLES = frozenset({"branch_admin", "academic_coordinator", "receptionist", "accountant"})


def sees_whole_branch(actor: Actor) -> bool:
    """Return True when the caller is not limited to owned rows."""
    return actor.is_super_admin or bool(actor.role_names & BROAD_ROLES)


def limits_to_assigned_batches(actor: Actor) -> bool:
    """Return True when this teacher must not see other teachers' batches."""
    return "teacher" in actor.role_names and not sees_whole_branch(actor)


def limits_to_linked_children(actor: Actor) -> bool:
    """Return True when this parent must not see other families."""
    return "parent" in actor.role_names and not sees_whole_branch(actor)


def limits_to_self(actor: Actor) -> bool:
    """Return True when this student login must not see other students."""
    return "student" in actor.role_names and not sees_whole_branch(actor)
