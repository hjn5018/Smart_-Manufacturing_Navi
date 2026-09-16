from typing import Any

from fastapi import HTTPException, WebSocket

from app.domains.control_contract.domain.enums import BoardMessageType, BoardType, ColorType, ConveyorCommandType
from app.domains.control_contract.infrastructure.sqlalchemy_models import ConveyorBoard, ConveyorBoardMetric, ConveyorBoardState
from app.domains.connection_session.application.session_service import ConnectionSessionService
from app.domains.connection_session.infrastructure.websocket_session_manager_adapter import WebSocketSessionManagerAdapter
from app.domains.control_contract.application.command_service import ControlContractService
from app.domains.control_contract.application.exceptions import ControlContractError
from app.domains.connection_session.infrastructure.board_session_manager import BoardSessionManager
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository


USE_CLASS_BOARD_TYPE = object()


class ContainerConveyorService:
    expected_board_type = BoardType.CONTAINER_CONVEYOR.value
    not_found_detail = "Container conveyor board not found"
    wrong_type_detail = "Board is not a container conveyor"
    disabled_detail = "Container conveyor board is disabled"

    def __init__(
        self,
        repository: ConveyorRepository,
        session_manager: BoardSessionManager,
        expected_board_type=USE_CLASS_BOARD_TYPE,
    ):
        self.repository = repository
        self.session_manager = session_manager
        if expected_board_type is not USE_CLASS_BOARD_TYPE:
            self.expected_board_type = expected_board_type
        self.connection_session_service = ConnectionSessionService(
            repository,
            WebSocketSessionManagerAdapter(session_manager),
        )
        self.control_service = ControlContractService(
            repository=repository,
            connection_session_service=self.connection_session_service,
            expected_board_type=self.expected_board_type,
            not_found_detail=self.not_found_detail,
            wrong_type_detail=self.wrong_type_detail,
            disabled_detail=self.disabled_detail,
            state_not_found_detail="Container conveyor state not found",
            metric_not_found_detail="Container conveyor metric not found",
            emergency_stopped_detail="Container conveyor is emergency stopped",
            not_connected_detail="Container conveyor board is not connected",
        )

    def get_status(self, board_id: str) -> dict[str, Any]:
        return self._call(self.control_service.get_status, board_id)

    def get_metrics(self, board_id: str) -> ConveyorBoardMetric:
        return self._call(self.control_service.get_metrics, board_id)

    def get_color_counts(self, board_id: str) -> dict[str, Any]:
        self._get_container_board(board_id)
        return {
            "board_id": board_id,
            "counts": self.repository.list_color_counts(board_id),
        }

    def get_color_detections(self, board_id: str, limit: int = 50) -> list:
        self._get_container_board(board_id)
        return self.repository.list_color_detections(board_id, limit)

    def get_events(self, board_id: str, limit: int = 50) -> list:
        return self._call(self.control_service.get_events, board_id, limit)

    def get_commands(self, board_id: str, limit: int = 50) -> list:
        return self._call(self.control_service.get_commands, board_id, limit)

    def get_pending_commands(self, board_id: str, limit: int = 50) -> list:
        return self._call(self.control_service.get_pending_commands, board_id, limit)

    def get_color_rules(self, board_id: str) -> list:
        self._get_container_board(board_id)
        return self.repository.list_color_rules(board_id)

    def get_diagnostics(self, board_id: str) -> dict[str, Any]:
        return self._call(self.control_service.get_diagnostics, board_id)

    def get_readiness(self, board_id: str) -> dict[str, Any]:
        return self._call(self.control_service.get_readiness, board_id)

    async def diagnostics_ping(self, board_id: str) -> dict[str, Any]:
        return await self._async_call(self.control_service.diagnostics_ping, board_id)

    async def set_speed(self, board_id: str, speed: int) -> dict[str, Any]:
        return await self._async_call(self.control_service.set_speed, board_id, speed)

    async def forward(self, board_id: str) -> dict[str, Any]:
        return await self._async_call(self.control_service.forward, board_id)

    async def reverse(self, board_id: str) -> dict[str, Any]:
        return await self._async_call(self.control_service.reverse, board_id)

    async def stop(self, board_id: str) -> dict[str, Any]:
        return await self._async_call(self.control_service.stop, board_id)

    async def sort_color(self, board_id: str, color: ColorType) -> dict[str, Any]:
        payload = {"color": color.value}
        rule = self.repository.find_enabled_color_rule(board_id, color.value)
        if rule is not None:
            payload["target_position"] = rule.target_position
        return await self._dispatch_command(board_id, ConveyorCommandType.SORT_COLOR.value, payload)

    async def reset(self, board_id: str) -> dict[str, Any]:
        return await self._async_call(self.control_service.reset, board_id)

    async def status_sync(self, board_id: str) -> dict[str, Any]:
        return await self._async_call(self.control_service.status_sync, board_id)

    async def release_emergency_stop(self, board_id: str) -> dict[str, Any]:
        return await self._async_call(self.control_service.release_emergency_stop, board_id)

    def timeout_command(self, board_id: str, command_id: str) -> Any:
        return self._call(self.control_service.timeout_command, board_id, command_id)

    def timeout_expired_commands(self, board_id: str) -> dict[str, Any]:
        return self._call(self.control_service.timeout_expired_commands, board_id)

    def check_stale_session(self, board_id: str) -> dict[str, Any]:
        return self._call(self.control_service.check_stale_session, board_id)

    def reset_metrics(self, board_id: str) -> Any:
        return self._call(self.control_service.reset_metrics, board_id)

    def reset_color_counts(self, board_id: str) -> dict[str, Any]:
        self._get_container_board(board_id)
        return {"board_id": board_id, "counts": self.repository.reset_color_counts(board_id)}

    def create_color_rule(self, board_id: str, color: ColorType, target_position: str, enabled: bool) -> Any:
        self._get_container_board(board_id)
        return self.repository.create_color_rule(board_id, color.value, target_position, enabled)

    def update_color_rule(self, board_id: str, rule_id: int, color: ColorType, target_position: str, enabled: bool) -> Any:
        self._get_container_board(board_id)
        row = self.repository.update_color_rule(board_id, rule_id, color.value, target_position, enabled)
        if row is None:
            raise HTTPException(status_code=404, detail="Color rule not found")
        return row

    def disable_color_rule(self, board_id: str, rule_id: int) -> Any:
        self._get_container_board(board_id)
        row = self.repository.disable_color_rule(board_id, rule_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Color rule not found")
        return row

    async def register_board_session(self, board_id: str, websocket: WebSocket) -> str:
        return await self._async_call(self.control_service.register_board_session, board_id, websocket)

    def unregister_board_session(self, board_id: str, websocket: WebSocket, reason: str = "disconnected") -> None:
        return self._call(self.control_service.unregister_board_session, board_id, websocket, reason)

    async def disconnect_board_session(self, board_id: str, reason: str = "server_requested") -> bool:
        return await self._async_call(self.control_service.disconnect_board_session, board_id, reason)

    def handle_board_message(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        if self.control_service.handle_common_board_message(message):
            return
        if message_type == BoardMessageType.COLOR_DETECTED.value:
            self.handle_color_detected(message)
        else:
            board_id = message.get("board_id")
            if board_id:
                self.repository.create_event(board_id, "ERROR_OCCURRED", {"message": "unsupported board message", "raw": message})

    def handle_ack(self, message: dict[str, Any]) -> None:
        self.control_service.handle_ack(message)

    def handle_result(self, message: dict[str, Any]) -> None:
        self.control_service.handle_result(message)

    def handle_status(self, message: dict[str, Any]) -> None:
        self.control_service.handle_status(message)

    def handle_heartbeat(self, message: dict[str, Any]) -> None:
        self.control_service.handle_heartbeat(message)

    def handle_emergency_stop(self, message: dict[str, Any]) -> None:
        self.control_service.handle_emergency_stop(message)

    def handle_color_detected(self, message: dict[str, Any]) -> None:
        board_id = message.get("board_id")
        color = message.get("color")
        if board_id and color:
            try:
                color = ColorType(color).value
            except ValueError:
                color = ColorType.UNKNOWN.value
            self.repository.record_color_detected(board_id, color, message.get("confidence"), message)

    async def _dispatch_command(self, board_id: str, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._async_call(self.control_service.dispatch_command, board_id, command, payload)

    def _get_container_board(self, board_id: str) -> ConveyorBoard:
        return self._call(self.control_service.get_board, board_id)

    def _get_state(self, board_id: str) -> ConveyorBoardState:
        return self._call(self.control_service.get_state, board_id)

    def _call(self, func, *args):
        try:
            return func(*args)
        except ControlContractError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    async def _async_call(self, func, *args):
        try:
            return await func(*args)
        except ControlContractError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
