import json

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.dependent_manager import get_board_connection_service, get_container_conveyor_service, verify_control_api_key
from app.core.application_config import settings
from app.domains.device_registration.application.registration_service import DeviceRegistrationService
from app.domains.connection_session.infrastructure.board_session_manager import board_session_manager
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository
from app.domains.control_contract.presentation.schemas import (
    BoardMetricResponse,
    BoardStatusResponse,
    ColorRuleRequest,
    ColorRuleResponse,
    ColorCountsResponse,
    CommandHistoryResponse,
    CommandResponse,
    DetectionResponse,
    DiagnosticsResponse,
    EventResponse,
    SortColorRequest,
    SpeedRequest,
)
from app.domains.capability_management.application.container_conveyor_service import ContainerConveyorService
from app.infra.db.session import get_db


router = APIRouter(
    prefix="/api/container-conveyors",
    tags=["container-conveyors"],
    dependencies=[Depends(verify_control_api_key)],
)
ws_router = APIRouter(tags=["board-websocket"])


# container conveyor의 현재 상태를 조회한다.
@router.get("/{board_id}/status", response_model=BoardStatusResponse)
def get_status(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.get_status(board_id)


# container conveyor의 운영 지표를 조회한다.
@router.get("/{board_id}/metrics", response_model=BoardMetricResponse)
def get_metrics(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.get_metrics(board_id)


# 색상별 누적 감지 수를 조회한다.
@router.get("/{board_id}/colors/counts", response_model=ColorCountsResponse)
def get_color_counts(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.get_color_counts(board_id)


# ESP가 보고한 색상 감지 이력을 조회한다.
@router.get("/{board_id}/colors/detections", response_model=list[DetectionResponse])
def get_color_detections(
    board_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.get_color_detections(board_id, limit)


# container conveyor에서 발생한 이벤트 이력을 조회한다.
@router.get("/{board_id}/events", response_model=list[EventResponse])
def get_events(
    board_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.get_events(board_id, limit)


# container conveyor에 요청된 명령 이력을 조회한다.
@router.get("/{board_id}/commands", response_model=list[CommandHistoryResponse])
def get_commands(
    board_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.get_commands(board_id, limit)


# 아직 완료되지 않은 container conveyor 명령을 조회한다.
@router.get("/{board_id}/commands/pending", response_model=list[CommandHistoryResponse])
def get_pending_commands(
    board_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.get_pending_commands(board_id, limit)


# 색상별 분류 목적지 rule 목록을 조회한다.
@router.get("/{board_id}/color-rules", response_model=list[ColorRuleResponse])
def get_color_rules(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.get_color_rules(board_id)


# container conveyor의 readiness 판단용 진단 정보를 조회한다.
@router.get("/{board_id}/diagnostics", response_model=DiagnosticsResponse)
def get_diagnostics(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.get_diagnostics(board_id)


# container conveyor가 명령을 받을 수 있는 준비 상태인지 조회한다.
@router.get("/{board_id}/diagnostics/readiness")
def get_readiness(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.get_readiness(board_id)


# 상태 동기화를 위해 STATUS_SYNC 명령을 전송한다.
@router.post("/{board_id}/diagnostics/ping", response_model=CommandResponse)
async def diagnostics_ping(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return await service.diagnostics_ping(board_id)


# 색상 분류 rule을 생성한다.
@router.post("/{board_id}/color-rules", response_model=ColorRuleResponse)
def create_color_rule(
    board_id: str,
    req: ColorRuleRequest,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.create_color_rule(board_id, req.color, req.target_position, req.enabled)


# 색상 분류 rule을 수정한다.
@router.put("/{board_id}/color-rules/{rule_id}", response_model=ColorRuleResponse)
def update_color_rule(
    board_id: str,
    rule_id: int,
    req: ColorRuleRequest,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.update_color_rule(board_id, rule_id, req.color, req.target_position, req.enabled)


# 색상 분류 rule을 비활성화한다.
@router.delete("/{board_id}/color-rules/{rule_id}", response_model=ColorRuleResponse)
def disable_color_rule(
    board_id: str,
    rule_id: int,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.disable_color_rule(board_id, rule_id)


# container conveyor 목표 속도를 변경한다.
@router.post("/{board_id}/commands/speed", response_model=CommandResponse)
async def set_speed(
    board_id: str,
    req: SpeedRequest,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return await service.set_speed(board_id, req.speed)


# container conveyor를 정방향으로 가동한다.
@router.post("/{board_id}/commands/forward", response_model=CommandResponse)
async def forward(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return await service.forward(board_id)


# container conveyor를 역방향으로 가동한다.
@router.post("/{board_id}/commands/reverse", response_model=CommandResponse)
async def reverse(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return await service.reverse(board_id)


# container conveyor를 정지한다.
@router.post("/{board_id}/commands/stop", response_model=CommandResponse)
async def stop(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return await service.stop(board_id)


# 지정 색상을 분류하도록 SORT_COLOR 명령을 전송한다.
@router.post("/{board_id}/commands/sort-color", response_model=CommandResponse)
async def sort_color(
    board_id: str,
    req: SortColorRequest,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return await service.sort_color(board_id, req.color)


# container conveyor 상태를 초기화한다.
@router.post("/{board_id}/commands/reset", response_model=CommandResponse)
async def reset(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return await service.reset(board_id)


# container conveyor 상태 동기화 명령을 전송한다.
@router.post("/{board_id}/commands/status-sync", response_model=CommandResponse)
async def status_sync(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return await service.status_sync(board_id)


# 비상정지 상태를 해제하는 명령을 전송한다.
@router.post("/{board_id}/commands/release-emergency-stop", response_model=CommandResponse)
async def release_emergency_stop(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return await service.release_emergency_stop(board_id)


# 특정 container conveyor 명령을 수동 timeout 처리한다.
@router.post("/{board_id}/commands/{command_id}/timeout", response_model=CommandHistoryResponse)
def timeout_command(
    board_id: str,
    command_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.timeout_command(board_id, command_id)


# timeout 기준을 초과한 container conveyor 명령을 timeout 처리한다.
@router.post("/{board_id}/commands/timeout-expired")
def timeout_expired_commands(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.timeout_expired_commands(board_id)


# heartbeat 기준으로 stale session 여부를 검사한다.
@router.post("/{board_id}/sessions/check-stale")
def check_stale_session(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.check_stale_session(board_id)


# container conveyor 운영 지표를 초기화한다.
@router.post("/{board_id}/metrics/reset", response_model=BoardMetricResponse)
def reset_metrics(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.reset_metrics(board_id)


# 색상별 누적 감지 수를 초기화한다.
@router.post("/{board_id}/colors/counts/reset", response_model=ColorCountsResponse)
def reset_color_counts(
    board_id: str,
    service: ContainerConveyorService = Depends(get_container_conveyor_service),
):
    return service.reset_color_counts(board_id)


def _control_key_for(board_id: str) -> str | None:
    expected_control_key = settings.DEVICE_CONTROL_KEY
    if settings.DEVICE_CONTROL_KEYS:
        try:
            expected_control_key = json.loads(settings.DEVICE_CONTROL_KEYS).get(board_id)
        except (TypeError, ValueError):
            expected_control_key = None

    return expected_control_key


async def _serve_board_session(
    websocket: WebSocket,
    board_id: str,
    session_id: str,
    service: ContainerConveyorService,
) -> None:
    try:
        while True:
            message = await websocket.receive_json()
            message.setdefault("board_id", board_id)
            if message.get("type") == "HELLO":
                if message.get("device_id", board_id) != board_id:
                    await websocket.close(code=1008, reason="device id mismatch")
                    service.unregister_board_session(board_id, websocket, "invalid_device_id")
                    return
                await websocket.send_json({
                    "type": "WELCOME",
                    "device_id": board_id,
                    "session_id": session_id,
                    "heartbeat_interval": settings.BOARD_HEARTBEAT_STALE_SECONDS,
                })
                continue
            service.handle_board_message(message)
    except WebSocketDisconnect:
        service.unregister_board_session(board_id, websocket)
    except Exception:
        service.unregister_board_session(board_id, websocket, "error")
        raise


# 등록된 ESP board가 WebSocket session으로 접속해 명령을 받고 상태/결과를 보고한다.
@ws_router.websocket("/ws/boards/{board_id}")
async def board_websocket(
    websocket: WebSocket,
    board_id: str,
    service: ContainerConveyorService = Depends(get_board_connection_service),
):
    expected_control_key = _control_key_for(board_id)
    if not expected_control_key or websocket.query_params.get("control_key") != expected_control_key:
        await websocket.close(code=1008, reason="invalid control key")
        return

    session_id = await service.register_board_session(board_id, websocket)
    await _serve_board_session(websocket, board_id, session_id, service)


# 서버에 식별자가 없는 ESP의 최초 등록과 첫 세션 연결을 처리한다.
@ws_router.websocket("/ws/devices/connect")
async def device_registration_websocket(
    websocket: WebSocket,
    db=Depends(get_db),
):
    provisioning_key = settings.DEVICE_PROVISIONING_KEY
    if not provisioning_key or websocket.query_params.get("provisioning_key") != provisioning_key:
        await websocket.close(code=1008, reason="invalid provisioning key")
        return

    await websocket.accept()
    try:
        hello = await websocket.receive_json()
        print(hello)
    except WebSocketDisconnect:
        return

    if hello.get("type") != "HELLO":
        await websocket.close(code=1008, reason="first message must be HELLO")
        return

    device_id = hello.get("device_id")
    device_type = hello.get("device_type")
    if not isinstance(device_id, str) or not device_id.strip() or len(device_id) > 64:
        await websocket.close(code=1008, reason="invalid device_id")
        return

    repository = ConveyorRepository(db)
    registration = DeviceRegistrationService(repository)
    try:
        result = registration.register(
            device_id=device_id,
            device_type=device_type,
            firmware_version=hello.get("firmware_version"),
            hardware_id=hello.get("hardware_id"),
        )
    except ValueError as exc:
        await websocket.close(code=1008, reason=str(exc))
        return

    service = ContainerConveyorService(repository, board_session_manager, expected_board_type=None)
    session_id = await service.register_board_session(device_id, websocket)
    await websocket.send_json({
        "type": "WELCOME",
        "device_id": result.device_id,
        "device_type": result.device_type,
        "session_id": session_id,
        "registered": result.created,
        "heartbeat_interval": settings.BOARD_HEARTBEAT_STALE_SECONDS,
    })
    await _serve_board_session(websocket, device_id, session_id, service)
