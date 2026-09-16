from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.sql import func

from app.infra.db.base import Base


AutoIncrementBigInteger = BigInteger().with_variant(Integer, "sqlite")


class ConveyorBoard(Base):
    __tablename__ = "conveyor_board"

    id = Column(String(64), primary_key=True)
    board_type = Column(String(32), nullable=False)
    name = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ConveyorBoardState(Base):
    __tablename__ = "conveyor_board_state"

    board_id = Column(String(64), ForeignKey("conveyor_board.id"), primary_key=True)
    connected = Column(Boolean, nullable=False, default=False)
    run_status = Column(String(32), nullable=False, default="DISCONNECTED")
    direction = Column(String(16), nullable=False, default="NONE")
    current_speed = Column(Integer, nullable=False, default=0)
    target_speed = Column(Integer, nullable=False, default=0)
    running = Column(Boolean, nullable=False, default=False)
    emergency_stopped = Column(Boolean, nullable=False, default=False)
    last_command_id = Column(String(64), nullable=True)
    last_error_message = Column(Text, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    state_updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ConveyorBoardMetric(Base):
    __tablename__ = "conveyor_board_metric"

    board_id = Column(String(64), ForeignKey("conveyor_board.id"), primary_key=True)
    total_run_seconds = Column(BigInteger, nullable=False, default=0)
    forward_run_seconds = Column(BigInteger, nullable=False, default=0)
    reverse_run_seconds = Column(BigInteger, nullable=False, default=0)
    command_count = Column(BigInteger, nullable=False, default=0)
    completed_command_count = Column(BigInteger, nullable=False, default=0)
    failed_command_count = Column(BigInteger, nullable=False, default=0)
    emergency_stop_count = Column(BigInteger, nullable=False, default=0)
    error_count = Column(BigInteger, nullable=False, default=0)
    last_run_started_at = Column(DateTime, nullable=True)
    last_run_stopped_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ConveyorSession(Base):
    __tablename__ = "conveyor_session"

    id = Column(String(64), primary_key=True)
    board_id = Column(String(64), ForeignKey("conveyor_board.id"), nullable=False, index=True)
    active = Column(Boolean, nullable=False, default=True)
    connected_at = Column(DateTime, nullable=False, server_default=func.now())
    disconnected_at = Column(DateTime, nullable=True)
    disconnect_reason = Column(String(255), nullable=True)
    last_ping_at = Column(DateTime, nullable=True)


class ConveyorCommand(Base):
    __tablename__ = "conveyor_command"

    id = Column(String(64), primary_key=True)
    board_id = Column(String(64), ForeignKey("conveyor_board.id"), nullable=False, index=True)
    command = Column(String(32), nullable=False)
    payload_json = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False)
    requested_at = Column(DateTime, nullable=False, server_default=func.now())
    sent_at = Column(DateTime, nullable=True)
    acked_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


class AgentInteractionLog(Base):
    """Audit trail for chat questions and user-initiated device actions."""

    __tablename__ = "agent_interaction_log"

    id = Column(AutoIncrementBigInteger, primary_key=True, autoincrement=True)
    interaction_type = Column(String(64), nullable=False, index=True)
    message = Column(Text, nullable=False)
    confirmed = Column(Boolean, nullable=True)
    status = Column(String(32), nullable=False, default="STARTED", index=True)
    tools_used_json = Column(JSON, nullable=False, default=list)
    command_ids_json = Column(JSON, nullable=False, default=list)
    response_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    completed_at = Column(DateTime, nullable=True)


class ConveyorEvent(Base):
    __tablename__ = "conveyor_event"

    id = Column(AutoIncrementBigInteger, primary_key=True, autoincrement=True)
    board_id = Column(String(64), ForeignKey("conveyor_board.id"), nullable=False, index=True)
    command_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False)
    event_payload_json = Column(JSON, nullable=False, default=dict)
    occurred_at = Column(DateTime, nullable=False, server_default=func.now())


class ContainerColorCount(Base):
    __tablename__ = "container_color_count"

    board_id = Column(String(64), ForeignKey("conveyor_board.id"), primary_key=True)
    color = Column(String(32), primary_key=True)
    count = Column(BigInteger, nullable=False, default=0)
    last_detected_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ContainerColorDetection(Base):
    __tablename__ = "container_color_detection"

    id = Column(AutoIncrementBigInteger, primary_key=True, autoincrement=True)
    board_id = Column(String(64), ForeignKey("conveyor_board.id"), nullable=False, index=True)
    color = Column(String(32), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=True)
    source = Column(String(32), nullable=False, default="ESP")
    detected_at = Column(DateTime, nullable=False, server_default=func.now())
    raw_payload_json = Column(JSON, nullable=False, default=dict)


class ContainerColorRule(Base):
    __tablename__ = "container_color_rule"

    id = Column(AutoIncrementBigInteger, primary_key=True, autoincrement=True)
    board_id = Column(String(64), ForeignKey("conveyor_board.id"), nullable=False, index=True)
    color = Column(String(32), nullable=False)
    target_position = Column(String(32), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class DeviceCapabilityModel(Base):
    __tablename__ = "device_capability"

    id = Column(AutoIncrementBigInteger, primary_key=True, autoincrement=True)
    board_id = Column(String(64), ForeignKey("conveyor_board.id"), nullable=False, index=True)
    capability_code = Column(String(64), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    commands_json = Column(JSON, nullable=False, default=list)
    payload_schema_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class OperationProfileModel(Base):
    __tablename__ = "operation_profile"

    code = Column(String(64), primary_key=True)
    operation_type = Column(String(64), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    allowed_commands_json = Column(JSON, nullable=False, default=list)
    capabilities_json = Column(JSON, nullable=False, default=list)
    safety_policy_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class DeviceProfileAssignmentModel(Base):
    __tablename__ = "device_profile_assignment"

    board_id = Column(String(64), ForeignKey("conveyor_board.id"), primary_key=True)
    profile_code = Column(String(64), ForeignKey("operation_profile.code"), nullable=False, index=True)
    assigned_at = Column(DateTime, nullable=False, server_default=func.now())
