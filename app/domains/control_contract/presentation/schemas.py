from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domains.control_contract.domain.enums import ColorType


class SpeedRequest(BaseModel):
    speed: int = Field(ge=0, le=255)


class GenericCommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = Field(default=None, max_length=128)


class GenericCapabilityCommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = Field(default=None, max_length=128)


class SortColorRequest(BaseModel):
    color: ColorType


class ColorRuleRequest(BaseModel):
    color: ColorType
    target_position: str = Field(min_length=1, max_length=32)
    enabled: bool = True


class ColorRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    board_id: str
    color: str
    target_position: str
    enabled: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CommandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    command_id: str
    board_id: str
    command: str
    status: str


class BoardStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    board_id: str
    board_type: str
    name: str
    connected: bool
    run_status: str
    direction: str
    current_speed: int
    target_speed: int
    running: bool
    emergency_stopped: bool
    last_command_id: str | None = None
    last_error_message: str | None = None
    last_seen_at: datetime | None = None
    state_updated_at: datetime | None = None


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    board_type: str
    name: str
    enabled: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BoardMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    board_id: str
    total_run_seconds: int
    forward_run_seconds: int
    reverse_run_seconds: int
    command_count: int
    completed_command_count: int
    failed_command_count: int
    emergency_stop_count: int
    error_count: int
    last_run_started_at: datetime | None = None
    last_run_stopped_at: datetime | None = None
    updated_at: datetime | None = None


class ColorCountItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    color: str
    count: int
    last_detected_at: datetime | None = None


class ColorCountsResponse(BaseModel):
    board_id: str
    counts: list[ColorCountItem]


class DetectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    board_id: str
    color: str
    confidence: float | None = None
    source: str
    detected_at: datetime | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    board_id: str
    command_id: str | None = None
    event_type: str
    event_payload_json: dict[str, Any]
    occurred_at: datetime | None = None


class CommandHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    board_id: str
    command: str
    payload_json: dict[str, Any]
    status: str
    requested_at: datetime | None = None
    sent_at: datetime | None = None
    acked_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class DiagnosticsResponse(BaseModel):
    board_id: str
    ready: bool
    connected: bool
    run_status: str | None = None
    last_seen_at: datetime | None = None
    last_ping_at: datetime | None = None
    pending_command_count: int
    last_command_id: str | None = None
    last_error_message: str | None = None
    emergency_stopped: bool
    checks: dict[str, bool]


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    board_id: str
    active: bool
    connected_at: datetime | None = None
    disconnected_at: datetime | None = None
    disconnect_reason: str | None = None
    last_ping_at: datetime | None = None


class ConnectedDeviceResponse(BaseModel):
    id: str
    board_type: str
    name: str
    session_id: str
    connected: bool
    connected_at: datetime | None = None
    last_heartbeat_at: datetime | None = None


class CapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    board_id: str | None = None
    capability_code: str | None = None
    code: str
    enabled: bool
    commands: list[str]
    payload_schema: dict[str, Any] = Field(default_factory=dict)


class CapabilityUpsertRequest(BaseModel):
    capability_code: str = Field(min_length=1, max_length=64)
    commands: list[str] = Field(default_factory=list)
    payload_schema: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class DeviceProfileResponse(BaseModel):
    device_id: str
    profile_code: str
    operation_type: str
    allowed_commands: list[str]
    capabilities: list[str]


class OperationProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    operation_type: str
    enabled: bool
    allowed_commands_json: list[str]
    capabilities_json: list[str]
    safety_policy_json: dict[str, Any]


class OperationProfileUpsertRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    operation_type: str = Field(min_length=1, max_length=64)
    allowed_commands: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    enabled: bool = True
    safety_policy: dict[str, Any] = Field(default_factory=dict)


class ProfileAssignmentRequest(BaseModel):
    profile_code: str = Field(min_length=1, max_length=64)


class ProfileAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    board_id: str
    profile_code: str
    assigned_at: datetime | None = None
