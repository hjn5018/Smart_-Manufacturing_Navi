from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domains.capability_management.domain.enums import CapabilityStatus
from app.domains.capability_management.domain.value_objects import (
    CapabilityCode,
    CapabilityPayloadSchema,
)


@dataclass
class DeviceCapability:
    device_id: str
    code: CapabilityCode
    status: CapabilityStatus = CapabilityStatus.ENABLED
    commands: set[str] = field(default_factory=set)
    payload_schema: CapabilityPayloadSchema = field(default_factory=CapabilityPayloadSchema)

    def enabled(self) -> bool:
        return self.status == CapabilityStatus.ENABLED

    def allows_command(self, command: str) -> bool:
        return self.enabled() and command in self.commands


@dataclass
class CapabilityRule:
    device_id: str
    capability_code: CapabilityCode
    rule_key: str
    rule_value: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass(frozen=True)
class CapabilityCommand:
    capability_code: CapabilityCode
    command: str
    payload: dict[str, Any] = field(default_factory=dict)
