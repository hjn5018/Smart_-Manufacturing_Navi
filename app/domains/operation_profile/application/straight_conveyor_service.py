from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.domains.control_contract.domain.enums import BoardType
from app.domains.control_contract.infrastructure.sqlalchemy_models import ConveyorBoardMetric
from app.domains.connection_session.application.session_service import ConnectionSessionService
from app.domains.connection_session.infrastructure.websocket_session_manager_adapter import WebSocketSessionManagerAdapter
from app.domains.control_contract.application.command_service import ControlContractService
from app.domains.control_contract.application.exceptions import ControlContractError
from app.domains.connection_session.infrastructure.board_session_manager import BoardSessionManager
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository


class StraightConveyorService:
    expected_board_type = BoardType.STRAIGHT_CONVEYOR.value
    not_found_detail = "Straight conveyor board not found"
    wrong_type_detail = "Board is not a straight conveyor"
    disabled_detail = "Straight conveyor board is disabled"

    def __init__(
        self,
        repository: ConveyorRepository,
        session_manager: BoardSessionManager,
    ):
        self.repository = repository
        self.session_manager = session_manager
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
            state_not_found_detail="Straight conveyor state not found",
            metric_not_found_detail="Straight conveyor metric not found",
            emergency_stopped_detail="Straight conveyor is emergency stopped",
            not_connected_detail="Straight conveyor board is not connected",
        )

    def get_status(self, board_id: str) -> dict[str, Any]:
        return self._call(self.control_service.get_status, board_id)

    def get_metrics(self, board_id: str) -> ConveyorBoardMetric:
        return self._call(self.control_service.get_metrics, board_id)

    def get_events(self, board_id: str, limit: int = 50) -> list:
        return self._call(self.control_service.get_events, board_id, limit)

    def get_commands(self, board_id: str, limit: int = 50) -> list:
        return self._call(self.control_service.get_commands, board_id, limit)

    def get_pending_commands(self, board_id: str, limit: int = 50) -> list:
        return self._call(self.control_service.get_pending_commands, board_id, limit)

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
