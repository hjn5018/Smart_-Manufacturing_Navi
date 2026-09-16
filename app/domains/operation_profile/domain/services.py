from __future__ import annotations

from app.domains.operation_profile.domain.entities import OperationProfile


class OperationProfilePolicy:
    def validate_command(self, profile: OperationProfile, command: str) -> bool:
        return profile.allows_command(command)

    def validate_capability(self, profile: OperationProfile, capability_code: str) -> bool:
        return capability_code in profile.capability_codes()
