from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domains.control_contract.domain.enums import (
    CommandStatus,
    DeviceDirection,
    DeviceRunStatus,
    SafetyStatus,
)
from app.domains.control_contract.domain.value_objects import (
    CommandIdentifier,
    CommandPayload,
    DeviceIdentifier,
)


@dataclass
class Device:
    id: DeviceIdentifier
    profile_code: str
    name: str
    enabled: bool = True
    capabilities: set[str] = field(default_factory=set)

    def supports(self, capability_code: str) -> bool:
        return capability_code in self.capabilities


@dataclass
class DeviceState:
    device_id: DeviceIdentifier
    run_status: DeviceRunStatus = DeviceRunStatus.DISCONNECTED
    direction: DeviceDirection = DeviceDirection.NONE
    current_speed: int = 0
    target_speed: int = 0
    safety_status: SafetyStatus = SafetyStatus.NORMAL
    connected: bool = False
    last_command_id: str | None = None
    last_error_message: str | None = None
    updated_at: datetime | None = None


@dataclass
class DeviceCommand:
    id: CommandIdentifier
    device_id: DeviceIdentifier
    command: str
    payload: CommandPayload
    status: CommandStatus = CommandStatus.REQUESTED
    requested_at: datetime | None = None
    sent_at: datetime | None = None
    result_payload: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    def mark_sent(self, sent_at: datetime) -> None:
        self.status = CommandStatus.SENT
        self.sent_at = sent_at

    def mark_failed(self, message: str) -> None:
        self.status = CommandStatus.FAILED
        self.error_message = message
