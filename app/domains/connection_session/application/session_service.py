from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.domains.connection_session.application.ports import SessionChannelManager
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository


class ConnectionSessionService:
    def __init__(
        self,
        repository: ConveyorRepository,
        session_manager: SessionChannelManager,
    ):
        self.repository = repository
        self.session_manager = session_manager

    async def register_session(self, device_id: str, channel: Any) -> str:
        session_id = f"session-{uuid4().hex}"
        await self.session_manager.connect(device_id, channel)
        self.repository.create_session(session_id, device_id)
        return session_id

    def unregister_session(self, device_id: str, channel: Any, reason: str = "disconnected") -> None:
        removed = self.session_manager.disconnect(device_id, channel)
        if removed is not False:
            self.repository.disconnect_board(device_id, reason)

    async def disconnect_device(self, device_id: str, reason: str = "server_requested") -> bool:
        closed = await self.session_manager.close(device_id, reason)
        if closed:
            self.repository.disconnect_board(device_id, reason)
        return closed

    def is_connected(self, device_id: str) -> bool:
        return self.session_manager.is_connected(device_id)

    async def send_command(self, device_id: str, message: dict[str, Any]) -> None:
        await self.session_manager.send_command(device_id, message)

    def record_heartbeat(self, device_id: str) -> None:
        self.repository.record_heartbeat(device_id)

    def mark_stale_if_needed(self, device_id: str, stale_after_seconds: int) -> bool:
        stale = self.repository.mark_stale_if_needed(device_id, stale_after_seconds)
        if stale:
            discard = getattr(self.session_manager, "discard", None)
            if discard is not None:
                discard(device_id)
        return stale
