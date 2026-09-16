from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionIdentifier:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("session id must not be empty")


@dataclass(frozen=True)
class DeviceIdentifier:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("device id must not be empty")
