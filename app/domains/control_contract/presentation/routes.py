from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependent_manager import verify_control_api_key
from app.domains.capability_management.application.capability_service import CapabilityManagementService
from app.domains.capability_management.application.container_conveyor_service import ContainerConveyorService
from app.domains.connection_session.infrastructure.board_session_manager import board_session_manager
from app.domains.control_contract.application.command_service import ControlContractService
from app.domains.control_contract.application.exceptions import ControlContractError
from app.domains.control_contract.domain.enums import ColorType
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository
from app.domains.control_contract.presentation.schemas import (
    BoardMetricResponse,
    BoardStatusResponse,
    CapabilityResponse,
    CommandHistoryResponse,
    CommandResponse,
    ConnectedDeviceResponse,
    DeviceProfileResponse,
    DeviceResponse,
    DiagnosticsResponse,
    EventResponse,
    GenericCapabilityCommandRequest,
    GenericCommandRequest,
    SessionResponse,
)
from app.domains.operation_profile.application.profile_service import OperationProfileService
from app.infra.db.session import get_db


router = APIRouter(
    prefix="/api/devices",
    tags=["devices"],
    dependencies=[Depends(verify_control_api_key)],
)


def get_control_service(db=Depends(get_db)):
    return ControlContractService(
        repository=ConveyorRepository(db),
        connection_session_service=_build_session_service(db),
        expected_board_type=None,
    )


def _build_session_service(db):
    from app.domains.connection_session.application.session_service import ConnectionSessionService
    from app.domains.connection_session.infrastructure.websocket_session_manager_adapter import (
        WebSocketSessionManagerAdapter,
    )

    return ConnectionSessionService(
        ConveyorRepository(db),
        WebSocketSessionManagerAdapter(board_session_manager),
    )


# 현재 WebSocket 세션이 활성화된 device만 조회한다.
@router.get("/connected", response_model=list[ConnectedDeviceResponse])
def list_connected_devices(db=Depends(get_db)):
    repository = ConveyorRepository(db)
    connected = []
    for board in repository.list_boards():
        session = repository.find_active_session(board.id)
        if session is None or not board_session_manager.is_connected(board.id):
            continue
        connected.append({
            "id": board.id,
            "board_type": board.board_type,
            "name": board.name,
            "session_id": session.id,
            "connected": True,
            "connected_at": session.connected_at,
            "last_heartbeat_at": session.last_ping_at,
        })
    return connected


# 등록된 모든 제어 대상 device를 조회한다.
@router.get("", response_model=list[DeviceResponse])
def list_devices(db=Depends(get_db)):
    return ConveyorRepository(db).list_boards()


# device 기본 정보를 조회한다.
@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(device_id: str, service: ControlContractService = Depends(get_control_service)):
    return _call(service.get_board, device_id)


# device의 현재 연결/운전/속도/비상정지 상태를 조회한다.
@router.get("/{device_id}/state", response_model=BoardStatusResponse)
def get_device_state(device_id: str, service: ControlContractService = Depends(get_control_service)):
    return _call(service.get_status, device_id)


# device의 누적 가동 시간, 명령 수, 실패 수 같은 운영 지표를 조회한다.
@router.get("/{device_id}/metrics", response_model=BoardMetricResponse)
def get_device_metrics(device_id: str, service: ControlContractService = Depends(get_control_service)):
    return _call(service.get_metrics, device_id)


# device의 운영 지표를 초기화한다.
@router.post("/{device_id}/metrics/reset", response_model=BoardMetricResponse)
def reset_device_metrics(device_id: str, service: ControlContractService = Depends(get_control_service)):
    return _call(service.reset_metrics, device_id)


# device에서 발생한 이벤트 이력을 조회한다.
@router.get("/{device_id}/events", response_model=list[EventResponse])
def get_device_events(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: ControlContractService = Depends(get_control_service),
):
    return _call(service.get_events, device_id, limit)


# device에 요청된 명령 이력을 조회한다.
@router.get("/{device_id}/commands", response_model=list[CommandHistoryResponse])
def get_device_commands(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: ControlContractService = Depends(get_control_service),
):
    return _call(service.get_commands, device_id, limit)


# 아직 완료되지 않은 대기/전송/ACK 상태 명령을 조회한다.
@router.get("/{device_id}/commands/pending", response_model=list[CommandHistoryResponse])
def get_device_pending_commands(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: ControlContractService = Depends(get_control_service),
):
    return _call(service.get_pending_commands, device_id, limit)


# board type과 무관하게 device로 범용 제어 명령을 전송한다.
@router.post("/{device_id}/commands", response_model=CommandResponse)
async def dispatch_device_command(
    device_id: str,
    req: GenericCommandRequest,
    service: ControlContractService = Depends(get_control_service),
):
    return await _async_call(service.dispatch_command, device_id, req.command, req.payload)


# 특정 명령을 수동 timeout 상태로 변경한다.
@router.post("/{device_id}/commands/{command_id}/timeout", response_model=CommandHistoryResponse)
def timeout_device_command(
    device_id: str,
    command_id: str,
    service: ControlContractService = Depends(get_control_service),
):
    return _call(service.timeout_command, device_id, command_id)


# timeout 기준을 초과한 pending 명령을 찾아 timeout 처리한다.
@router.post("/{device_id}/commands/timeout-expired")
def timeout_expired_device_commands(
    device_id: str,
    service: ControlContractService = Depends(get_control_service),
):
    return _call(service.timeout_expired_commands, device_id)


# device readiness 판단에 필요한 진단 정보를 조회한다.
@router.get("/{device_id}/diagnostics", response_model=DiagnosticsResponse)
def get_device_diagnostics(
    device_id: str,
    service: ControlContractService = Depends(get_control_service),
):
    return _call(service.get_diagnostics, device_id)


# device가 명령을 받을 수 있는 준비 상태인지 간단히 조회한다.
@router.get("/{device_id}/diagnostics/readiness")
def get_device_readiness(
    device_id: str,
    service: ControlContractService = Depends(get_control_service),
):
    return _call(service.get_readiness, device_id)


# device에 상태 동기화용 ping 명령을 전송한다.
@router.post("/{device_id}/diagnostics/ping", response_model=CommandResponse)
async def ping_device(
    device_id: str,
    service: ControlContractService = Depends(get_control_service),
):
    return await _async_call(service.diagnostics_ping, device_id)


# device의 WebSocket session 연결 이력을 조회한다.
@router.get("/{device_id}/sessions", response_model=list[SessionResponse])
def get_device_sessions(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db=Depends(get_db),
    service: ControlContractService = Depends(get_control_service),
):
    _call(service.get_board, device_id)
    return ConveyorRepository(db).list_sessions(device_id, limit)


# heartbeat 기준으로 stale session 여부를 검사하고 필요하면 상태를 갱신한다.
@router.post("/{device_id}/sessions/check-stale")
def check_device_stale_session(
    device_id: str,
    service: ControlContractService = Depends(get_control_service),
):
    return _call(service.check_stale_session, device_id)


# 서버가 해당 device의 현재 WebSocket 연결을 강제로 종료한다.
@router.post("/{device_id}/sessions/disconnect")
async def disconnect_device_session(
    device_id: str,
    service: ControlContractService = Depends(get_control_service),
):
    disconnected = await _async_call(service.disconnect_board_session, device_id)
    return {"device_id": device_id, "disconnected": disconnected}


# device에 등록된 capability 목록을 조회한다.
@router.get("/{device_id}/capabilities", response_model=list[CapabilityResponse])
def get_device_capabilities(
    device_id: str,
    db=Depends(get_db),
    service: ControlContractService = Depends(get_control_service),
):
    _call(service.get_board, device_id)
    capability_service = CapabilityManagementService(ConveyorRepository(db))
    return [_capability_response(row) for row in capability_service.list_capabilities(device_id)]


# 특정 capability에 속한 명령을 device로 전송한다.
@router.post("/{device_id}/capabilities/{capability_code}/commands", response_model=CommandResponse)
async def dispatch_capability_command(
    device_id: str,
    capability_code: str,
    req: GenericCapabilityCommandRequest,
    db=Depends(get_db),
    service: ControlContractService = Depends(get_control_service),
):
    _call(service.get_board, device_id)
    capability_service = CapabilityManagementService(ConveyorRepository(db))
    capabilities = {
        row.capability_code
        for row in capability_service.list_capabilities(device_id)
        if row.enabled
    }
    if capability_code not in capabilities:
        raise HTTPException(status_code=404, detail="Device capability not found")
    if capability_code == "COLOR_CLASSIFICATION":
        color = req.payload.get("color")
        if not color:
            raise HTTPException(status_code=400, detail="color is required")
        container_service = ContainerConveyorService(ConveyorRepository(db), board_session_manager, expected_board_type=None)
        try:
            color_type = ColorType(color)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Unsupported color") from exc
        return await container_service.sort_color(device_id, color_type)
    return await _async_call(service.dispatch_command, device_id, req.command, req.payload)


# device에 할당된 operation profile을 조회한다.
@router.get("/{device_id}/profile", response_model=DeviceProfileResponse)
def get_device_profile(
    device_id: str,
    db=Depends(get_db),
    service: ControlContractService = Depends(get_control_service),
):
    _call(service.get_board, device_id)
    profile_service = OperationProfileService(ConveyorRepository(db))
    row = profile_service.get_device_profile(device_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Device profile assignment not found")
    return {
        "device_id": device_id,
        "profile_code": row.code,
        "operation_type": row.operation_type,
        "allowed_commands": row.allowed_commands_json or [],
        "capabilities": row.capabilities_json or [],
    }


def _capability_response(row) -> dict[str, Any]:
    return {
        "id": row.id,
        "board_id": row.board_id,
        "capability_code": row.capability_code,
        "code": row.capability_code,
        "enabled": row.enabled,
        "commands": row.commands_json or [],
        "payload_schema": row.payload_schema_json or {},
    }


def _call(func, *args):
    try:
        return func(*args)
    except ControlContractError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


async def _async_call(func, *args):
    try:
        return await func(*args)
    except ControlContractError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
