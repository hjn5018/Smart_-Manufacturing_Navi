from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class CommandPayload:
    values: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.values)


@dataclass(frozen=True)
class DeviceIdentifier:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("device id must not be empty")


@dataclass(frozen=True)
class CommandIdentifier:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("command id must not be empty")


@dataclass(frozen=True)
class IssuedAt:
    value: datetime
