# baseclass for any strategy, that describes some shortcut methods
from datetime import datetime

from event_queue import event_queue
from event_queue.queue_event import EventType, QueueEvent
from global_params import GlobalParams

RESERVED_ITEMS = {
    "ANTIMATTER": True
}


def queue_create_survey(ship_symbol: str, when: datetime | None = None):
    if when is not None:
        events = event_queue.new_events_from(
            (EventType.SHIP, "orbit", [ship_symbol]),
            (EventType.SHIP, "survey", [ship_symbol])
        )
        event_queue.schedule(when, events)
        return

    # make sure we are in orbit (slightly suboptimal, wastes rps if we are already orbiting)
    event_queue.put(EventType.SHIP, "orbit", [ship_symbol])
    event_queue.put(EventType.SHIP, "survey", [ship_symbol, ])


def __when_handler(event: QueueEvent, when: datetime | None = None):
    if when is not None:
        event_queue.schedule(when, event)
    else:
        event_queue.put(event=event)


def queue_dock(ship_symbol: str, when: datetime | None = None):
    event = event_queue.new_event(
        EventType.SHIP, "dock", [ship_symbol]
    )
    __when_handler(event, when)


def queue_orbit(ship_symbol: str, when: datetime | None = None):
    event = event_queue.new_event(
        EventType.SHIP, "orbit", [ship_symbol]
    )
    __when_handler(event, when)


def queue_refuel(ship_symbol: str, when: datetime | None = None):
    event = event_queue.new_event(
        EventType.SHIP, "refuel", [ship_symbol]
    )
    __when_handler(event, when)


def queue_navigate(ship_symbol: str, waypoint: str, when: datetime | None = None,
                   record_to: dict[int, str] | None = None):
    event = event_queue.new_event(
        EventType.SHIP, "navigate", [ship_symbol, waypoint]
    )
    __when_handler(event, when)
    if record_to is not None:
        record_to[event.id] = ship_symbol


def queue_sell_cargo(ship_symbol: str, resource_symbol: str, units: int, when: datetime | None = None):
    event = event_queue.new_event(
        EventType.SHIP, "sell_cargo_item", [ship_symbol, resource_symbol, units]
    )
    __when_handler(event, when)


def queue_buy_cargo(ship_symbol: str, resource_symbol: str, units: int, when: datetime | None = None):
    event = event_queue.new_event(
        EventType.SHIP, "buy_cargo_item", [ship_symbol, resource_symbol, units]
    )
    __when_handler(event, when)


class BaseStrategy:
    def __init__(self, params: GlobalParams):
        self.__params = params
