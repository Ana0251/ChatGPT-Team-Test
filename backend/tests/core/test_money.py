"""H-08: no binary floats, implicit rounding, signed-journal mixing or lossy JSON."""
from __future__ import annotations

from decimal import Decimal, Inexact, Rounded, localcontext
import json
from pathlib import Path
import re

import pytest
import yaml

from app.core.money import (
    MAX_RIAL, RialValueError, add_rials, format_rial, format_signed_rial,
    parse_rial, parse_signed_rial, sum_rials,
)

MAX_TEXT = "99999999999999999999"


def test_approved_openapi_rc4_rial_and_signed_patterns():
    """Use the actual checked-in contract rather than an invented allowed enum."""
    contract = Path(__file__).resolve().parents[3] / "docs" / "contracts" / "openapi.yaml"
    data = yaml.safe_load(contract.read_text(encoding="utf-8"))
    assert data["info"]["version"] == "1.0.0-rc.4"
    assert data["components"]["schemas"]["Rial"]["type"] == "string"
    assert data["components"]["schemas"]["Rial"]["pattern"] == r"^(0|[1-9][0-9]{0,19})$"
    assert data["components"]["schemas"]["SignedRial"]["type"] == "string"
    assert data["components"]["schemas"]["SignedRial"]["pattern"] == r"^(0|-?[1-9][0-9]{0,19})$"


@pytest.mark.parametrize("wire", [
    "0", "1", "9", "10", "123456789", "10000000000000000000",
    "99999999999999999998", MAX_TEXT,
])
def test_rial_canonical_values_roundtrip_and_json_ascii(wire):
    parsed = parse_rial(wire)
    assert type(parsed) is Decimal
    assert format_rial(parsed) == wire
    encoded = json.dumps({"amount": format_rial(parsed)})
    assert json.loads(encoded) == {"amount": wire}
    assert isinstance(json.loads(encoded)["amount"], str)
    assert re.fullmatch(r"^(0|[1-9][0-9]{0,19})$", wire, flags=re.ASCII)


@pytest.mark.parametrize("bad", [
    "", " ", " 1", "1 ", "\n1", "1\n", "\t0", "+1", "-1", "-0", "--1",
    "00", "01", "0001", "010", "00000000000000000000",
    "1.0", "0.0", "1.5", ".1", "1.", "1e3", "1E+3", "1E-3",
    "NaN", "nan", "sNaN", "Infinity", "-Infinity", "Inf",
    "1,000", "1_000", "1 IRR", "IRR1", "0x10",
    "100000000000000000000", "9"*21, "1"*100,
    "۱", "۱۲۳", "١٢٣", "１", "𝟙", "0\u200b", "\u00a01", "٢0",
    "\u0660", "1\x00", "😀",
])
def test_reject_invalid_noncanonical_wire_values(bad):
    with pytest.raises(RialValueError):
        parse_rial(bad)


@pytest.mark.parametrize("bad", [
    0, 1, 10, -1, True, False, None, 0.0, 1.0, -1.0, 1.5,
    float("nan"), float("inf"), float("-inf"), [], {}, ["1"],
    Decimal("0"), Decimal("1"), Decimal("NaN"),
])
def test_rial_json_input_rejects_non_string_types(bad):
    with pytest.raises(RialValueError):
        parse_rial(bad)


@pytest.mark.parametrize("wire_json", [
    "0", "1", "1.0", "-1", "true", "false", "null",
    "1e3", "1E+3", "NaN", "Infinity", "-Infinity", '["1"]', '{"amount":"1"}',
])
def test_actual_json_numeric_and_non_string_values_rejected(wire_json):
    incoming = json.loads(wire_json)
    assert type(incoming) is not str
    with pytest.raises(RialValueError):
        parse_rial(incoming)


@pytest.mark.parametrize("bad", [
    0, 1, False, True, 1.0, 0.0, float("nan"), None,
    Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"),
    Decimal("-Infinity"), Decimal("-1"), Decimal("-0"),
    Decimal("1.0"), Decimal("0.0"), Decimal("1.00"),
    Decimal("1E+1"), Decimal("1E-1"), Decimal("0E+4"), Decimal("-0.0"),
    Decimal("100000000000000000000"),
])
def test_internal_decimal_must_be_finite_integral_canonical_and_bounded(bad):
    with pytest.raises(RialValueError):
        format_rial(bad)


def test_decimal_boundaries_and_exact_addition():
    assert MAX_RIAL == Decimal(MAX_TEXT)
    assert add_rials(parse_rial("0"), parse_rial("0")) == Decimal("0")
    assert add_rials(parse_rial("1"), parse_rial("1")) == Decimal("2")
    assert format_rial(add_rials(parse_rial("99999999999999999998"), parse_rial("1"))) == MAX_TEXT
    assert format_rial(add_rials(parse_rial("12345678901234567890"), parse_rial("1"))) == "12345678901234567891"
    assert format_rial(sum_rials([parse_rial("9"), parse_rial("0"), parse_rial("10")])) == "19"
    assert format_rial(sum_rials([])) == "0"


@pytest.mark.parametrize("left,right", [
    (MAX_TEXT, "1"),
    (MAX_TEXT, MAX_TEXT),
    ("50000000000000000000", "50000000000000000000"),
])
def test_exact_sum_detects_twenty_digit_overflow(left, right):
    with pytest.raises(RialValueError):
        add_rials(parse_rial(left), parse_rial(right))
    with pytest.raises(RialValueError):
        sum_rials([parse_rial(left), parse_rial(right)])


def test_multi_item_aggregation_and_intermediate_overflow():
    pieces = (parse_rial("9876543210987654321") for _ in range(10))
    assert format_rial(sum_rials(pieces)) == "98765432109876543210"
    assert format_rial(sum_rials(parse_rial("1") for _ in range(1000))) == "1000"
    with pytest.raises(RialValueError):
        sum_rials([parse_rial(MAX_TEXT), parse_rial("1"), parse_rial("0")])


def test_arithmetic_never_implicitly_rounds_under_low_caller_precision():
    left = parse_rial("12345678901234567890")
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.traps[Inexact] = True
        ctx.traps[Rounded] = True
        value = add_rials(left, parse_rial("9"))
        assert format_rial(value) == "12345678901234567899"
        assert format_rial(sum_rials((left, parse_rial("9")))) == "12345678901234567899"
        with pytest.raises(RialValueError):
            add_rials(parse_rial(MAX_TEXT), parse_rial("1"))


def test_inputs_to_addition_and_aggregation_are_strictly_decimal():
    for bad in ("1", 1, 1.0, True, Decimal("1.0"), Decimal("-1")):
        with pytest.raises(RialValueError):
            add_rials(parse_rial("0"), bad)
        with pytest.raises(RialValueError):
            sum_rials([parse_rial("0"), bad])


@pytest.mark.parametrize("wire", [
    "0", "1", "50", MAX_TEXT, "-1", "-50", "-" + MAX_TEXT,
])
def test_signed_report_roundtrip_separate_from_journal(wire):
    amount = parse_signed_rial(wire)
    assert format_signed_rial(amount) == wire
    if wire.startswith("-"):
        with pytest.raises(RialValueError):
            parse_rial(wire)
        with pytest.raises(RialValueError):
            format_rial(amount)
        with pytest.raises(RialValueError):
            add_rials(amount, Decimal("1"))


@pytest.mark.parametrize("wire", [
    "-0", "-00", "-01", "+1", "+0", "--1", "0.0", "-1.0",
    "-1e2", "01", "١", "-۱", "100000000000000000000",
    "-100000000000000000000", "", " 0", "1 ",
])
def test_signed_report_rejects_noncanonical_wire(wire):
    with pytest.raises(RialValueError):
        parse_signed_rial(wire)


@pytest.mark.parametrize("value", [
    Decimal("-0"), Decimal("-0.0"), Decimal("-1.00"),
    Decimal("1E+2"), Decimal("-1E+2"), Decimal("-Infinity"),
    Decimal("NaN"), Decimal("-100000000000000000000"),
    0, 1, 1.0, True, "1",
])
def test_signed_report_serializer_rejects_invalid_internal_values(value):
    with pytest.raises(RialValueError):
        format_signed_rial(value)
