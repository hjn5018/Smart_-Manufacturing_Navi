from __future__ import annotations

from collections.abc import Iterable

from app.domains.control_contract.domain.entities import Device, DeviceState
from app.domains.control_contract.domain.enums import SafetyStatus


class CommandPolicy:
    def can_accept_command(
        self,
        device: Device,
        state: DeviceState,
        command: str,
        allowed_commands: Iterable[str],
    ) -> bool:
        if not device.enabled:
            return False
        if state.safety_status == SafetyStatus.EMERGENCY_STOPPED:
            return command == "RELEASE_EMERGENCY_STOP"
        return command in set(allowed_commands)
