from rich.pretty import pprint

from event_queue import QueueEvent
from global_params import GlobalParams
from printers import print_waypoints, FAIL_PREFIX
from space_traders_api_client.api.systems import (
    get_system_waypoints, get_waypoint
)


class SystemHandler:
    event_type = "system"

    def __init__(self):
        self.handlers = {
            "waypoint": self.fetch_waypoint,
            "system_waypoints": self.fetch_system_waypoints,
        }

    @staticmethod
    def fetch_waypoint(params: GlobalParams, event: QueueEvent):
        waypoint = event.args[0]
        system = "-".join(waypoint.split("-")[0:2])

        result = get_waypoint.sync(client=params.client, system_symbol=system, waypoint_symbol=waypoint)
        if result.data:
            pprint(result.data)
        else:
            params.console.print(f"{FAIL_PREFIX}System not found")

    @staticmethod
    def fetch_system_waypoints(params: GlobalParams, event: QueueEvent):
        system = event.args[0]
        result = get_system_waypoints.sync(client=params.client, system_symbol=system)
        if result.data:
            print_waypoints(params.console, result.data)
        else:
            params.console.print(f"{FAIL_PREFIX}Failed to fetch system {system} waypoints")
