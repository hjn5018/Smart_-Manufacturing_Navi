from __future__ import annotations

from typing import Any

from app.domains.connection_session.infrastructure.board_session_manager import BoardSessionManager


class WebSocketSessionManagerAdapter:
    def __init__(self, manager: BoardSessionManager):
        self.manager = manager

    async def connect(self, device_id: str, channel: Any) -> None:
        await self.manager.connect(device_id, channel)

    def disconnect(self, device_id: str, channel: Any) -> bool:
        return self.manager.disconnect(device_id, channel)

    def is_connected(self, device_id: str) -> bool:
        return self.manager.is_connected(device_id)

    async def send_command(self, device_id: str, message: dict[str, Any]) -> None:
        await self.manager.send_command(device_id, message)

    async def close(self, device_id: str, reason: str = "server_requested") -> bool:
        return await self.manager.close(device_id, reason)

    def discard(self, device_id: str) -> bool:
        return self.manager.discard(device_id)
