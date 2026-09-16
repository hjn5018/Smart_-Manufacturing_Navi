from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProfileCode:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("profile code must not be empty")


@dataclass(frozen=True)
class AllowedCommand:
    command: str
    payload_template: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProfileCapability:
    capability_code: str
    required: bool = False


@dataclass(frozen=True)
class ProfileSafetyPolicy:
    emergency_stop_enabled: bool = True
    reject_commands_while_emergency_stopped: bool = True
