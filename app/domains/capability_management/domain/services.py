from __future__ import annotations

from typing import Any

from app.domains.capability_management.domain.entities import DeviceCapability


class CapabilityPayloadPolicy:
    def validate_required_fields(
        self,
        capability: DeviceCapability,
        payload: dict[str, Any],
    ) -> bool:
        required_fields = capability.payload_schema.required_field_names()
        return required_fields.issubset(payload.keys())
