from rich.pretty import pprint

from event_queue.queue_event import QueueEvent
from global_params import GlobalParams
from printers import print_ships, print_ship, print_agent, SUCCESS_PREFIX
from space_traders_api_client.api.fleet import create_survey
from space_traders_api_client.api.fleet import (
    get_my_ships, purchase_ship, navigate_ship, dock_ship, refuel_ship, orbit_ship, extract_resources, sell_cargo
)
from space_traders_api_client.models.extract_resources_json_body import ExtractResourcesJsonBody, Unset
from space_traders_api_client.models.navigate_ship_json_body import NavigateShipJsonBody
from space_traders_api_client.models.purchase_ship_json_body import PurchaseShipJsonBody, ShipType
from space_traders_api_client.models.sell_cargo_sell_cargo_request import SellCargoSellCargoRequest


class ShipHandler:
    event_type = "ships"

    def __init__(self):
        self.handlers = {
            "dock": self.dock,
            "orbit": self.orbit,
            "navigate": self.navigate,
            "extract": self.extract,
            "refuel": self.refuel,
            "purchase": self.purchase,
            "sell_cargo_item": self.sell_cargo_item,
            "fetch_all": self.fetch_all,
        }

    @staticmethod
    def dock(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        result = dock_ship.sync(client=params.client, ship_symbol=ship_symbol)

        if result.data:
            params.console.print(f"{SUCCESS_PREFIX}Docked ship at {result.data.nav.waypoint_symbol}")
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.nav = result.data.nav

                print_ship(params.console, ship)

    @staticmethod
    def orbit(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        result = orbit_ship.sync(client=params.client, ship_symbol=ship_symbol)
        if result.data:
            params.console.print(
                f"{SUCCESS_PREFIX}Entered orbit of {result.data.nav.waypoint_symbol} with {ship_symbol}")
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.nav = result.data.nav

                print_ship(params.console, ship)

    @staticmethod
    def navigate(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]

        body = NavigateShipJsonBody(
            waypoint_symbol=event.args[1]
        )

        result = navigate_ship.sync(client=params.client, ship_symbol=ship_symbol, json_body=body)
        if result.data:
            params.console.print(f"{SUCCESS_PREFIX}Moving ship to {event.args[1]}")
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.nav = result.data.nav
                ship.fuel = result.data.fuel

                print_ship(params.console, ship)

    @staticmethod
    def extract(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        # TODO: implement survey supplying when they fix them
        body = ExtractResourcesJsonBody(
            survey=Unset()
        )
        result = extract_resources.sync(client=params.client, ship_symbol=ship_symbol, json_body=body)
        if result.data:
            params.console.print(f"{SUCCESS_PREFIX}Mined {result.data.cargo} with {ship_symbol}")
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.cargo = result.data.cargo
                ship.additional_properties["cooldown"] = result.data.cooldown

                print_ship(params.console, ship)

    @staticmethod
    def refuel(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        result = refuel_ship.sync(client=params.client, ship_symbol=ship_symbol)

        if result.data:
            params.console.print(f"{SUCCESS_PREFIX}Refueled ship to {result.data.fuel.current}")
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.fuel = result.data.fuel

                print_ship(params.console, ship)

    @staticmethod
    def purchase(params: GlobalParams, event: QueueEvent):
        body = PurchaseShipJsonBody(
            waypoint_symbol=event.args[0],
            ship_type=ShipType(event.args[1].upper())
        )
        result = purchase_ship.sync(client=params.client, json_body=body)
        if result.data:
            new_ship = result.data.ship
            with params.lock:
                params.console.print(f"{SUCCESS_PREFIX}Purchased ship {new_ship.symbol}")
                params.game_state.agent = result.data.agent
                params.game_state.ships[new_ship.symbol] = new_ship

    @staticmethod
    def sell_cargo_item(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]

        body = SellCargoSellCargoRequest(
            symbol=event.args[1],
            units=int(event.args[2])
        )
        result = sell_cargo.sync(client=params.client, ship_symbol=ship_symbol, json_body=body)
        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            params.game_state.agent = result.data.agent
            ship.cargo = result.data.cargo

            print_agent(params.console, result.data.agent)
            print_ship(params.console, ship)

    @staticmethod
    def fetch_all(params: GlobalParams, event: QueueEvent):
        result = get_my_ships.sync(client=params.client)
        # NOTE: might need pagination handling in the future
        params.console.print(SUCCESS_PREFIX, f"Ships: [b][u]{len(result.data)}[/]")

        with params.lock:
            params.game_state.ships = {ship.symbol: ship for ship in result.data}
            print_ships(params.console, result.data)

    @staticmethod
    def create_survey(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        result = create_survey.sync(client=params.client, ship_symbol=ship_symbol)
        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            ship.additional_properties["cooldown"] = result.data.cooldown
            pprint(result.data.surveys)
            for survey in result.data.surveys:
                params.game_state.surveys[survey.symbol][survey.signature] = survey