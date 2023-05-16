from rich.pretty import pprint

from event_queue import QueueEvent
from global_params import GlobalParams
from printers import print_ships, print_contracts, FAIL_PREFIX, print_ship
from space_traders_api_client.api.systems import (
    get_shipyard, get_market
)


class ViewHandler:
    event_type = "view"

    def __init__(self):
        self.handlers = {
            "ship": self.view_ship,
            "all_ships": self.view_all_ships,
            "agent": self.view_agent,
            "contract": self.view_contract,
            "all_contracts": self.view_all_contracts,
            "waypoint": self.view_waypoint,
            "system": self.view_system,
            "market": self.view_market,
            "shipyard": self.view_shipyard,
            "surveys": self.view_surveys,
        }
    @staticmethod
    def view_ship(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        ship = params.game_state.ships.get(ship_symbol, None)
        if ship is None:
            params.console.print(f"No ship with symbol {ship_symbol}", style="red")
            return

        with params.lock:
            print_ship(params.console, ship)

    @staticmethod
    def view_all_ships(params: GlobalParams, event: QueueEvent):
        with params.lock:
            print_ships(params.console, list(params.game_state.ships.values()))

    @staticmethod
    def view_agent(params: GlobalParams, event: QueueEvent):
        with params.lock:
            params.console.print(params.game_state.agent)

    @staticmethod
    def view_contract(params: GlobalParams, event: QueueEvent):
        pass

    @staticmethod
    def view_all_contracts(params: GlobalParams, event: QueueEvent):
        with params.lock:
            print_contracts(params.console, params.game_state.contracts.values())

    @staticmethod
    def view_waypoint(params: GlobalParams, event: QueueEvent):
        pass

    @staticmethod
    def view_system(params: GlobalParams, event: QueueEvent):
        pass

    @staticmethod
    def view_market(params: GlobalParams, event: QueueEvent):
        waypoint = event.args[0]
        system = "-".join(waypoint.split("-")[0:2])

        result = get_market.sync(client=params.client, waypoint_symbol=waypoint, system_symbol=system)
        pprint(result.data)

    @staticmethod
    def view_shipyard(params: GlobalParams, event: QueueEvent):
        waypoint = event.args[0]
        system = "-".join(waypoint.split("-")[0:2])

        result = get_shipyard.sync(client=params.client, system_symbol=system, waypoint_symbol=waypoint)
        if result.data:
            pprint(result.data)
        else:
            params.console.print(f"{FAIL_PREFIX}Failed to fetch system {system} shipyard")


    @staticmethod
    def view_surveys(params: GlobalParams, event: QueueEvent):
        with params.lock:
            pprint(params.game_state.surveys)