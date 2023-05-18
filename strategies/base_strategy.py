# baseclass for any strategy, that describes some shortcut methods
from datetime import datetime
from json import load
from math import dist
from typing import Collection

from event_queue import event_queue
from event_queue.queue_event import EventType, QueueEvent
from space_traders_api_client.models import ShipNavFlightMode, Waypoint, WaypointTraitSymbol, ShipCargoItem

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


def queue_flight_mode(ship_symbol: str, flight_mode: ShipNavFlightMode, when: datetime | None = None):
    event = event_queue.new_event(
        EventType.SHIP, "flight_mode", [ship_symbol, flight_mode]
    )
    __when_handler(event, when)


def queue_fetch_system_waypoints(ship_symbol: str, system_symbol: str, when: datetime | None = None,
                                 record_to: dict[int, str] | None = None):
    event = event_queue.new_event(
        EventType.SYSTEM, "system_waypoints", [system_symbol]
    )
    __when_handler(event, when)
    if record_to is not None:
        record_to[event.id] = ship_symbol


def queue_fetch_market(waypoint_symbol: str, when: datetime | None = None,
                       record_to: dict[int, str] | None = None):
    event = event_queue.new_event(
        EventType.SYSTEM, "fetch_market", [waypoint_symbol]
    )
    __when_handler(event, when)
    if record_to is not None:
        record_to[event.id] = waypoint_symbol


def load_system_waypoints(system_name: str) -> list[Waypoint] | None:
    # TODO: this should be handled by the database!!
    try:
        with open(f"fetched_json_data/waypoints/{system_name}.json", "r") as src:
            return [Waypoint.from_dict(wp) for wp in load(src)]
    except FileNotFoundError:
        return None


def filter_waypoints_by_traits(waypoints: Collection[Waypoint], traits: list[WaypointTraitSymbol]) -> list[Waypoint]:
    required_count = len(traits)
    return [
        wp for wp in waypoints
        if sum(1 for trait in wp.traits if trait.symbol in traits) >= required_count
    ]


def get_nearest_waypoint_from(coords: tuple[int, int], waypoints: Collection[Waypoint]) -> Waypoint | None:
    # build a list of Waypoint - distance to it, sort in asc, return first
    if len(waypoints) == 0:
        return

    distances = [
        (wp, dist(coords, (wp.x, wp.y)))
        for wp in waypoints
    ]
    distances.sort(key=lambda entry: entry[1])
    return distances[0][0]


def get_resource_count(inventory: list[ShipCargoItem], resource_name: str):
    return next((item.units for item in inventory if item.symbol == resource_name), 0)
