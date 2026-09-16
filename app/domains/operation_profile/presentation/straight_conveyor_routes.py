from fastapi import APIRouter, Depends, Query

from app.api.dependent_manager import get_straight_conveyor_service, verify_control_api_key
from app.domains.control_contract.presentation.schemas import (
    BoardMetricResponse,
    BoardStatusResponse,
    CommandHistoryResponse,
    CommandResponse,
    DiagnosticsResponse,
    EventResponse,
    SpeedRequest,
)
from app.domains.operation_profile.application.straight_conveyor_service import StraightConveyorService


router = APIRouter(
    prefix="/api/straight-conveyors",
    tags=["straight-conveyors"],
    dependencies=[Depends(verify_control_api_key)],
)


# straight conveyor의 현재 상태를 조회한다.
@router.get("/{board_id}/status", response_model=BoardStatusResponse)
def get_status(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.get_status(board_id)


# straight conveyor의 운영 지표를 조회한다.
@router.get("/{board_id}/metrics", response_model=BoardMetricResponse)
def get_metrics(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.get_metrics(board_id)


# straight conveyor에서 발생한 이벤트 이력을 조회한다.
@router.get("/{board_id}/events", response_model=list[EventResponse])
def get_events(
    board_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.get_events(board_id, limit)


# straight conveyor에 요청된 명령 이력을 조회한다.
@router.get("/{board_id}/commands", response_model=list[CommandHistoryResponse])
def get_commands(
    board_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.get_commands(board_id, limit)


# 아직 완료되지 않은 straight conveyor 명령을 조회한다.
@router.get("/{board_id}/commands/pending", response_model=list[CommandHistoryResponse])
def get_pending_commands(
    board_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.get_pending_commands(board_id, limit)


# straight conveyor의 readiness 판단용 진단 정보를 조회한다.
@router.get("/{board_id}/diagnostics", response_model=DiagnosticsResponse)
def get_diagnostics(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.get_diagnostics(board_id)


# straight conveyor가 명령을 받을 수 있는 준비 상태인지 조회한다.
@router.get("/{board_id}/diagnostics/readiness")
def get_readiness(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.get_readiness(board_id)


# 상태 동기화를 위해 STATUS_SYNC 명령을 전송한다.
@router.post("/{board_id}/diagnostics/ping", response_model=CommandResponse)
async def diagnostics_ping(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return await service.diagnostics_ping(board_id)


# straight conveyor 목표 속도를 변경한다.
@router.post("/{board_id}/commands/speed", response_model=CommandResponse)
async def set_speed(
    board_id: str,
    req: SpeedRequest,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return await service.set_speed(board_id, req.speed)


# straight conveyor를 정방향으로 가동한다.
@router.post("/{board_id}/commands/forward", response_model=CommandResponse)
async def forward(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return await service.forward(board_id)


# straight conveyor를 역방향으로 가동한다.
@router.post("/{board_id}/commands/reverse", response_model=CommandResponse)
async def reverse(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return await service.reverse(board_id)


# straight conveyor를 정지한다.
@router.post("/{board_id}/commands/stop", response_model=CommandResponse)
async def stop(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return await service.stop(board_id)


# straight conveyor 상태를 초기화한다.
@router.post("/{board_id}/commands/reset", response_model=CommandResponse)
async def reset(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return await service.reset(board_id)


# straight conveyor 상태 동기화 명령을 전송한다.
@router.post("/{board_id}/commands/status-sync", response_model=CommandResponse)
async def status_sync(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return await service.status_sync(board_id)


# 비상정지 상태를 해제하는 명령을 전송한다.
@router.post("/{board_id}/commands/release-emergency-stop", response_model=CommandResponse)
async def release_emergency_stop(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return await service.release_emergency_stop(board_id)


# 특정 straight conveyor 명령을 수동 timeout 처리한다.
@router.post("/{board_id}/commands/{command_id}/timeout", response_model=CommandHistoryResponse)
def timeout_command(
    board_id: str,
    command_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.timeout_command(board_id, command_id)


# timeout 기준을 초과한 straight conveyor 명령을 timeout 처리한다.
@router.post("/{board_id}/commands/timeout-expired")
def timeout_expired_commands(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.timeout_expired_commands(board_id)


# heartbeat 기준으로 stale session 여부를 검사한다.
@router.post("/{board_id}/sessions/check-stale")
def check_stale_session(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.check_stale_session(board_id)


# straight conveyor 운영 지표를 초기화한다.
@router.post("/{board_id}/metrics/reset", response_model=BoardMetricResponse)
def reset_metrics(
    board_id: str,
    service: StraightConveyorService = Depends(get_straight_conveyor_service),
):
    return service.reset_metrics(board_id)
