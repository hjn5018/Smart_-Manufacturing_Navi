from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependent_manager import verify_control_api_key
from app.domains.capability_management.application.capability_service import CapabilityManagementService
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository
from app.domains.control_contract.presentation.schemas import CapabilityResponse, CapabilityUpsertRequest
from app.infra.db.session import get_db


router = APIRouter(
    prefix="/api/capabilities",
    tags=["capabilities"],
    dependencies=[Depends(verify_control_api_key)],
)


def get_capability_service(db=Depends(get_db)):
    return CapabilityManagementService(ConveyorRepository(db))


# device에 등록된 모든 capability를 조회한다.
@router.get("/devices/{device_id}", response_model=list[CapabilityResponse])
def list_device_capabilities(
    device_id: str,
    service: CapabilityManagementService = Depends(get_capability_service),
):
    try:
        return [_to_response(row) for row in service.list_capabilities(device_id)]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# device에 등록된 특정 capability를 조회한다.
@router.get("/devices/{device_id}/{capability_code}", response_model=CapabilityResponse)
def get_device_capability(
    device_id: str,
    capability_code: str,
    service: CapabilityManagementService = Depends(get_capability_service),
):
    try:
        row = service.get_capability(device_id, capability_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Device capability not found")
    return _to_response(row)


# device에 capability를 새로 등록하거나 기존 정의를 수정한다.
@router.put("/devices/{device_id}/{capability_code}", response_model=CapabilityResponse)
def upsert_device_capability(
    device_id: str,
    capability_code: str,
    req: CapabilityUpsertRequest,
    service: CapabilityManagementService = Depends(get_capability_service),
):
    if req.capability_code != capability_code:
        raise HTTPException(status_code=400, detail="capability_code does not match path")
    try:
        row = service.upsert_capability(
            device_id=device_id,
            capability_code=capability_code,
            commands=req.commands,
            payload_schema=req.payload_schema,
            enabled=req.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(row)


# device capability를 활성화해서 명령 실행 가능 상태로 만든다.
@router.post("/devices/{device_id}/{capability_code}/enable", response_model=CapabilityResponse)
def enable_device_capability(
    device_id: str,
    capability_code: str,
    service: CapabilityManagementService = Depends(get_capability_service),
):
    return _set_enabled(service, device_id, capability_code, True)


# device capability를 비활성화해서 명령 실행 대상에서 제외한다.
@router.post("/devices/{device_id}/{capability_code}/disable", response_model=CapabilityResponse)
def disable_device_capability(
    device_id: str,
    capability_code: str,
    service: CapabilityManagementService = Depends(get_capability_service),
):
    return _set_enabled(service, device_id, capability_code, False)


def _set_enabled(
    service: CapabilityManagementService,
    device_id: str,
    capability_code: str,
    enabled: bool,
):
    try:
        row = service.set_enabled(device_id, capability_code, enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Device capability not found")
    return _to_response(row)


def _to_response(row) -> dict:
    return {
        "id": row.id,
        "board_id": row.board_id,
        "capability_code": row.capability_code,
        "code": row.capability_code,
        "enabled": row.enabled,
        "commands": row.commands_json or [],
        "payload_schema": row.payload_schema_json or {},
    }
