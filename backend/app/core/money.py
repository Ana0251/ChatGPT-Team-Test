"""H-08: canonical IRR amounts with lossless Decimal-only arithmetic.

Wire format (OpenAPI 1.0.0-rc.4):
    Rial       ^(0|[1-9][0-9]{0,19})$
    SignedRial ^(0|-?[1-9][0-9]{0,19})$   (reporting only)

No JSON numbers, float conversion, currency conversion, implicit rounding, or
database persistence belong in this module. The signed reporting helpers are
deliberately separate from nonnegative journal-input helpers.
"""
from __future__ import annotations

from decimal import Decimal, Inexact, Rounded, localcontext
import re
from typing import Iterable

MAX_RIAL_DIGITS = 20
MAX_RIAL = Decimal("99999999999999999999")

_RIAL_WIRE = re.compile(r"(?:0|[1-9][0-9]{0,19})", flags=re.ASCII)
_SIGNED_WIRE = re.compile(r"(?:0|-?[1-9][0-9]{0,19})", flags=re.ASCII)


class RialValueError(ValueError):
    """The amount is not an exact canonical 20-digit IRR integer."""


def parse_rial(value: str) -> Decimal:
    """Decode an OpenAPI Rial JSON *string*; reject all other Python types."""
    if type(value) is not str or _RIAL_WIRE.fullmatch(value) is None:
        raise RialValueError("Rial must be a canonical nonnegative ASCII JSON string")
    return Decimal(value)


def _decimal_string(value: Decimal, *, signed: bool) -> str:
    """Serialize an internal exact integral Decimal; disallow scale/coercion."""
    if type(value) is not Decimal or not value.is_finite():
        raise RialValueError("Expected a finite Decimal, never a JSON number or float")
    if value.as_tuple().exponent != 0 or (value.is_zero() and value.is_signed()):
        raise RialValueError("Decimal must have canonical integer scale and no signed zero")
    if value.copy_abs() > MAX_RIAL or (not signed and value.is_signed()):
        raise RialValueError("Rial amount is negative or exceeds the 20-digit IRR limit")
    result = format(value, "f")
    pattern = _SIGNED_WIRE if signed else _RIAL_WIRE
    if pattern.fullmatch(result) is None:
        raise RialValueError("Decimal is not a canonical IRR amount")
    return result


def format_rial(value: Decimal) -> str:
    """Encode a nonnegative Decimal as the canonical JSON Rial string."""
    return _decimal_string(value, signed=False)


def add_rials(left: Decimal, right: Decimal) -> Decimal:
    """Add two validated IRR amounts exactly, failing on 20-digit overflow.

    Decimal uses the active context for arithmetic. Override its precision
    locally and trap any rounding, independent of the calling context.
    """
    format_rial(left)
    format_rial(right)
    with localcontext() as context:
        context.prec = MAX_RIAL_DIGITS + 1
        context.Emax = 999999
        context.Emin = -999999
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        total = left + right
    format_rial(total)  # Detect overflow before returning an unrepresentable sum.
    return total


def sum_rials(amounts: Iterable[Decimal]) -> Decimal:
    """Accumulate Decimal IRR amounts exactly, checking each intermediate sum."""
    total = Decimal("0")
    for amount in amounts:
        total = add_rials(total, amount)
    return total


def parse_signed_rial(value: str) -> Decimal:
    """Decode report-only SignedRial; never use for journal Rial input."""
    if type(value) is not str or _SIGNED_WIRE.fullmatch(value) is None:
        raise RialValueError("SignedRial must be a canonical ASCII JSON string")
    return Decimal(value)


def format_signed_rial(value: Decimal) -> str:
    """Encode report-only SignedRial; negative amounts stay forbidden to Rial."""
    return _decimal_string(value, signed=True)
