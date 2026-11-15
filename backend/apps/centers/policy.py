"""One resolver for organization and center policy.

self enrollment is allowed only when the global ceiling and the center choice
are both on. Approval is required when either level requires it. The installment
limit is the smallest of the product cap, the global cap, and the center cap.
Exports stay on the permission catalog so they are not configured twice.
"""

from apps.common.choices import Role
from apps.common.permissions_catalog import role_has_permission

PRODUCT_INSTALLMENT_LIMIT = 3
PRODUCT_CURRENCY = 'AFN'


def _rule(*, configured, inherited, effective, source, effect):
    return {
        'configured': configured,
        'inherited': inherited,
        'effective': effective,
        'source': source,
        'effect': effect,
    }


def resolve_policy(center):
    """Effective policy for one center. Historical invoices are not inputs."""

    from apps.centers.models import GlobalSettings

    global_settings = GlobalSettings.load()
    local = center.settings
    self_enrollment = bool(global_settings.allow_self_enrollment and local.allow_self_enrollment)
    approval = bool(global_settings.require_enrollment_approval or local.require_enrollment_approval)
    installments = max(1, min(
        PRODUCT_INSTALLMENT_LIMIT,
        int(global_settings.max_installments),
        int(local.max_installments),
    ))
    waitlist = bool(global_settings.allow_waitlist and local.allow_waitlist)
    student_refunds = bool(
        global_settings.allow_student_refund_requests and local.allow_student_refund_requests
    )
    finance_refunds = bool(
        global_settings.allow_finance_refund_requests and local.allow_finance_refund_requests
    )
    later = 'Applies to later operations. Issued invoices, installment plans, and frozen reports stay as they were.'
    return {
        'currency': _rule(
            configured=PRODUCT_CURRENCY,
            inherited=PRODUCT_CURRENCY,
            effective=PRODUCT_CURRENCY,
            source='product',
            effect='Every amount is AFN. The label cannot rename existing amounts.',
        ),
        'self_enrollment': _rule(
            configured=local.allow_self_enrollment,
            inherited=global_settings.allow_self_enrollment,
            effective=self_enrollment,
            source='global_allows AND center_enables',
            effect=later,
        ),
        'approval_required': _rule(
            configured=local.require_enrollment_approval,
            inherited=global_settings.require_enrollment_approval,
            effective=approval,
            source='global_requires OR center_requires',
            effect=later,
        ),
        'installment_limit': _rule(
            configured=local.max_installments,
            inherited=min(PRODUCT_INSTALLMENT_LIMIT, int(global_settings.max_installments)),
            effective=installments,
            source='min(product_limit, global_limit, center_limit)',
            effect='New plans use this cap. A lower cap does not rewrite an existing plan.',
        ),
        'waitlist': _rule(
            configured=local.allow_waitlist,
            inherited=global_settings.allow_waitlist,
            effective=waitlist,
            source='global_allows AND center_enables',
            effect='Closing the waitlist does not delete people who are already waiting.',
        ),
        'student_refund_requests': _rule(
            configured=local.allow_student_refund_requests,
            inherited=global_settings.allow_student_refund_requests,
            effective=student_refunds,
            source='global_allows AND center_enables',
            effect='Pending refund requests are not cancelled by a later policy change.',
        ),
        'finance_refund_requests': _rule(
            configured=local.allow_finance_refund_requests,
            inherited=global_settings.allow_finance_refund_requests,
            effective=finance_refunds,
            source='global_allows AND center_enables',
            effect='Pending refund requests are not cancelled by a later policy change.',
        ),
        'exports': {
            'configured': 'permission exports.invoices',
            'inherited': 'role ceiling',
            'effective': {
                role: role_has_permission(role, 'exports.invoices', center)
                for role in (Role.SUPER_ADMIN, Role.CENTER_MANAGER, Role.FINANCE_MANAGER)
            },
            'source': 'permission catalog',
            'effect': 'Export access changes on the next request and does not alter invoices.',
        },
        'defaults': {
            'self_enrollment': global_settings.default_allow_self_enrollment,
        },
    }


def center_payload(settings_obj):
    return {
        'allow_self_enrollment': settings_obj.allow_self_enrollment,
        'require_enrollment_approval': settings_obj.require_enrollment_approval,
        'allow_waitlist': settings_obj.allow_waitlist,
        'allow_student_refund_requests': settings_obj.allow_student_refund_requests,
        'allow_finance_refund_requests': settings_obj.allow_finance_refund_requests,
        'max_installments': settings_obj.max_installments,
    }


def global_payload(settings_obj):
    return {
        'organization_name': settings_obj.organization_name,
        'currency': PRODUCT_CURRENCY,
        'default_allow_self_enrollment': settings_obj.default_allow_self_enrollment,
        'allow_self_enrollment': settings_obj.allow_self_enrollment,
        'require_enrollment_approval': settings_obj.require_enrollment_approval,
        'allow_waitlist': settings_obj.allow_waitlist,
        'allow_student_refund_requests': settings_obj.allow_student_refund_requests,
        'allow_finance_refund_requests': settings_obj.allow_finance_refund_requests,
        'max_installments': settings_obj.max_installments,
    }
