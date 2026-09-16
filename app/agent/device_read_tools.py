"""Read-only tools that an LLM may use to inspect Planner devices.

The executor intentionally exposes no database session, SQL, HTTP client, or
command-dispatch method to the model.
"""

from __future__ import annotations

import json
import asyncio
from typing import Any

from app.domains.capability_management.application.capability_service import (
    CapabilityManagementService,
)
from app.domains.control_contract.application.command_service import ControlContractService


READ_DEVICE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_devices",
            "description": "List all registered Planner devices.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_device_state",
            "description": "Get the current connection and operating state of one device.",
            "parameters": {
                "type": "object",
                "properties": {"device_id": {"type": "string"}},
                "required": ["device_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_device_diagnostics",
            "description": "Get readiness checks and diagnostic details for one device.",
            "parameters": {
                "type": "object",
                "properties": {"device_id": {"type": "string"}},
                "required": ["device_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_device_capabilities",
            "description": "List enabled and disabled capabilities configured for one device.",
            "parameters": {
                "type": "object",
                "properties": {"device_id": {"type": "string"}},
                "required": ["device_id"],
                "additionalProperties": False,
            },
        },
    },
]

COMMON_CONTROL_COMMANDS = {
    "START",
    "STOP",
    "EMERGENCY_STOP",
}

CONTROL_COMMANDS = COMMON_CONTROL_COMMANDS | {
    "SET_SPEED",
    "FORWARD",
    "REVERSE",
    "RESET",
    "STATUS_SYNC",
    "RELEASE_EMERGENCY_STOP",
    "SET_COLOR",
    "RETURN_HOME",
    "BOX_ACTION",
}

DEVICE_COMMANDS_BY_TYPE = {
    "CONTAINER_CONVEYOR": COMMON_CONTROL_COMMANDS | {
        "SET_SPEED", "FORWARD", "REVERSE", "SET_COLOR", "RESET",
        "STATUS_SYNC", "RELEASE_EMERGENCY_STOP",
    },
    "STRAIGHT_CONVEYOR": COMMON_CONTROL_COMMANDS | {
        "SET_SPEED", "FORWARD", "REVERSE", "RESET", "STATUS_SYNC",
        "RELEASE_EMERGENCY_STOP",
    },
    "CONVEYOR": COMMON_CONTROL_COMMANDS | {
        "SET_SPEED", "FORWARD", "REVERSE", "RESET", "STATUS_SYNC",
        "RELEASE_EMERGENCY_STOP",
    },
    "FEEDER": COMMON_CONTROL_COMMANDS | {
        "SET_SPEED", "FORWARD", "REVERSE", "RESET", "STATUS_SYNC",
        "RELEASE_EMERGENCY_STOP",
    },
    "AGV": COMMON_CONTROL_COMMANDS | {
        "SET_SPEED", "RETURN_HOME", "BOX_ACTION", "RESET", "STATUS_SYNC",
        "RELEASE_EMERGENCY_STOP",
    },
}

SEND_DEVICE_COMMAND_TOOL = {
    "type": "function",
    "function": {
        "name": "send_device_command",
        "description": (
            "Send one allowed command to a connected device after user confirmation. "
            "Commands: START, STOP, EMERGENCY_STOP for all devices; SET_SPEED, "
            "FORWARD and REVERSE for conveyors/feeders; SET_COLOR for a color "
            "sorting conveyor; RETURN_HOME and BOX_ACTION for an AGV."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string"},
                "command": {"type": "string", "enum": sorted(CONTROL_COMMANDS)},
                "payload": {"type": "object", "additionalProperties": True},
            },
            "required": ["device_id", "command", "payload"],
            "additionalProperties": False,
        },
    },
}


class DeviceReadToolExecutor:
    def __init__(
        self,
        control_service: ControlContractService,
        capability_service: CapabilityManagementService,
    ):
        self.control_service = control_service
        self.capability_service = capability_service

    def execute(self, name: str, arguments: str | dict[str, Any]) -> dict[str, Any]:
        """Run one allow-listed read tool and return JSON-safe tool output."""
        try:
            parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
            if not isinstance(parsed, dict):
                raise ValueError("tool arguments must be a JSON object")

            handlers = {
                "list_devices": self._list_devices,
                "get_device_state": self._get_device_state,
                "get_device_diagnostics": self._get_device_diagnostics,
                "get_device_capabilities": self._get_device_capabilities,
            }
            handler = handlers.get(name)
            if handler is None:
                raise ValueError(f"unsupported read tool: {name}")
            return {"ok": True, "data": handler(parsed)}
        except Exception as exc:
            # Tool errors go back to the model, which can explain them without
            # exposing a traceback or credentials to the user.
            return {"ok": False, "error": str(exc)}

    def _list_devices(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        if arguments:
            raise ValueError("list_devices does not accept arguments")
        return [
            {
                "device_id": board.id,
                "board_type": board.board_type,
                "name": board.name,
                "enabled": board.enabled,
            }
            for board in self.control_service.repository.list_boards()
        ]

    def _get_device_state(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.control_service.get_status(self._device_id(arguments))

    def _get_device_diagnostics(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.control_service.get_diagnostics(self._device_id(arguments))

    def _get_device_capabilities(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        device_id = self._device_id(arguments)
        return [
            {
                "code": row.capability_code,
                "enabled": row.enabled,
                "commands": row.commands_json or [],
                "payload_schema": row.payload_schema_json or {},
            }
            for row in self.capability_service.list_capabilities(device_id)
        ]

    @staticmethod
    def _device_id(arguments: dict[str, Any]) -> str:
        device_id = arguments.get("device_id")
        if not isinstance(device_id, str) or not device_id.strip():
            raise ValueError("device_id is required")
        return device_id.strip()


class DeviceControlToolExecutor(DeviceReadToolExecutor):
    """Adds one explicitly allow-listed command tool to the read executor."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.command_results: list[dict[str, Any]] = []

    def execute(self, name: str, arguments: str | dict[str, Any]) -> dict[str, Any]:
        if name != "send_device_command":
            return super().execute(name, arguments)

        try:
            parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
            if not isinstance(parsed, dict):
                raise ValueError("tool arguments must be a JSON object")
            device_id = self._device_id(parsed)
            command = parsed.get("command")
            payload = parsed.get("payload")
            if command not in CONTROL_COMMANDS:
                raise ValueError("unsupported command")
            if not isinstance(payload, dict):
                raise ValueError("payload must be a JSON object")
            self._validate_payload(command, payload)

            service = getattr(self.control_service, "control_service", self.control_service)
            self._validate_command_for_device(service, device_id, command)
            result = asyncio.run(service.dispatch_command(device_id, command, payload))
            output = {"ok": True, "data": result}
            self.command_results.append(output)
            return output
        except Exception as exc:
            output = {"ok": False, "error": str(exc)}
            self.command_results.append(output)
            return output

    @staticmethod
    def _validate_payload(command: str, payload: dict[str, Any]) -> None:
        if command == "SET_SPEED":
            speed = payload.get("speed")
            if isinstance(speed, bool) or not isinstance(speed, int) or not 0 <= speed <= 255:
                raise ValueError("SET_SPEED requires an integer speed between 0 and 255")
            if set(payload) != {"speed"}:
                raise ValueError("SET_SPEED accepts only the speed payload field")
        elif command == "SET_COLOR":
            color = payload.get("color")
            if color not in {"RED", "GREEN", "BLUE", "UNKNOWN"}:
                raise ValueError("SET_COLOR requires color RED, GREEN, BLUE, or UNKNOWN")
            if set(payload) != {"color"}:
                raise ValueError("SET_COLOR accepts only the color payload field")
        elif payload:
            raise ValueError(f"{command} does not accept a payload")

    @staticmethod
    def _validate_command_for_device(service: Any, device_id: str, command: str) -> None:
        board = service.repository.find_board(device_id)
        if board is None:
            raise ValueError("device not found")
        allowed = DEVICE_COMMANDS_BY_TYPE.get(board.board_type, COMMON_CONTROL_COMMANDS)
        if command not in allowed:
            raise ValueError(f"{command} is not supported by device type {board.board_type}")
