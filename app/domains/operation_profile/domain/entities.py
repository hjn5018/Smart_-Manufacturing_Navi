from __future__ import annotations

from dataclasses import dataclass, field

from app.domains.operation_profile.domain.enums import OperationType, ProfileStatus
from app.domains.operation_profile.domain.value_objects import (
    AllowedCommand,
    ProfileCapability,
    ProfileCode,
    ProfileSafetyPolicy,
)


@dataclass
class OperationProfile:
    code: ProfileCode
    operation_type: OperationType
    status: ProfileStatus = ProfileStatus.ACTIVE
    allowed_commands: tuple[AllowedCommand, ...] = field(default_factory=tuple)
    capabilities: tuple[ProfileCapability, ...] = field(default_factory=tuple)
    safety_policy: ProfileSafetyPolicy = field(default_factory=ProfileSafetyPolicy)

    def active(self) -> bool:
        return self.status == ProfileStatus.ACTIVE

    def allows_command(self, command: str) -> bool:
        return self.active() and any(item.command == command for item in self.allowed_commands)

    def capability_codes(self) -> set[str]:
        return {capability.capability_code for capability in self.capabilities}
