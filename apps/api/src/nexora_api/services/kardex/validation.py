"""Central movement, barcode and monetary validation rules."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from nexora_api.core.exceptions import DataStudioError

INBOUND_TYPES = {
    "OPENING_BALANCE",
    "PURCHASE_IN",
    "PRODUCTION_IN",
    "CUSTOMER_RETURN_IN",
    "TRANSFER_IN",
    "POSITIVE_ADJUSTMENT",
}
OUTBOUND_TYPES = {
    "SALE_OUT",
    "PRODUCTION_CONSUMPTION_OUT",
    "SUPPLIER_RETURN_OUT",
    "TRANSFER_OUT",
    "NEGATIVE_ADJUSTMENT",
}
MONEY_QUANT = Decimal("0.000001")
ZERO = Decimal("0.000000")


def quantize(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def movement_direction(movement_type: str) -> str:
    if movement_type in INBOUND_TYPES:
        return "in"
    if movement_type in OUTBOUND_TYPES:
        return "out"
    raise DataStudioError("kardex_invalid_movement_type", "El tipo de movimiento no es válido.")


def validate_barcode(value: str | None, barcode_type: str | None) -> None:
    if not value:
        return
    if barcode_type in {"EAN13", "EAN8", "UPC_A"}:
        lengths = {"EAN13": 13, "EAN8": 8, "UPC_A": 12}
        if not value.isdigit() or len(value) != lengths[barcode_type]:
            raise DataStudioError(
                "kardex_invalid_barcode", "El código no coincide con el formato seleccionado."
            )
        digits = [int(character) for character in value]
        payload, check = digits[:-1], digits[-1]
        reversed_payload = list(reversed(payload))
        total = sum(
            number * (3 if index % 2 == 0 else 1)
            for index, number in enumerate(reversed_payload)
        )
        if (10 - total % 10) % 10 != check:
            raise DataStudioError(
                "kardex_invalid_barcode", "El dígito de control del código no es válido."
            )


def validate_bounds(minimum: Decimal | None, maximum: Decimal | None) -> None:
    if minimum is not None and maximum is not None and minimum > maximum:
        raise DataStudioError(
            "kardex_invalid_stock_limits", "El stock mínimo no puede superar al máximo."
        )
