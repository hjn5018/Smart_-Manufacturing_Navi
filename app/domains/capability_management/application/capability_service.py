from __future__ import annotations

from typing import Any

from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository


class CapabilityManagementService:
    def __init__(self, repository: ConveyorRepository):
        self.repository = repository

    def list_capabilities(self, device_id: str) -> list:
        self._ensure_device(device_id)
        return self.repository.list_device_capabilities(device_id)

    def get_capability(self, device_id: str, capability_code: str):
        self._ensure_device(device_id)
        return self.repository.find_device_capability(device_id, capability_code)

    def upsert_capability(
        self,
        device_id: str,
        capability_code: str,
        commands: list[str],
        payload_schema: dict[str, Any] | None,
        enabled: bool,
    ):
        self._ensure_device(device_id)
        return self.repository.ensure_device_capability(
            board_id=device_id,
            capability_code=capability_code,
            commands=commands,
            payload_schema=payload_schema,
            enabled=enabled,
        )

    def set_enabled(self, device_id: str, capability_code: str, enabled: bool):
        self._ensure_device(device_id)
        return self.repository.set_device_capability_enabled(device_id, capability_code, enabled)

    def _ensure_device(self, device_id: str) -> None:
        if self.repository.find_board(device_id) is None:
            raise ValueError("Device not found")
