"""Money helpers. Amounts are decimal afghanis with no exchange conversion."""

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal('0.01')


def money(value):
    """Quantize a numeric value to two decimal places."""

    if value is None:
        value = 0
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def money_str(value):
    """Serialize a money value as a fixed two-decimal string."""

    return f'{money(value):.2f}'


def split_amount(total, parts):
    """Split a total into `parts` cents-safe shares. The last share absorbs rounding."""

    if parts < 1:
        raise ValueError('Installment count must be at least 1.')
    total = money(total)
    base = money(total / Decimal(parts))
    shares = [base for _ in range(parts)]
    shares[-1] = money(total - base * (parts - 1))
    return shares
