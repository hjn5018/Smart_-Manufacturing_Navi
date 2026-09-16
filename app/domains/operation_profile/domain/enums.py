from enum import Enum


class OperationType(str, Enum):
    SIMPLE_TRANSFER = "SIMPLE_TRANSFER"
    CLASSIFICATION = "CLASSIFICATION"
    DETECTION_COUNTING = "DETECTION_COUNTING"


class ProfileStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
