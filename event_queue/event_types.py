from enum import Enum


class EventType(str, Enum):
    SHIP = "ships"
    CONTRACT = "contracts"
    AGENT = "agent"
    SYSTEM = "system"
    VIEW = "view"
    STRATEGY = "strategy"

    DEFAULT = "default"

    def __str__(self) -> str:
        return str(self.value)
