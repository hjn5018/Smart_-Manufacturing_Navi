from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependent_manager import verify_control_api_key
from app.domains.control_contract.presentation.schemas import (
    DeviceProfileResponse,
    OperationProfileResponse,
    OperationProfileUpsertRequest,
    ProfileAssignmentRequest,
    ProfileAssignmentResponse,
)
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository
from app.domains.operation_profile.application.profile_service import OperationProfileService
from app.infra.db.session import get_db


router = APIRouter(
    prefix="/api/operation-profiles",
    tags=["operation-profiles"],
    dependencies=[Depends(verify_control_api_key)],
)


def get_profile_service(db=Depends(get_db)):
    return OperationProfileService(ConveyorRepository(db))


# 등록된 operation profile 목록을 조회한다.
@router.get("", response_model=list[OperationProfileResponse])
def list_operation_profiles(service: OperationProfileService = Depends(get_profile_service)):
    return service.list_profiles()


# profile code로 operation profile 상세 정의를 조회한다.
@router.get("/{profile_code}", response_model=OperationProfileResponse)
def get_operation_profile(
    profile_code: str,
    service: OperationProfileService = Depends(get_profile_service),
):
    row = service.get_profile(profile_code)
    if row is None:
        raise HTTPException(status_code=404, detail="Operation profile not found")
    return row


# operation profile을 새로 등록하거나 기존 정의를 수정한다.
@router.put("/{profile_code}", response_model=OperationProfileResponse)
def upsert_operation_profile(
    profile_code: str,
    req: OperationProfileUpsertRequest,
    service: OperationProfileService = Depends(get_profile_service),
):
    if req.code != profile_code:
        raise HTTPException(status_code=400, detail="profile code does not match path")
    return service.upsert_profile(
        code=profile_code,
        operation_type=req.operation_type,
        allowed_commands=req.allowed_commands,
        capabilities=req.capabilities,
        enabled=req.enabled,
        safety_policy=req.safety_policy,
    )


# device에 현재 할당된 operation profile을 조회한다.
@router.get("/devices/{device_id}/assignment", response_model=DeviceProfileResponse)
def get_device_profile_assignment(
    device_id: str,
    service: OperationProfileService = Depends(get_profile_service),
):
    try:
        row = service.get_device_profile(device_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Device profile assignment not found")
    return _device_profile_response(device_id, row)


# device가 사용할 operation profile을 변경한다.
@router.put("/devices/{device_id}/assignment", response_model=ProfileAssignmentResponse)
def assign_device_profile(
    device_id: str,
    req: ProfileAssignmentRequest,
    service: OperationProfileService = Depends(get_profile_service),
):
    try:
        return service.assign_profile(device_id, req.profile_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _device_profile_response(device_id: str, row) -> dict:
    return {
        "device_id": device_id,
        "profile_code": row.code,
        "operation_type": row.operation_type,
        "allowed_commands": row.allowed_commands_json or [],
        "capabilities": row.capabilities_json or [],
    }
