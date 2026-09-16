from __future__ import annotations

from typing import Protocol

from app.domains.operation_profile.domain.entities import OperationProfile
from app.domains.operation_profile.domain.value_objects import ProfileCode


class OperationProfileRepository(Protocol):
    def get(self, code: ProfileCode) -> OperationProfile | None:
        ...

    def save(self, profile: OperationProfile) -> None:
        ...

    def list_active(self) -> list[OperationProfile]:
        ...
