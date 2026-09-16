from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependent_manager import verify_control_api_key
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository
from app.domains.control_contract.presentation.schemas import BoardMetricResponse, EventResponse
from app.domains.operation_event.application.event_metric_service import EventMetricService
from app.infra.db.session import get_db


router = APIRouter(
    prefix="/api/operation-events",
    tags=["operation-events"],
    dependencies=[Depends(verify_control_api_key)],
)


def get_event_metric_service(db=Depends(get_db)):
    return EventMetricService(ConveyorRepository(db))


# device에서 발생한 이벤트 이력을 조회한다.
@router.get("/devices/{device_id}/events", response_model=list[EventResponse])
def list_device_events(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: EventMetricService = Depends(get_event_metric_service),
):
    try:
        return service.list_events(device_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# device의 누적 가동 시간, 명령 수, 오류 수 같은 운영 지표를 조회한다.
@router.get("/devices/{device_id}/metrics", response_model=BoardMetricResponse)
def get_device_metrics(
    device_id: str,
    service: EventMetricService = Depends(get_event_metric_service),
):
    try:
        row = service.get_metrics(device_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Device metric not found")
    return row


# device의 운영 지표를 초기화하고 초기화 이벤트를 기록한다.
@router.post("/devices/{device_id}/metrics/reset", response_model=BoardMetricResponse)
def reset_device_metrics(
    device_id: str,
    service: EventMetricService = Depends(get_event_metric_service),
):
    try:
        row = service.reset_metrics(device_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Device metric not found")
    return row
