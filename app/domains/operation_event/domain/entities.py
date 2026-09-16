from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domains.operation_event.domain.enums import EventType, MetricType


@dataclass
class DeviceEvent:
    device_id: str
    event_type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    command_id: str | None = None
    occurred_at: datetime | None = None


@dataclass
class DeviceMetric:
    device_id: str
    metric_type: MetricType
    value: int = 0
    capability_code: str | None = None
    updated_at: datetime | None = None

    def increase(self, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("metric increase amount must not be negative")
        self.value += amount


@dataclass(frozen=True)
class MetricSnapshot:
    device_id: str
    values: dict[str, int]
    measured_at: datetime
