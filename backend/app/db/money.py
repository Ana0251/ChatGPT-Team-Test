"""Lossless, SQLite TEXT-backed IRR amount adapter for future financial tables.

SQLite NUMERIC affinity can round large amounts. This type intentionally stores
canonical whole-rial strings and exposes Decimal to application code. It does not
create accounting tables or claim PostgreSQL NUMERIC(20,0) equivalence.
"""

from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy.types import Text, TypeDecorator

_CANONICAL_RIAL = re.compile(r"(?:0|[1-9][0-9]{0,19})\Z")


class ExactRial(TypeDecorator[Decimal]):
    """Nonnegative 0..(10^20 - 1) IRR persisted as canonical SQLite TEXT."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: object, dialect: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, bool) or isinstance(value, float):
            raise ValueError("Boolean and float money values are forbidden")
        if isinstance(value, int):
            canonical = str(value)
        elif isinstance(value, Decimal):
            if not value.is_finite() or value != value.to_integral_value():
                raise ValueError("IRR amounts must be finite whole-rial values")
            # Preserve input notation for validation: Decimal("1E+3") is not
            # canonical even though its mathematical value is the integer 1000.
            # Explicit decimal-string/integer input is required; no normalization.
            canonical = str(value)
        elif isinstance(value, str):
            canonical = value
        else:
            raise TypeError("Expected int, Decimal, or canonical decimal string")

        if not _CANONICAL_RIAL.fullmatch(canonical):
            raise ValueError("IRR must be a nonnegative canonical integer string of at most 20 digits")
        return canonical

    def process_result_value(self, value: object, dialect: object) -> Decimal | None:
        if value is None:
            return None
        if not isinstance(value, str) or not _CANONICAL_RIAL.fullmatch(value):
            raise ValueError("Noncanonical IRR amount encountered in database")
        return Decimal(value)
