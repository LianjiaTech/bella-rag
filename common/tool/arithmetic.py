from decimal import Decimal


def fadd(f1, f2):
    return float(Decimal(str(f1)) + Decimal(str(f2)))
