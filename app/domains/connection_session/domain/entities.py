from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domains.connection_session.domain.enums import SessionStatus
from app.domains.connection_session.domain.value_objects import DeviceIdentifier, SessionIdentifier


@dataclass
class DeviceSession:
    id: SessionIdentifier
    device_id: DeviceIdentifier
    status: SessionStatus = SessionStatus.CONNECTED
    connected_at: datetime | None = None
    disconnected_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    disconnect_reason: str | None = None

    @property
    def active(self) -> bool:
        return self.status == SessionStatus.CONNECTED


@dataclass(frozen=True)
class Heartbeat:
    device_id: DeviceIdentifier
    received_at: datetime
