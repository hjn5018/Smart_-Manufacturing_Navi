from fastapi import WebSocket
from starlette.websockets import WebSocketState


class BoardSessionManager:
    def __init__(self):
        self.active_sessions: dict[str, WebSocket] = {}

    async def connect(self, board_id: str, websocket: WebSocket) -> None:
        if websocket.application_state == WebSocketState.CONNECTING:
            await websocket.accept()
        old = self.active_sessions.get(board_id)
        if old is not None:
            await old.close(code=4000, reason="reconnected")
        self.active_sessions[board_id] = websocket

    def disconnect(self, board_id: str, websocket: WebSocket) -> bool:
        if self.active_sessions.get(board_id) is websocket:
            self.active_sessions.pop(board_id, None)
            return True
        return False

    def is_connected(self, board_id: str) -> bool:
        return board_id in self.active_sessions

    async def send_command(self, board_id: str, message: dict) -> None:
        websocket = self.active_sessions.get(board_id)
        if websocket is None:
            raise RuntimeError("board websocket session is not connected")
        await websocket.send_json(message)

    async def close(self, board_id: str, reason: str = "server_requested") -> bool:
        websocket = self.active_sessions.pop(board_id, None)
        if websocket is None:
            return False
        await websocket.close(code=1000, reason=reason)
        return True

    def discard(self, board_id: str) -> bool:
        return self.active_sessions.pop(board_id, None) is not None


board_session_manager = BoardSessionManager()
