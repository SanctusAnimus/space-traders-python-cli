from collections import defaultdict
from datetime import datetime, timezone
from queue import Queue, PriorityQueue, Empty
from threading import Lock
from traceback import format_exc
from typing import Any, Callable, Iterable

from loguru import logger

from .event_types import EventType
from .queue_event import QueueEvent


class EventQueue:
    def __init__(self):
        self.__queue = Queue()
        self.__current_id = 0
        self.__id_lock = Lock()
        # self.__event_lock = Lock()

        self.__scheduled_lock = Lock()
        self.__scheduled_events = PriorityQueue()

        self.event_subscribers = defaultdict(dict)

    def get_new_id(self) -> int:
        with self.__id_lock:
            self.__current_id = self.__current_id + 1
            return self.__current_id

    def get(self, *args, **kwargs):
        return self.__queue.get(*args, **kwargs)

    def new_event(self, event_type: EventType, event_name: str, args: Any | None = None) -> QueueEvent:
        new_id = self.get_new_id()
        return QueueEvent(id=new_id, event_type=event_type, event_name=event_name, args=args)

    def new_events_from(self, *src: tuple[EventType, str, Any | None]) -> list[QueueEvent]:
        return [
            QueueEvent(id=self.get_new_id(), event_type=event_data[0], event_name=event_data[1], args=event_data[2])
            for event_data in src
        ]

    def put(self, event_type: EventType | None = None, event_name: str | None = None, args: Any | None = None,
            event: QueueEvent | None = None) -> int:
        if event is None:
            event = self.new_event(event_type, event_name, args)

        self.__queue.put(event)

        return event.id

    def event_done(self, event: QueueEvent, result: bool):
        self.__queue.task_done()

        if result is False:
            logger.debug(f"Failed to handle {event}, notification discarded!")
            return

        # with self.__event_lock:
        event_type_subscribers = self.event_subscribers.get(event.event_type, {})
        subscribers = event_type_subscribers.get(event.event_name, None)

        for subscriber in subscribers or []:
            try:
                subscriber(event)
            except Exception as e:
                logger.error(f"EXCEPTION IN QUEUE: {e}\n{format_exc()}")

    def schedule(self, when: datetime, event: QueueEvent | Iterable[QueueEvent]):
        if type(event) is not QueueEvent:
            logger.debug(f"Scheduled multiple events at {when}")
            for _event in event:
                self.schedule(when, _event)
        else:
            logger.debug(f"Scheduled {event} to enqueue {when}")
            # while put itself is threadsafe, we're reading index in update
            # which is NOT threadsafe as we can't access internal locks of queue reliably
            # guarding with own lock instead
            with self.__scheduled_lock:
                self.__scheduled_events.put((when, event))

    def update_scheduled(self):
        current_time = datetime.now(tz=timezone.utc)
        while True:
            with self.__scheduled_lock:
                try:
                    scheduled = self.__scheduled_events.queue[0]
                except (Empty, IndexError):
                    break

                # if the first-fetched item is in the future, the rest will be as well
                # (because schedule is priority queue)
                # so we can stop checking items at this point
                # otherwise process item and proceed with the next iteration
                if scheduled[0] > current_time:
                    break

                self.__scheduled_events.get()
                # logger.debug(f"Re-queueing scheduled event - {scheduled}")
                self.__queue.put(scheduled[1])
                self.__scheduled_events.task_done()

    def subscribe(self, event_type: EventType, event_name: str, callback: Callable):
        if event_name not in self.event_subscribers[event_type]:
            self.event_subscribers[event_type][event_name] = []
        self.event_subscribers[event_type][event_name].append(callback)


event_queue = EventQueue()
