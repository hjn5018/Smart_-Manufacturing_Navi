from __future__ import annotations

from typing import Protocol

from app.domains.connection_session.domain.entities import DeviceSession
from app.domains.connection_session.domain.value_objects import DeviceIdentifier, SessionIdentifier


class SessionRepository(Protocol):
    def get(self, session_id: SessionIdentifier) -> DeviceSession | None:
        ...

    def find_active_by_device(self, device_id: DeviceIdentifier) -> DeviceSession | None:
        ...

    def save(self, session: DeviceSession) -> None:
        ...
