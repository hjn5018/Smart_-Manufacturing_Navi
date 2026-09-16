from __future__ import annotations

from dataclasses import dataclass

from app.domains.control_contract.domain.enums import BoardType
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository


@dataclass(frozen=True)
class RegistrationResult:
    device_id: str
    device_type: str
    created: bool


class DeviceRegistrationService:
    """Registers a device before its first normal control connection."""

    def __init__(self, repository: ConveyorRepository):
        self.repository = repository

    def register(
        self,
        device_id: str,
        device_type: str,
        firmware_version: str | None = None,
        hardware_id: str | None = None,
    ) -> RegistrationResult:
        if not device_id or len(device_id) > 64:
            raise ValueError("device_id must be between 1 and 64 characters")
        if not isinstance(device_type, str) or not device_type.strip() or len(device_type.strip()) > 32:
            raise ValueError("device_type must be between 1 and 32 characters")
        print("Register 진입")

        # Provisioning must record every valid device type.  The two conveyor
        # types receive their existing specialized defaults; other device types
        # are stored as generic boards and can be configured afterwards.
        board_type = device_type.strip()

        existing = self.repository.find_board(device_id)
        if existing is not None:
            if existing.board_type != board_type:
                raise ValueError("device_type does not match registered device")
            return RegistrationResult(device_id, existing.board_type, False)

        if board_type == BoardType.CONTAINER_CONVEYOR.value:
            board = self.repository.ensure_container_board(device_id)
        elif board_type == BoardType.STRAIGHT_CONVEYOR.value:
            board = self.repository.ensure_straight_board(device_id)
        else:
            board = self.repository.ensure_board(
                device_id,
                board_type,
                f"Device {device_id}",
            )

        self.repository.create_event(
            device_id,
            "DEVICE_REGISTERED",
            {
                "device_type": board.board_type,
                "firmware_version": firmware_version,
                "hardware_id": hardware_id,
            },
        )
        return RegistrationResult(device_id, board.board_type, True)
