"""Pure checks shared by serializers, services, and model.clean()."""

from apps.common.choices import ContractType


def contract_window_error(contract_type, start, end):
    """Return an error when a contract length does not match its type.

    Yearly contracts must span 364–366 days. Six-month contracts must span
    178–186 days. Those windows cover calendar boundaries and leap years
    without allowing a free-form duration.
    """

    if start is None or end is None or end <= start:
        return 'Contract end date must be after the start date.'
    days = (end - start).days
    if contract_type == ContractType.YEARLY and not 364 <= days <= 366:
        return 'A yearly contract must cover one full year (364 to 366 days).'
    if contract_type == ContractType.SIX_MONTHS and not 178 <= days <= 186:
        return 'A six-month contract must cover six months (178 to 186 days).'
    return ''
