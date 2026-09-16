from __future__ import annotations

from typing import Protocol

from app.domains.control_contract.domain.entities import Device, DeviceCommand, DeviceState
from app.domains.control_contract.domain.value_objects import CommandIdentifier, DeviceIdentifier


class DeviceRepository(Protocol):
    def get(self, device_id: DeviceIdentifier) -> Device | None:
        ...

    def save(self, device: Device) -> None:
        ...


class DeviceStateRepository(Protocol):
    def get(self, device_id: DeviceIdentifier) -> DeviceState | None:
        ...

    def save(self, state: DeviceState) -> None:
        ...


class DeviceCommandRepository(Protocol):
    def get(self, command_id: CommandIdentifier) -> DeviceCommand | None:
        ...

    def save(self, command: DeviceCommand) -> None:
        ...
