from __future__ import annotations

from typing import Protocol

from app.domains.operation_event.domain.entities import DeviceEvent, DeviceMetric


class EventRepository(Protocol):
    def save(self, event: DeviceEvent) -> None:
        ...

    def find_by_device(self, device_id: str, limit: int = 100) -> list[DeviceEvent]:
        ...


class MetricRepository(Protocol):
    def get(self, device_id: str, metric_key: str) -> DeviceMetric | None:
        ...

    def save(self, metric: DeviceMetric) -> None:
        ...
