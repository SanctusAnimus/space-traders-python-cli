from datetime import datetime, timezone
from json import dump, load

from dateutil.parser import isoparse
from loguru import logger
from rich.pretty import pprint

from event_queue.queue_event import QueueEvent
from global_params import GlobalParams
from printers import print_ships, SUCCESS_PREFIX
from space_traders_api_client.api.fleet import create_survey
from space_traders_api_client.api.fleet import (
    get_my_ships, purchase_ship, navigate_ship, dock_ship, refuel_ship, orbit_ship, extract_resources, sell_cargo
)
from space_traders_api_client.models.extract_resources_json_body import ExtractResourcesJsonBody, Unset
from space_traders_api_client.models.navigate_ship_json_body import NavigateShipJsonBody
from space_traders_api_client.models.purchase_ship_json_body import PurchaseShipJsonBody, ShipType
from space_traders_api_client.models.sell_cargo_sell_cargo_request import SellCargoSellCargoRequest
from space_traders_api_client.models.survey import Survey, SurveySize, SurveyDeposit


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
            "survey": self.create_survey_method,
            "load_survey": self.load_survey,
        }

    @staticmethod
    def dock(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        result = dock_ship.sync(client=params.client, ship_symbol=ship_symbol)

        if result.data:
            params.console.print(
                f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] docked at [waypoint]{result.data.nav.waypoint_symbol}[/]"
            )
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.nav = result.data.nav

                # print_ship(params.console, ship)

    @staticmethod
    def orbit(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        result = orbit_ship.sync(client=params.client, ship_symbol=ship_symbol)
        if result.data:
            params.console.print(
                f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] entered orbit of [waypoint]{result.data.nav.waypoint_symbol}[/]")
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.nav = result.data.nav

                # print_ship(params.console, ship)

    @staticmethod
    def navigate(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        waypoint = event.args[1]

        body = NavigateShipJsonBody(
            waypoint_symbol=waypoint
        )

        result = navigate_ship.sync(client=params.client, ship_symbol=ship_symbol, json_body=body)
        if result.data:
            route = result.data.nav.route
            params.console.print(f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] navigating towards [waypoint]{waypoint}[/]. "
                                 f"Estimated: [duration]{route.arrival - route.departure_time}[/]")
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.nav = result.data.nav
                ship.fuel = result.data.fuel

    @staticmethod
    def extract(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]

        current_datetime = datetime.now(tz=timezone.utc)

        survey = Unset()
        if len(event.args) >= 2:
            survey_symbol = event.args[1]
            with params.lock:
                waypoint = params.game_state.ships[ship_symbol].nav.waypoint_symbol
                survey = params.game_state.surveys[waypoint][survey_symbol]
                # if a survey is expired, discard
                if survey.expiration < current_datetime:
                    logger.debug(f"Requested excavate survey {survey_symbol} is expired!")
                    survey = Unset()
        body = ExtractResourcesJsonBody(
            survey=survey
        )
        # TODO: handle exhausted surveys 400 response somehow
        result = extract_resources.sync(client=params.client, ship_symbol=ship_symbol, json_body=body)
        if result.data:
            extraction_yield = result.data.extraction.yield_
            cooldown = result.data.cooldown

            cooldown_duration = cooldown.expiration - datetime.now(tz=timezone.utc)

            params.console.print(f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] mined"
                                 f" {extraction_yield.units} [resource]{extraction_yield.symbol}[/]. "
                                 f"On cooldown for [cooldown]{cooldown_duration} "
                                 f"({cooldown.expiration.isoformat(timespec='seconds')})[/]")
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.cargo = result.data.cargo
                ship.additional_properties["cooldown"] = cooldown

    @staticmethod
    def refuel(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        result = refuel_ship.sync(client=params.client, ship_symbol=ship_symbol)

        if result.data:
            params.console.print(
                f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] refueled to {result.data.fuel.current}"
            )
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.fuel = result.data.fuel
                params.game_state.agent = result.data.agent

                # print_ship(params.console, ship)

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
                params.console.print(f"{SUCCESS_PREFIX}[ship]{new_ship.symbol}[/] has been purchased!")
                params.game_state.agent = result.data.agent
                params.game_state.ships[new_ship.symbol] = new_ship

    @staticmethod
    def sell_cargo_item(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]

        symbol = event.args[1]

        if symbol == "ANTIMATTER":
            logger.debug(f"TRIED TO SELL ANTIMATTER")
            return

        body = SellCargoSellCargoRequest(
            symbol=symbol,
            units=int(event.args[2])
        )
        result = sell_cargo.sync(client=params.client, ship_symbol=ship_symbol, json_body=body)
        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            params.game_state.agent = result.data.agent
            ship.cargo = result.data.cargo

            transaction = result.data.transaction
            params.console.print(
                f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] sold {transaction.units} "
                f"[resource]{transaction.trade_symbol}[/] "
                f"for {transaction.total_price} ({transaction.price_per_unit} per unit)"
            )

            # print_agent(params.console, result.data.agent)
            # print_ship(params.console, ship)

    @staticmethod
    def fetch_all(params: GlobalParams, event: QueueEvent):
        result = get_my_ships.sync(client=params.client)
        # NOTE: might need pagination handling in the future
        params.console.print(f"{SUCCESS_PREFIX}Ships: [b u]{len(result.data)}[/]")

        with params.lock:
            params.game_state.ships = {ship.symbol: ship for ship in result.data}
            print_ships(result.data)

    @staticmethod
    def create_survey_method(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        result = create_survey.sync(client=params.client, ship_symbol=ship_symbol)
        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            ship.additional_properties["cooldown"] = result.data.cooldown
            survey_log_data = []

            for survey in result.data.surveys:
                params.game_state.surveys[survey.symbol][survey.signature] = survey
                deposits = ", ".join(f"[resource]{deposit.symbol}[/]" for deposit in survey.deposits)
                survey_log_data.append(f"[waypoint]{survey.signature}[/]([green u]{survey.size}[/]): {deposits}")

                with open(f"surveys/{survey.signature}.json", "w") as target:
                    dump(survey.to_dict(), target)

            survey_log_data = "\n".join(survey_log_data)
            params.console.print(f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] created surveys:\n{survey_log_data}")

    @staticmethod
    def load_survey(params: GlobalParams, event: QueueEvent):
        survey_name = event.args[0]

        with open(f"surveys/{survey_name}.json", "r") as src:
            survey = load(src)

            with params.lock:
                params.game_state.surveys[survey["symbol"]][survey["signature"]] = Survey(
                    symbol=survey["symbol"],
                    signature=survey["signature"],
                    expiration=isoparse(survey["expiration"]),
                    size=SurveySize(survey["size"]),
                    deposits=[SurveyDeposit(deposit["symbol"]) for deposit in survey["deposits"]]
                )
                pprint(params.game_state.surveys)

