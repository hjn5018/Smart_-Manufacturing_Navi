from __future__ import annotations

from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository


class EventMetricService:
    def __init__(self, repository: ConveyorRepository):
        self.repository = repository

    def list_events(self, device_id: str, limit: int = 50) -> list:
        self._ensure_device(device_id)
        return self.repository.list_events(device_id, limit)

    def get_metrics(self, device_id: str):
        self._ensure_device(device_id)
        return self.repository.find_metric(device_id)

    def reset_metrics(self, device_id: str):
        self._ensure_device(device_id)
        return self.repository.reset_metrics(device_id)

    def _ensure_device(self, device_id: str) -> None:
        if self.repository.find_board(device_id) is None:
            raise ValueError("Device not found")
