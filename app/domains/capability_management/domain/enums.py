from enum import Enum


class CapabilityStatus(str, Enum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class PayloadFieldType(str, Enum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    OBJECT = "OBJECT"
    ARRAY = "ARRAY"
