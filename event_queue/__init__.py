from collections import defaultdict
from queue import Queue
from threading import Lock
from traceback import format_exc
from typing import Any, Callable

from loguru import logger

from .event_types import EventType
from .queue_event import QueueEvent


class EventQueue:
    def __init__(self):
        self.__queue = Queue()
        self.__current_id = 0
        self.__id_lock = Lock()
        self.__event_lock = Lock()

        self.event_subscribers = defaultdict(dict)

    def get_new_id(self) -> int:
        with self.__id_lock:
            self.__current_id = self.__current_id + 1
            return self.__current_id

    def get(self, *args, **kwargs):
        return self.__queue.get(*args, **kwargs)

    def new_event(self, event_type: EventType, event_name: str, args: Any | None = None) -> QueueEvent:
        new_id = self.get_new_id()
        return QueueEvent(id=new_id, event_name=event_name, args=args, event_type=event_type)

    def put(self, event_type: EventType, event_name: str, args: Any | None = None) -> int:
        event = self.new_event(event_type, event_name, args)

        self.__queue.put(event)

        return event.id

    def event_done(self, event: QueueEvent):
        self.__queue.task_done()

        logger.debug(f"Event Done: {event}")

        with self.__event_lock:
            event_type_subscribers = self.event_subscribers.get(event.event_type, {})
            subscribers = event_type_subscribers.get(event.event_name, None)

            for subscriber in subscribers or []:
                try:
                    subscriber(event)
                except Exception as e:
                    logger.error(f"EXCEPTION IN QUEUE: {e}\n{format_exc()}")

    def subscribe(self, event_type: EventType, event_name: str, callback: Callable):
        if event_name not in self.event_subscribers[event_type]:
            self.event_subscribers[event_type][event_name] = []
        self.event_subscribers[event_type][event_name].append(callback)


event_queue = EventQueue()
