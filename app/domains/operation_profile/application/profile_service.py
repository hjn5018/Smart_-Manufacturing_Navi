from __future__ import annotations

from typing import Any

from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository


class OperationProfileService:
    def __init__(self, repository: ConveyorRepository):
        self.repository = repository

    def list_profiles(self) -> list:
        return self.repository.list_operation_profiles()

    def get_profile(self, profile_code: str):
        return self.repository.find_operation_profile(profile_code)

    def get_device_profile(self, device_id: str):
        self._ensure_device(device_id)
        return self.repository.find_profile_by_board(device_id)

    def upsert_profile(
        self,
        code: str,
        operation_type: str,
        allowed_commands: list[str],
        capabilities: list[str],
        enabled: bool,
        safety_policy: dict[str, Any] | None,
    ):
        return self.repository.ensure_operation_profile(
            code=code,
            operation_type=operation_type,
            allowed_commands=allowed_commands,
            capabilities=capabilities,
            enabled=enabled,
            safety_policy=safety_policy,
        )

    def assign_profile(self, device_id: str, profile_code: str):
        self._ensure_device(device_id)
        if self.repository.find_operation_profile(profile_code) is None:
            raise ValueError("Operation profile not found")
        return self.repository.assign_operation_profile(device_id, profile_code)

    def _ensure_device(self, device_id: str) -> None:
        if self.repository.find_board(device_id) is None:
            raise ValueError("Device not found")
