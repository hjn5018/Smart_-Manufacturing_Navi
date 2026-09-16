from __future__ import annotations

from typing import Protocol

from app.domains.capability_management.domain.entities import DeviceCapability, CapabilityRule
from app.domains.capability_management.domain.value_objects import CapabilityCode


class CapabilityRepository(Protocol):
    def find_by_device(self, device_id: str) -> list[DeviceCapability]:
        ...

    def get(self, device_id: str, code: CapabilityCode) -> DeviceCapability | None:
        ...

    def save(self, capability: DeviceCapability) -> None:
        ...


class CapabilityRuleRepository(Protocol):
    def find_by_capability(self, device_id: str, code: CapabilityCode) -> list[CapabilityRule]:
        ...

    def save(self, rule: CapabilityRule) -> None:
        ...
