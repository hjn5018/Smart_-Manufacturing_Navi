from __future__ import annotations

from typing import Any, Protocol


class SessionChannelManager(Protocol):
    async def connect(self, device_id: str, channel: Any) -> None:
        ...

    def disconnect(self, device_id: str, channel: Any) -> bool | None:
        ...

    def is_connected(self, device_id: str) -> bool:
        ...

    async def send_command(self, device_id: str, message: dict[str, Any]) -> None:
        ...

    async def close(self, device_id: str, reason: str = "server_requested") -> bool:
        ...

    def discard(self, device_id: str) -> bool:
        ...
