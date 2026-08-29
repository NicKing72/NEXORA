"""Canonical roles and upload constraints shared by Data Studio services."""

CANONICAL_ROLES = (
    "date",
    "demand",
    "product",
    "price",
    "stock",
    "promotion",
    "location",
    "category",
    "cost",
    "lead_time",
    "channel",
    "supplier",
)
REQUIRED_ROLES = ("date", "demand")
RECOMMENDED_ROLES = ("product",)
OPTIONAL_ROLES = tuple(
    role for role in CANONICAL_ROLES if role not in REQUIRED_ROLES + RECOMMENDED_ROLES
)
NON_EXCLUSIVE_ROLES = ("external", "ignore")
ALLOWED_EXTENSIONS = {".csv": "csv", ".xlsx": "xlsx", ".xls": "xls"}
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/csv",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
    "",
}
