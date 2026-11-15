"""Mirror each business role into a Django auth group.

API authorization uses `user.role` plus center checks, because Django model
permissions cannot express "super admin may view courses but must not create
them" or center isolation. Groups still exist so the Django admin and
`user.groups` match the role matrix.
"""

from django.db.utils import OperationalError, ProgrammingError

from apps.common.choices import ROLE_GROUP

ROLE_PERMISSIONS = {
    'Super Admin': None,  # all permissions; API write rules still apply
    'Center Manager': [
        'view_user', 'add_user', 'change_user',
        'view_center', 'change_center',
        'view_course', 'add_course', 'change_course',
        'view_courseclass', 'add_courseclass', 'change_courseclass',
        'view_classschedule', 'add_classschedule', 'change_classschedule', 'delete_classschedule',
        'view_classroom', 'add_classroom', 'change_classroom',
        'view_enrollment', 'add_enrollment', 'change_enrollment',
        'view_attendance', 'change_attendance',
        'view_attendancerecord', 'change_attendancerecord',
        'view_invoice', 'view_payment', 'view_installment', 'view_scholarship',
        'view_refund', 'change_refund',
        'view_contract', 'add_contract', 'change_contract',
        'view_financialreport', 'change_financialreport',
    ],
    'Finance Manager': [
        'view_user', 'view_invoice', 'view_enrollment',
        'add_payment', 'view_payment',
        'add_installment', 'view_installment', 'change_installment',
        'add_scholarship', 'view_scholarship', 'change_scholarship',
        'add_refund', 'view_refund',
        'add_financialreport', 'view_financialreport', 'change_financialreport',
        'view_contract',
    ],
    'Teacher': [
        'view_course', 'view_courseclass', 'view_classschedule',
        'add_attendance', 'view_attendance',
        'add_attendancerecord', 'view_attendancerecord',
        'view_enrollment', 'view_contract',
    ],
    'Student': [
        'view_course', 'view_courseclass', 'view_classschedule',
        'view_enrollment', 'add_enrollment',
        'view_invoice', 'view_payment', 'view_installment', 'view_scholarship',
        'add_refund', 'view_refund', 'view_attendancerecord',
    ],
}


def sync_role_group(user):
    """Put the user in exactly one role group. Safe to call on every save."""

    from django.contrib.auth.models import Group

    name = ROLE_GROUP.get(user.role)
    if not name:
        return
    try:
        group, _created = Group.objects.get_or_create(name=name)
    except (OperationalError, ProgrammingError):
        return
    user.groups.set([group])


def assign_role_permissions(*args, **kwargs):
    """Attach model permissions to role groups once the permission tables exist."""

    from django.contrib.auth.models import Group, Permission

    try:
        if not Permission.objects.exists():
            return
    except (OperationalError, ProgrammingError):
        return
    for name in ROLE_GROUP.values():
        Group.objects.get_or_create(name=name)
    for group_name, codenames in ROLE_PERMISSIONS.items():
        group = Group.objects.get(name=group_name)
        if codenames is None:
            group.permissions.set(Permission.objects.all())
            continue
        perms = list(Permission.objects.filter(codename__in=codenames))
        if perms:
            group.permissions.add(*perms)
