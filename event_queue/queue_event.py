from dataclasses import dataclass
from typing import Any

from .event_types import EventType


@dataclass(slots=True)
class QueueEvent:
    id: int  # id is usually simply an incremental number
    event_type: EventType
    event_name: str
    args: Any

    def __str__(self):
        return f"QueueEvent[<{self.id}> {self.event_type}.{self.event_name} {self.args}]"
