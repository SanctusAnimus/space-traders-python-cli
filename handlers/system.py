from json import dump

from rich.pretty import pprint

from event_queue import QueueEvent, EventType
from global_params import GlobalParams
from printers import print_waypoints, FAIL_PREFIX, print_market, SUCCESS_PREFIX
from space_traders_api_client.api.systems import (
    get_system_waypoints, get_waypoint, get_market
)


class SystemHandler:
    event_type = EventType.SYSTEM

    def __init__(self):
        self.handlers = {
            "waypoint": self.fetch_waypoint,
            "system_waypoints": self.fetch_system_waypoints,
            "fetch_market": self.fetch_market,
        }

    @staticmethod
    def fetch_waypoint(params: GlobalParams, event: QueueEvent):
        waypoint = event.args[0]
        system = "-".join(waypoint.split("-")[0:2])

        result = get_waypoint.sync(client=params.client, system_symbol=system, waypoint_symbol=waypoint)
        if result.data:
            pprint(result.data)
        else:
            params.console.print(f"{FAIL_PREFIX}System [system]{system}[/] not found")

    @staticmethod
    def fetch_system_waypoints(params: GlobalParams, event: QueueEvent):
        system = event.args[0]
        result = get_system_waypoints.sync(client=params.client, system_symbol=system)
        if result.data:
            print_waypoints(result.data)
        else:
            params.console.print(f"{FAIL_PREFIX}Failed to fetch system [system]{system}[/] waypoints")

    @staticmethod
    def fetch_market(params: GlobalParams, event: QueueEvent):
        waypoint = event.args[0]
        system = "-".join(waypoint.split("-")[0:2])

        result = get_market.sync(client=params.client, system_symbol=system, waypoint_symbol=waypoint)
        # remove debug when done
        print_market(result.data)
        params.console.print(f"{SUCCESS_PREFIX}Updated [waypoint]{waypoint}[/] Market")
        with params.lock:
            params.game_state.markets[waypoint] = result.data

        with open(f"markets/{waypoint}.json", "w") as target_file:
            dump(result.data.to_dict(), target_file)
