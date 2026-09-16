from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.domains.control_contract.infrastructure.sqlalchemy_models import (
    AgentInteractionLog,
    ContainerColorCount,
    ContainerColorDetection,
    ContainerColorRule,
    ConveyorBoard,
    ConveyorBoardMetric,
    ConveyorBoardState,
    ConveyorCommand,
    ConveyorEvent,
    ConveyorSession,
    DeviceCapabilityModel,
    DeviceProfileAssignmentModel,
    OperationProfileModel,
)


class ConveyorRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_boards(self) -> list[ConveyorBoard]:
        return self.db.query(ConveyorBoard).order_by(ConveyorBoard.id.asc()).all()

    def find_board(self, board_id: str) -> ConveyorBoard | None:
        return self.db.get(ConveyorBoard, board_id)

    def find_state(self, board_id: str) -> ConveyorBoardState | None:
        return self.db.get(ConveyorBoardState, board_id)

    def find_metric(self, board_id: str) -> ConveyorBoardMetric | None:
        return self.db.get(ConveyorBoardMetric, board_id)

    def find_color_rule(self, rule_id: int) -> ContainerColorRule | None:
        return self.db.get(ContainerColorRule, rule_id)

    def create_agent_interaction(
        self,
        interaction_type: str,
        message: str,
        confirmed: bool | None = None,
    ) -> AgentInteractionLog:
        row = AgentInteractionLog(
            interaction_type=interaction_type,
            message=message,
            confirmed=confirmed,
            status="STARTED",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def complete_agent_interaction(
        self,
        interaction_id: int,
        *,
        status: str,
        tools_used: list[str] | None = None,
        command_ids: list[str] | None = None,
        response_text: str | None = None,
        error_message: str | None = None,
    ) -> None:
        row = self.db.get(AgentInteractionLog, interaction_id)
        if row is None:
            return
        row.status = status
        row.tools_used_json = tools_used or []
        row.command_ids_json = command_ids or []
        row.response_text = response_text
        row.error_message = error_message
        row.completed_at = datetime.utcnow()
        self.db.commit()

    def list_agent_interactions(self, limit: int = 100) -> list[AgentInteractionLog]:
        return (
            self.db.query(AgentInteractionLog)
            .order_by(AgentInteractionLog.id.desc())
            .limit(limit)
            .all()
        )

    def find_active_session(self, board_id: str) -> ConveyorSession | None:
        return (
            self.db.query(ConveyorSession)
            .filter(ConveyorSession.board_id == board_id, ConveyorSession.active.is_(True))
            .order_by(ConveyorSession.connected_at.desc())
            .first()
        )

    def list_sessions(self, board_id: str, limit: int = 50) -> list[ConveyorSession]:
        return (
            self.db.query(ConveyorSession)
            .filter(ConveyorSession.board_id == board_id)
            .order_by(ConveyorSession.connected_at.desc())
            .limit(limit)
            .all()
        )

    def ensure_container_board(self, board_id: str = "container-01") -> ConveyorBoard:
        board = self.ensure_board(
            board_id=board_id,
            board_type="CONTAINER_CONVEYOR",
            name="색상 분류 컨테이너",
        )
        for color in ("RED", "GREEN", "BLUE", "UNKNOWN"):
            if self.db.get(ContainerColorCount, {"board_id": board_id, "color": color}) is None:
                self.db.add(ContainerColorCount(board_id=board_id, color=color))
        self.db.commit()
        self.ensure_operation_profile(
            code="classification-transfer",
            operation_type="CLASSIFICATION",
            allowed_commands=[
                "SET_SPEED",
                "FORWARD",
                "REVERSE",
                "STOP",
                "RESET",
                "STATUS_SYNC",
                "RELEASE_EMERGENCY_STOP",
                "SORT_COLOR",
            ],
            capabilities=["COLOR_CLASSIFICATION"],
        )
        self.assign_operation_profile(board_id, "classification-transfer")
        self.ensure_device_capability(
            board_id=board_id,
            capability_code="COLOR_CLASSIFICATION",
            commands=["SORT_COLOR"],
            payload_schema={"required": ["color"], "properties": {"color": {"type": "string"}}},
        )
        return board

    def ensure_straight_board(self, board_id: str = "straight-01") -> ConveyorBoard:
        board = self.ensure_board(
            board_id=board_id,
            board_type="STRAIGHT_CONVEYOR",
            name="일반 1자형 컨베이어",
        )
        self.ensure_operation_profile(
            code="simple-transfer",
            operation_type="SIMPLE_TRANSFER",
            allowed_commands=[
                "SET_SPEED",
                "FORWARD",
                "REVERSE",
                "STOP",
                "RESET",
                "STATUS_SYNC",
                "RELEASE_EMERGENCY_STOP",
            ],
            capabilities=[],
        )
        self.assign_operation_profile(board_id, "simple-transfer")
        return board

    def ensure_board(self, board_id: str, board_type: str, name: str) -> ConveyorBoard:
        board = self.find_board(board_id)
        if board is None:
            board = ConveyorBoard(
                id=board_id,
                board_type=board_type,
                name=name,
                enabled=True,
            )
            self.db.add(board)
        else:
            board.board_type = board_type
            board.name = name
            board.enabled = True
        if self.find_state(board_id) is None:
            self.db.add(ConveyorBoardState(board_id=board_id))
        if self.find_metric(board_id) is None:
            self.db.add(ConveyorBoardMetric(board_id=board_id))
        self.db.commit()
        return board

    def create_command(self, command_id: str, board_id: str, command: str, payload: dict[str, Any]) -> ConveyorCommand:
        row = ConveyorCommand(
            id=command_id,
            board_id=board_id,
            command=command,
            payload_json=payload,
            status="REQUESTED",
        )
        self.db.add(row)
        metric = self.find_metric(board_id)
        if metric is not None:
            metric.command_count = (metric.command_count or 0) + 1
        self.db.commit()
        self.db.refresh(row)
        return row

    def mark_command_sent(self, command_id: str) -> None:
        row = self.db.get(ConveyorCommand, command_id)
        if row is not None:
            row.status = "SENT"
            row.sent_at = datetime.utcnow()
            self.db.commit()

    def mark_command_acked(self, command_id: str) -> None:
        row = self.db.get(ConveyorCommand, command_id)
        if row is not None:
            row.status = "ACKED"
            row.acked_at = datetime.utcnow()
            self.db.commit()

    def mark_command_completed(self, command_id: str) -> ConveyorCommand | None:
        row = self.db.get(ConveyorCommand, command_id)
        if row is not None:
            row.status = "COMPLETED"
            row.completed_at = datetime.utcnow()
            metric = self.find_metric(row.board_id)
            if metric is not None:
                metric.completed_command_count = (metric.completed_command_count or 0) + 1
            self.db.commit()
        return row

    def mark_command_failed(self, command_id: str, error_message: str | None = None, status: str = "FAILED") -> ConveyorCommand | None:
        row = self.db.get(ConveyorCommand, command_id)
        if row is not None:
            row.status = status
            row.completed_at = datetime.utcnow()
            row.error_message = error_message
            metric = self.find_metric(row.board_id)
            if metric is not None:
                metric.failed_command_count = (metric.failed_command_count or 0) + 1
            self.db.commit()
        return row

    def create_session(self, session_id: str, board_id: str) -> ConveyorSession:
        self.deactivate_sessions(board_id, "reconnected", commit=False)
        row = ConveyorSession(id=session_id, board_id=board_id, active=True)
        self.db.add(row)
        self.update_connection_state(board_id, True, "IDLE", commit=False)
        self.create_event(board_id, "CONNECTED", {"session_id": session_id}, commit=False)
        self.db.commit()
        self.db.refresh(row)
        return row

    def deactivate_sessions(self, board_id: str, reason: str, commit: bool = True) -> None:
        rows = (
            self.db.query(ConveyorSession)
            .filter(ConveyorSession.board_id == board_id, ConveyorSession.active.is_(True))
            .all()
        )
        for row in rows:
            row.active = False
            row.disconnected_at = datetime.utcnow()
            row.disconnect_reason = reason
        if commit:
            self.db.commit()

    def disconnect_board(self, board_id: str, reason: str = "disconnected") -> None:
        self.close_run_period(board_id, datetime.utcnow(), commit=False)
        self.deactivate_sessions(board_id, reason, commit=False)
        self.update_connection_state(board_id, False, "DISCONNECTED", commit=False)
        state = self.find_state(board_id)
        if state is not None:
            state.running = False
            state.direction = "NONE"
            state.current_speed = 0
        self.create_event(board_id, "DISCONNECTED", {"reason": reason}, commit=False)
        self.db.commit()

    def update_connection_state(self, board_id: str, connected: bool, run_status: str, commit: bool = True) -> None:
        state = self.find_state(board_id)
        if state is not None:
            state.connected = connected
            state.run_status = run_status
            state.last_seen_at = datetime.utcnow()
            state.state_updated_at = datetime.utcnow()
        if commit:
            self.db.commit()

    def update_runtime_state(self, board_id: str, state_payload: dict[str, Any], command_id: str | None = None) -> None:
        state = self.find_state(board_id)
        if state is None:
            return
        state.last_command_id = command_id or state.last_command_id
        state.last_seen_at = datetime.utcnow()
        state.state_updated_at = datetime.utcnow()
        state.run_status = state_payload.get("run_status") or state_payload.get("status") or state.run_status
        state.direction = state_payload.get("direction", state.direction)
        state.current_speed = state_payload.get("current_speed", state.current_speed)
        state.target_speed = state_payload.get("target_speed", state.target_speed)
        state.running = state_payload.get("running", state.running)
        state.emergency_stopped = state_payload.get("emergency_stopped", state.emergency_stopped)
        self.db.commit()

    def apply_completed_command(self, command: ConveyorCommand, result_state: dict[str, Any] | None = None) -> None:
        now = datetime.utcnow()
        state = self.find_state(command.board_id)
        if state is None:
            return
        payload = command.payload_json or {}
        result_state = result_state or {}
        if command.command == "SET_SPEED":
            speed = result_state.get("current_speed", payload.get("speed", state.current_speed))
            state.current_speed = speed
            state.target_speed = payload.get("speed", speed)
            self.create_event(command.board_id, "SPEED_CHANGED", {"speed": speed}, command.id, commit=False)
        elif command.command in ("START", "FORWARD", "REVERSE"):
            direction = "FORWARD" if command.command == "START" else command.command
            state.direction = direction
            state.running = True
            state.run_status = "RUNNING"
            self.start_run_period(command.board_id, now, commit=False)
            self.create_event(command.board_id, "RUN_STARTED", {"direction": direction}, command.id, commit=False)
            self.create_event(command.board_id, "DIRECTION_CHANGED", {"direction": direction}, command.id, commit=False)
        elif command.command == "STOP":
            self.close_run_period(command.board_id, now, commit=False)
            state.running = False
            state.run_status = "STOPPED"
            state.current_speed = result_state.get("current_speed", 0)
            self.create_event(command.board_id, "RUN_STOPPED", {}, command.id, commit=False)
        elif command.command == "EMERGENCY_STOP":
            self.close_run_period(command.board_id, now, commit=False)
            state.running = False
            state.run_status = "EMERGENCY_STOPPED"
            state.direction = "NONE"
            state.current_speed = 0
            state.emergency_stopped = True
            metric = self.find_metric(command.board_id)
            if metric is not None:
                metric.emergency_stop_count = (metric.emergency_stop_count or 0) + 1
            self.create_event(command.board_id, "EMERGENCY_STOP", {}, command.id, commit=False)
        elif command.command == "SORT_COLOR":
            self.create_event(command.board_id, "COLOR_SORT_REQUESTED", payload, command.id, commit=False)
        elif command.command == "SET_COLOR":
            self.create_event(command.board_id, "COLOR_TARGET_CHANGED", payload, command.id, commit=False)
        elif command.command == "RETURN_HOME":
            state.running = True
            state.run_status = "RETURNING"
            self.create_event(command.board_id, "RETURN_HOME_REQUESTED", {}, command.id, commit=False)
        elif command.command == "BOX_ACTION":
            self.create_event(command.board_id, "BOX_ACTION_REQUESTED", {}, command.id, commit=False)
        elif command.command == "RESET":
            self.close_run_period(command.board_id, now, commit=False)
            state.running = False
            state.run_status = "IDLE"
            state.direction = "NONE"
            state.current_speed = 0
            state.target_speed = 0
            state.emergency_stopped = False
            state.last_error_message = None
            self.create_event(command.board_id, "RESET_COMPLETED", {}, command.id, commit=False)
        elif command.command == "STATUS_SYNC":
            self.create_event(command.board_id, "STATUS_SYNC_COMPLETED", result_state, command.id, commit=False)
        elif command.command == "RELEASE_EMERGENCY_STOP":
            state.running = False
            state.run_status = "IDLE"
            state.direction = "NONE"
            state.current_speed = 0
            state.emergency_stopped = False
            state.last_error_message = None
            self.create_event(command.board_id, "EMERGENCY_RELEASED", {}, command.id, commit=False)
        state.last_command_id = command.id
        state.last_seen_at = now
        state.state_updated_at = now
        self.db.commit()

    def apply_emergency_stop(self, board_id: str, error_message: str | None, payload: dict[str, Any]) -> None:
        now = datetime.utcnow()
        self.close_run_period(board_id, now, commit=False)
        state = self.find_state(board_id)
        if state is not None:
            state.running = False
            state.run_status = "EMERGENCY_STOPPED"
            state.direction = "NONE"
            state.current_speed = 0
            state.emergency_stopped = True
            state.last_error_message = error_message
            state.last_seen_at = now
            state.state_updated_at = now
        metric = self.find_metric(board_id)
        if metric is not None:
            metric.emergency_stop_count = (metric.emergency_stop_count or 0) + 1
            metric.error_count = (metric.error_count or 0) + 1
        self.create_event(board_id, "EMERGENCY_STOP", {"error_message": error_message, "payload": payload}, commit=False)
        self.db.commit()

    def record_color_detected(self, board_id: str, color: str, confidence: float | None, raw_payload: dict[str, Any]) -> None:
        detected_at = datetime.utcnow()
        self.db.add(
            ContainerColorDetection(
                board_id=board_id,
                color=color,
                confidence=confidence,
                source="ESP",
                detected_at=detected_at,
                raw_payload_json=raw_payload,
            )
        )
        count = self.db.get(ContainerColorCount, {"board_id": board_id, "color": color})
        if count is None:
            count = ContainerColorCount(board_id=board_id, color=color, count=0)
            self.db.add(count)
        count.count = (count.count or 0) + 1
        count.last_detected_at = detected_at
        self.create_event(board_id, "COLOR_DETECTED", raw_payload, commit=False)
        state = self.find_state(board_id)
        if state is not None:
            state.last_seen_at = detected_at
            state.state_updated_at = detected_at
        self.db.commit()

    def record_heartbeat(self, board_id: str) -> None:
        now = datetime.utcnow()
        rows = (
            self.db.query(ConveyorSession)
            .filter(ConveyorSession.board_id == board_id, ConveyorSession.active.is_(True))
            .all()
        )
        if not rows:
            return
        state = self.find_state(board_id)
        if state is not None:
            state.connected = True
            state.last_seen_at = now
            state.state_updated_at = now
        for row in rows:
            row.last_ping_at = now
        self.db.commit()

    def mark_stale_if_needed(self, board_id: str, stale_after_seconds: int, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        state = self.find_state(board_id)
        if state is None or state.last_seen_at is None:
            return False
        elapsed = (now - state.last_seen_at).total_seconds()
        if elapsed <= stale_after_seconds:
            return False
        state.run_status = "ERROR"
        state.connected = False
        state.state_updated_at = now
        self.deactivate_sessions(board_id, "stale", commit=False)
        self.create_event(
            board_id,
            "ERROR_OCCURRED",
            {"message": "board heartbeat is stale", "elapsed_seconds": elapsed},
            commit=False,
        )
        self.db.commit()
        return True

    def list_pending_commands(self, board_id: str, limit: int = 50) -> list[ConveyorCommand]:
        return (
            self.db.query(ConveyorCommand)
            .filter(
                ConveyorCommand.board_id == board_id,
                ConveyorCommand.status.in_(["REQUESTED", "SENT", "ACKED"]),
            )
            .order_by(ConveyorCommand.requested_at.asc())
            .limit(limit)
            .all()
        )

    def count_pending_commands(self, board_id: str) -> int:
        return (
            self.db.query(ConveyorCommand)
            .filter(
                ConveyorCommand.board_id == board_id,
                ConveyorCommand.status.in_(["REQUESTED", "SENT", "ACKED"]),
            )
            .count()
        )

    def has_pending_timeout(self, board_id: str, ack_timeout_seconds: int, result_timeout_seconds: int) -> bool:
        now = datetime.utcnow()
        for row in self.list_pending_commands(board_id, limit=1000):
            if row.status == "SENT" and row.sent_at and (now - row.sent_at).total_seconds() > ack_timeout_seconds:
                return True
            if row.status == "ACKED" and row.acked_at and (now - row.acked_at).total_seconds() > result_timeout_seconds:
                return True
        return False

    def timeout_command(self, board_id: str, command_id: str, reason: str = "manual timeout") -> ConveyorCommand | None:
        row = self.db.get(ConveyorCommand, command_id)
        if row is None or row.board_id != board_id:
            return None
        if row.status not in ("REQUESTED", "SENT", "ACKED"):
            return row
        row.status = "TIMEOUT"
        row.completed_at = datetime.utcnow()
        row.error_message = reason
        metric = self.find_metric(board_id)
        if metric is not None:
            metric.failed_command_count = (metric.failed_command_count or 0) + 1
        self.create_event(board_id, "ERROR_OCCURRED", {"command_id": command_id, "reason": reason}, command_id, commit=False)
        self.db.commit()
        return row

    def timeout_expired_commands(self, board_id: str, ack_timeout_seconds: int, result_timeout_seconds: int) -> int:
        now = datetime.utcnow()
        count = 0
        pending = self.list_pending_commands(board_id, limit=1000)
        for row in pending:
            if row.status == "SENT" and row.sent_at and (now - row.sent_at).total_seconds() > ack_timeout_seconds:
                self.timeout_command(board_id, row.id, "ack timeout")
                count += 1
            elif row.status == "ACKED" and row.acked_at and (now - row.acked_at).total_seconds() > result_timeout_seconds:
                self.timeout_command(board_id, row.id, "result timeout")
                count += 1
        return count

    def reset_metrics(self, board_id: str) -> ConveyorBoardMetric | None:
        metric = self.find_metric(board_id)
        if metric is None:
            return None
        metric.total_run_seconds = 0
        metric.forward_run_seconds = 0
        metric.reverse_run_seconds = 0
        metric.command_count = 0
        metric.completed_command_count = 0
        metric.failed_command_count = 0
        metric.emergency_stop_count = 0
        metric.error_count = 0
        metric.last_run_started_at = None
        metric.last_run_stopped_at = None
        self.create_event(board_id, "METRICS_RESET", {}, commit=False)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    def reset_color_counts(self, board_id: str) -> list[ContainerColorCount]:
        rows = self.list_color_counts(board_id)
        now = datetime.utcnow()
        for row in rows:
            row.count = 0
            row.last_detected_at = None
            row.updated_at = now
        self.create_event(board_id, "COLOR_COUNTS_RESET", {}, commit=False)
        self.db.commit()
        return rows

    def list_color_rules(self, board_id: str) -> list[ContainerColorRule]:
        return (
            self.db.query(ContainerColorRule)
            .filter(ContainerColorRule.board_id == board_id)
            .order_by(ContainerColorRule.color.asc(), ContainerColorRule.id.asc())
            .all()
        )

    def find_enabled_color_rule(self, board_id: str, color: str) -> ContainerColorRule | None:
        return (
            self.db.query(ContainerColorRule)
            .filter(
                ContainerColorRule.board_id == board_id,
                ContainerColorRule.color == color,
                ContainerColorRule.enabled.is_(True),
            )
            .order_by(ContainerColorRule.id.desc())
            .first()
        )

    def create_color_rule(self, board_id: str, color: str, target_position: str, enabled: bool) -> ContainerColorRule:
        row = ContainerColorRule(
            board_id=board_id,
            color=color,
            target_position=target_position,
            enabled=enabled,
        )
        self.db.add(row)
        self.create_event(
            board_id,
            "COLOR_RULE_CREATED",
            {"color": color, "target_position": target_position, "enabled": enabled},
            commit=False,
        )
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_color_rule(self, board_id: str, rule_id: int, color: str, target_position: str, enabled: bool) -> ContainerColorRule | None:
        row = self.find_color_rule(rule_id)
        if row is None or row.board_id != board_id:
            return None
        row.color = color
        row.target_position = target_position
        row.enabled = enabled
        self.create_event(
            board_id,
            "COLOR_RULE_UPDATED",
            {"rule_id": rule_id, "color": color, "target_position": target_position, "enabled": enabled},
            commit=False,
        )
        self.db.commit()
        self.db.refresh(row)
        return row

    def disable_color_rule(self, board_id: str, rule_id: int) -> ContainerColorRule | None:
        row = self.find_color_rule(rule_id)
        if row is None or row.board_id != board_id:
            return None
        row.enabled = False
        self.create_event(board_id, "COLOR_RULE_DISABLED", {"rule_id": rule_id}, commit=False)
        self.db.commit()
        self.db.refresh(row)
        return row

    def start_run_period(self, board_id: str, started_at: datetime, commit: bool = True) -> None:
        metric = self.find_metric(board_id)
        if metric is not None and metric.last_run_started_at is None:
            metric.last_run_started_at = started_at
        if commit:
            self.db.commit()

    def close_run_period(self, board_id: str, stopped_at: datetime, commit: bool = True) -> None:
        metric = self.find_metric(board_id)
        state = self.find_state(board_id)
        if metric is not None and state is not None and metric.last_run_started_at is not None:
            seconds = max(0, int((stopped_at - metric.last_run_started_at).total_seconds()))
            metric.total_run_seconds = (metric.total_run_seconds or 0) + seconds
            if state.direction == "FORWARD":
                metric.forward_run_seconds = (metric.forward_run_seconds or 0) + seconds
            elif state.direction == "REVERSE":
                metric.reverse_run_seconds = (metric.reverse_run_seconds or 0) + seconds
            metric.last_run_started_at = None
            metric.last_run_stopped_at = stopped_at
        if commit:
            self.db.commit()

    def create_event(
        self,
        board_id: str,
        event_type: str,
        payload: dict[str, Any],
        command_id: str | None = None,
        commit: bool = True,
    ) -> None:
        self.db.add(
            ConveyorEvent(
                board_id=board_id,
                command_id=command_id,
                event_type=event_type,
                event_payload_json=payload,
            )
        )
        print("create_event 진입")
        if commit:
            self.db.commit()

    def list_operation_profiles(self) -> list[OperationProfileModel]:
        return self.db.query(OperationProfileModel).order_by(OperationProfileModel.code.asc()).all()

    def find_operation_profile(self, code: str) -> OperationProfileModel | None:
        return self.db.get(OperationProfileModel, code)

    def ensure_operation_profile(
        self,
        code: str,
        operation_type: str,
        allowed_commands: list[str],
        capabilities: list[str],
        enabled: bool = True,
        safety_policy: dict[str, Any] | None = None,
    ) -> OperationProfileModel:
        row = self.find_operation_profile(code)
        if row is None:
            row = OperationProfileModel(code=code)
            self.db.add(row)
        row.operation_type = operation_type
        row.enabled = enabled
        row.allowed_commands_json = allowed_commands
        row.capabilities_json = capabilities
        row.safety_policy_json = safety_policy or {"emergency_stop_enabled": True}
        self.db.commit()
        self.db.refresh(row)
        return row

    def assign_operation_profile(self, board_id: str, profile_code: str) -> DeviceProfileAssignmentModel:
        row = self.db.get(DeviceProfileAssignmentModel, board_id)
        if row is None:
            row = DeviceProfileAssignmentModel(board_id=board_id)
            self.db.add(row)
        row.profile_code = profile_code
        self.db.commit()
        self.db.refresh(row)
        return row

    def find_profile_by_board(self, board_id: str) -> OperationProfileModel | None:
        assignment = self.db.get(DeviceProfileAssignmentModel, board_id)
        if assignment is None:
            return None
        return self.find_operation_profile(assignment.profile_code)

    def list_device_capabilities(self, board_id: str) -> list[DeviceCapabilityModel]:
        return (
            self.db.query(DeviceCapabilityModel)
            .filter(DeviceCapabilityModel.board_id == board_id)
            .order_by(DeviceCapabilityModel.capability_code.asc())
            .all()
        )

    def find_device_capability(self, board_id: str, capability_code: str) -> DeviceCapabilityModel | None:
        return (
            self.db.query(DeviceCapabilityModel)
            .filter(
                DeviceCapabilityModel.board_id == board_id,
                DeviceCapabilityModel.capability_code == capability_code,
            )
            .first()
        )

    def ensure_device_capability(
        self,
        board_id: str,
        capability_code: str,
        commands: list[str],
        payload_schema: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> DeviceCapabilityModel:
        row = self.find_device_capability(board_id, capability_code)
        if row is None:
            row = DeviceCapabilityModel(board_id=board_id, capability_code=capability_code)
            self.db.add(row)
        row.enabled = enabled
        row.commands_json = commands
        row.payload_schema_json = payload_schema or {}
        self.db.commit()
        self.db.refresh(row)
        return row

    def set_device_capability_enabled(
        self,
        board_id: str,
        capability_code: str,
        enabled: bool,
    ) -> DeviceCapabilityModel | None:
        row = self.find_device_capability(board_id, capability_code)
        if row is None:
            return None
        row.enabled = enabled
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_commands(self, board_id: str, limit: int = 50) -> list[ConveyorCommand]:
        return (
            self.db.query(ConveyorCommand)
            .filter(ConveyorCommand.board_id == board_id)
            .order_by(ConveyorCommand.requested_at.desc())
            .limit(limit)
            .all()
        )

    def list_events(self, board_id: str, limit: int = 50) -> list[ConveyorEvent]:
        return (
            self.db.query(ConveyorEvent)
            .filter(ConveyorEvent.board_id == board_id)
            .order_by(ConveyorEvent.occurred_at.desc())
            .limit(limit)
            .all()
        )

    def list_color_counts(self, board_id: str) -> list[ContainerColorCount]:
        return (
            self.db.query(ContainerColorCount)
            .filter(ContainerColorCount.board_id == board_id)
            .order_by(ContainerColorCount.color.asc())
            .all()
        )

    def list_color_detections(self, board_id: str, limit: int = 50) -> list[ContainerColorDetection]:
        return (
            self.db.query(ContainerColorDetection)
            .filter(ContainerColorDetection.board_id == board_id)
            .order_by(ContainerColorDetection.detected_at.desc())
            .limit(limit)
            .all()
        )
