from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.application_config import settings
from app.domains.control_contract.domain.enums import BoardMessageType, ConveyorCommandType
from app.domains.control_contract.infrastructure.sqlalchemy_models import ConveyorBoard, ConveyorBoardMetric, ConveyorBoardState
from app.domains.connection_session.application.session_service import ConnectionSessionService
from app.domains.control_contract.application.exceptions import (
    CommandDispatchError,
    DeviceCommandNotFoundError,
    DeviceDisabledError,
    DeviceMetricNotFoundError,
    DeviceNotConnectedError,
    DeviceNotFoundError,
    DeviceStateNotFoundError,
    DeviceTypeMismatchError,
    EmergencyStoppedError,
)
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository


class ControlContractService:
    def __init__(
        self,
        repository: ConveyorRepository,
        connection_session_service: ConnectionSessionService,
        expected_board_type: str | None = None,
        not_found_detail: str = "Device not found",
        wrong_type_detail: str = "Device type mismatch",
        disabled_detail: str = "Device is disabled",
        state_not_found_detail: str = "Device state not found",
        metric_not_found_detail: str = "Device metric not found",
        emergency_stopped_detail: str = "Device is emergency stopped",
        not_connected_detail: str = "Device is not connected",
    ):
        self.repository = repository
        self.connection_session_service = connection_session_service
        self.expected_board_type = expected_board_type
        self.not_found_detail = not_found_detail
        self.wrong_type_detail = wrong_type_detail
        self.disabled_detail = disabled_detail
        self.state_not_found_detail = state_not_found_detail
        self.metric_not_found_detail = metric_not_found_detail
        self.emergency_stopped_detail = emergency_stopped_detail
        self.not_connected_detail = not_connected_detail

    def get_status(self, board_id: str) -> dict[str, Any]:
        board = self.get_board(board_id)
        state = self.get_state(board_id)
        return {
            "board_id": board.id,
            "board_type": board.board_type,
            "name": board.name,
            "connected": state.connected,
            "run_status": state.run_status,
            "direction": state.direction,
            "current_speed": state.current_speed,
            "target_speed": state.target_speed,
            "running": state.running,
            "emergency_stopped": state.emergency_stopped,
            "last_command_id": state.last_command_id,
            "last_error_message": state.last_error_message,
            "last_seen_at": state.last_seen_at,
            "state_updated_at": state.state_updated_at,
        }

    def get_metrics(self, board_id: str) -> ConveyorBoardMetric:
        self.get_board(board_id)
        metric = self.repository.find_metric(board_id)
        if metric is None:
            raise DeviceMetricNotFoundError(self.metric_not_found_detail)
        return metric

    def get_events(self, board_id: str, limit: int = 50) -> list:
        self.get_board(board_id)
        return self.repository.list_events(board_id, limit)

    def get_commands(self, board_id: str, limit: int = 50) -> list:
        self.get_board(board_id)
        return self.repository.list_commands(board_id, limit)

    def get_pending_commands(self, board_id: str, limit: int = 50) -> list:
        self.get_board(board_id)
        return self.repository.list_pending_commands(board_id, limit)

    def get_diagnostics(self, board_id: str) -> dict[str, Any]:
        board = self.get_board(board_id)
        state = self.repository.find_state(board_id)
        metric = self.repository.find_metric(board_id)
        active_session = self.repository.find_active_session(board_id)
        pending_command_count = self.repository.count_pending_commands(board_id)
        heartbeat_recent = False
        last_ping_at = active_session.last_ping_at if active_session else None

        if state and state.last_seen_at:
            heartbeat_recent = (
                datetime.utcnow() - state.last_seen_at
            ).total_seconds() <= settings.BOARD_HEARTBEAT_STALE_SECONDS

        session_active = bool(active_session and self.connection_session_service.is_connected(board_id))
        checks = {
            "board_exists": board is not None,
            "state_exists": state is not None,
            "metric_exists": metric is not None,
            "session_active": session_active,
            "heartbeat_recent": heartbeat_recent,
            "no_pending_timeout": not self.repository.has_pending_timeout(
                board_id,
                settings.COMMAND_ACK_TIMEOUT_SECONDS,
                settings.COMMAND_RESULT_TIMEOUT_SECONDS,
            ),
            "not_emergency_stopped": bool(state and not state.emergency_stopped),
        }
        ready = all(checks.values())
        return {
            "board_id": board_id,
            "ready": ready,
            "connected": bool(state and state.connected and session_active),
            "run_status": state.run_status if state else None,
            "last_seen_at": state.last_seen_at if state else None,
            "last_ping_at": last_ping_at,
            "pending_command_count": pending_command_count,
            "last_command_id": state.last_command_id if state else None,
            "last_error_message": state.last_error_message if state else None,
            "emergency_stopped": bool(state and state.emergency_stopped),
            "checks": checks,
        }

    def get_readiness(self, board_id: str) -> dict[str, Any]:
        diagnostics = self.get_diagnostics(board_id)
        return {
            "board_id": board_id,
            "ready": diagnostics["ready"],
            "checks": diagnostics["checks"],
        }

    async def diagnostics_ping(self, board_id: str) -> dict[str, Any]:
        return await self.status_sync(board_id)

    async def set_speed(self, board_id: str, speed: int) -> dict[str, Any]:
        return await self.dispatch_command(board_id, ConveyorCommandType.SET_SPEED.value, {"speed": speed})

    async def forward(self, board_id: str) -> dict[str, Any]:
        return await self.dispatch_command(board_id, ConveyorCommandType.FORWARD.value, {})

    async def reverse(self, board_id: str) -> dict[str, Any]:
        return await self.dispatch_command(board_id, ConveyorCommandType.REVERSE.value, {})

    async def stop(self, board_id: str) -> dict[str, Any]:
        return await self.dispatch_command(board_id, ConveyorCommandType.STOP.value, {})

    async def reset(self, board_id: str) -> dict[str, Any]:
        return await self.dispatch_command(board_id, ConveyorCommandType.RESET.value, {})

    async def status_sync(self, board_id: str) -> dict[str, Any]:
        return await self.dispatch_command(board_id, ConveyorCommandType.STATUS_SYNC.value, {})

    async def release_emergency_stop(self, board_id: str) -> dict[str, Any]:
        return await self.dispatch_command(board_id, ConveyorCommandType.RELEASE_EMERGENCY_STOP.value, {})

    def timeout_command(self, board_id: str, command_id: str) -> Any:
        self.get_board(board_id)
        row = self.repository.timeout_command(board_id, command_id)
        if row is None:
            raise DeviceCommandNotFoundError("Command not found")
        return row

    def timeout_expired_commands(self, board_id: str) -> dict[str, Any]:
        self.get_board(board_id)
        count = self.repository.timeout_expired_commands(
            board_id,
            settings.COMMAND_ACK_TIMEOUT_SECONDS,
            settings.COMMAND_RESULT_TIMEOUT_SECONDS,
        )
        return {"board_id": board_id, "timed_out_count": count}

    def check_stale_session(self, board_id: str) -> dict[str, Any]:
        self.get_board(board_id)
        stale = self.connection_session_service.mark_stale_if_needed(
            board_id,
            settings.BOARD_HEARTBEAT_STALE_SECONDS,
        )
        return {"board_id": board_id, "stale": stale}

    def reset_metrics(self, board_id: str) -> Any:
        self.get_board(board_id)
        row = self.repository.reset_metrics(board_id)
        if row is None:
            raise DeviceMetricNotFoundError(self.metric_not_found_detail)
        return row

    async def register_board_session(self, board_id: str, websocket: Any) -> str:
        self.get_board(board_id)
        return await self.connection_session_service.register_session(board_id, websocket)

    def unregister_board_session(self, board_id: str, websocket: Any, reason: str = "disconnected") -> None:
        self.connection_session_service.unregister_session(board_id, websocket, reason)

    async def disconnect_board_session(self, board_id: str, reason: str = "server_requested") -> bool:
        self.get_board(board_id)
        return await self.connection_session_service.disconnect_device(board_id, reason)

    def handle_common_board_message(self, message: dict[str, Any]) -> bool:
        message_type = message.get("type")
        if message_type == BoardMessageType.ACK.value:
            self.handle_ack(message)
        elif message_type == BoardMessageType.RESULT.value:
            self.handle_result(message)
        elif message_type == BoardMessageType.STATUS.value:
            self.handle_status(message)
        elif message_type == BoardMessageType.ERROR.value and message.get("status") == "EMERGENCY_STOPPED":
            self.handle_emergency_stop(message)
        elif message_type == BoardMessageType.HEARTBEAT.value:
            self.handle_heartbeat(message)
        else:
            return False
        return True

    def handle_ack(self, message: dict[str, Any]) -> None:
        command_id = message.get("command_id")
        if command_id:
            self.repository.mark_command_acked(command_id)

    def handle_result(self, message: dict[str, Any]) -> None:
        command_id = message.get("command_id")
        if not command_id:
            return
        if message.get("status") == "COMPLETED":
            command = self.repository.mark_command_completed(command_id)
            if command is not None:
                self.repository.apply_completed_command(command, message.get("state"))
        elif message.get("status") == "FAILED":
            command = self.repository.mark_command_failed(command_id, message.get("error_message"))
            if command is not None:
                self.repository.create_event(
                    command.board_id,
                    "ERROR_OCCURRED",
                    {"command_id": command_id, "error_message": message.get("error_message")},
                    command_id,
                )

    def handle_status(self, message: dict[str, Any]) -> None:
        board_id = message.get("board_id")
        if not board_id:
            return
        state = message.get("state") or {}
        state["status"] = message.get("status", state.get("status"))
        self.repository.update_runtime_state(board_id, state, message.get("command_id"))

    def handle_heartbeat(self, message: dict[str, Any]) -> None:
        board_id = message.get("board_id")
        if board_id:
            self.connection_session_service.record_heartbeat(board_id)

    def handle_emergency_stop(self, message: dict[str, Any]) -> None:
        board_id = message.get("board_id")
        if board_id:
            self.repository.apply_emergency_stop(board_id, message.get("error_message"), message)

    async def dispatch_command(self, board_id: str, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.get_board(board_id)
        state = self.get_state(board_id)
        if self.repository.find_active_session(board_id) is None or not self.connection_session_service.is_connected(board_id):
            raise DeviceNotConnectedError(self.not_connected_detail)
        emergency_allowed = {
            ConveyorCommandType.STOP.value,
            ConveyorCommandType.EMERGENCY_STOP.value,
            ConveyorCommandType.RESET.value,
            ConveyorCommandType.RELEASE_EMERGENCY_STOP.value,
        }
        if state.emergency_stopped and command not in emergency_allowed:
            raise EmergencyStoppedError(self.emergency_stopped_detail)

        command_id = f"cmd-{uuid4().hex}"
        row = self.repository.create_command(command_id, board_id, command, payload)
        message = {
            "command_id": command_id,
            "board_id": board_id,
            "command": command,
            "payload": payload,
        }
        try:
            await self.connection_session_service.send_command(board_id, message)
        except RuntimeError as exc:
            self.repository.mark_command_failed(command_id, str(exc))
            raise DeviceNotConnectedError(self.not_connected_detail) from exc
        except Exception as exc:
            self.repository.mark_command_failed(command_id, str(exc))
            raise CommandDispatchError("Failed to send command to board") from exc

        self.repository.mark_command_sent(command_id)
        return {
            "command_id": row.id,
            "board_id": row.board_id,
            "command": row.command,
            "status": "SENT",
        }

    def get_board(self, board_id: str) -> ConveyorBoard:
        board = self.repository.find_board(board_id)
        if board is None:
            raise DeviceNotFoundError(self.not_found_detail)
        if not board.enabled:
            raise DeviceDisabledError(self.disabled_detail)
        if self.expected_board_type and board.board_type != self.expected_board_type:
            raise DeviceTypeMismatchError(self.wrong_type_detail)
        return board

    def get_state(self, board_id: str) -> ConveyorBoardState:
        state = self.repository.find_state(board_id)
        if state is None:
            raise DeviceStateNotFoundError(self.state_not_found_detail)
        return state
