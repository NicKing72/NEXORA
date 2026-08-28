"""Declarative base shared by future domain models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for every persisted NEXORA entity."""
