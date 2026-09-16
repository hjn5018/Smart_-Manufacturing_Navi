from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domains.capability_management.domain.enums import PayloadFieldType


@dataclass(frozen=True)
class CapabilityCode:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("capability code must not be empty")


@dataclass(frozen=True)
class PayloadField:
    name: str
    field_type: PayloadFieldType
    required: bool = True
    default_value: Any | None = None


@dataclass(frozen=True)
class CapabilityPayloadSchema:
    fields: tuple[PayloadField, ...] = field(default_factory=tuple)

    def required_field_names(self) -> set[str]:
        return {field.name for field in self.fields if field.required}
