from event_queue import QueueEvent, EventType
from global_params import GlobalParams
from printers import print_ships, print_contracts, FAIL_PREFIX, print_ship, print_agent, print_market, print_shipyard, \
    print_surveys
from space_traders_api_client.api.systems import (
    get_shipyard, get_market
)


class ViewHandler:
    event_type = EventType.VIEW

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
            params.console.print(f"No ship with symbol [ship]{ship_symbol}[/]", style="red")
            return

        with params.lock:
            print_ship(ship)

    @staticmethod
    def view_all_ships(params: GlobalParams, event: QueueEvent):
        with params.lock:
            print_ships(list(params.game_state.ships.values()))

    @staticmethod
    def view_agent(params: GlobalParams, event: QueueEvent):
        with params.lock:
            print_agent(params.game_state.agent)

    @staticmethod
    def view_contract(params: GlobalParams, event: QueueEvent):
        pass

    @staticmethod
    def view_all_contracts(params: GlobalParams, event: QueueEvent):
        with params.lock:
            print_contracts(params.game_state.contracts.values())

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

        print_market(result.data)

    @staticmethod
    def view_shipyard(params: GlobalParams, event: QueueEvent):
        waypoint = event.args[0]
        system = "-".join(waypoint.split("-")[0:2])

        result = get_shipyard.sync(client=params.client, system_symbol=system, waypoint_symbol=waypoint)
        if result.data:
            print_shipyard(result.data)
        else:
            params.console.print(f"{FAIL_PREFIX}Failed to fetch system [system]{system}[/] shipyard")

    @staticmethod
    def view_surveys(params: GlobalParams, event: QueueEvent):
        with params.lock:
            print_surveys(params.game_state.surveys)
