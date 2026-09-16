from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from app.domains.connection_session.domain.entities import DeviceSession
from app.domains.connection_session.domain.enums import SessionStatus


class ConnectionChannel(Protocol):
    async def send_json(self, payload: dict) -> None:
        ...


class SessionPolicy:
    def mark_stale_when_expired(
        self,
        session: DeviceSession,
        now: datetime,
        timeout: timedelta,
    ) -> DeviceSession:
        if session.last_heartbeat_at and now - session.last_heartbeat_at > timeout:
            session.status = SessionStatus.STALE
        return session
