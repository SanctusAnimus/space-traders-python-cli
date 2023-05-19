from datetime import datetime, timezone
from json import dump, load

from dateutil.parser import isoparse
from loguru import logger
from rich.pretty import pprint

from event_queue.queue_event import QueueEvent, EventType
from global_params import GlobalParams
from handle_result import HandleResult
from printers import print_ships, SUCCESS_PREFIX
from space_traders_api_client.api.fleet import create_survey
from space_traders_api_client.api.fleet import (
    get_my_ships, purchase_ship, navigate_ship, dock_ship, refuel_ship, orbit_ship, extract_resources, sell_cargo,
    purchase_cargo, jump_ship, patch_ship_nav, create_chart, create_ship_waypoint_scan, jettison
)
from space_traders_api_client.models import (
    ExtractResourcesJsonBody, JumpShipJsonBody, NavigateShipJsonBody,
    PatchShipNavJsonBody, ShipNavFlightMode,
    PurchaseCargoPurchaseCargoRequest,
    PurchaseShipJsonBody, Ship, ShipType, ShipNavStatus,
    SellCargoSellCargoRequest,
    Survey, SurveySize, SurveyDeposit,
    JettisonJsonBody
)
from space_traders_api_client.types import Unset
from strategies.base_strategy import get_resource_count


def get_cargo_space(ship: Ship) -> int:
    cargo_capacity = ship.cargo.capacity

    for item in ship.cargo.inventory:
        cargo_capacity -= item.units

    return cargo_capacity


class ShipHandler:
    event_type = EventType.SHIP

    def __init__(self):
        self.handlers = {
            "dock": self.dock,
            "orbit": self.orbit,
            "navigate": self.navigate,
            "extract": self.extract,
            "refuel": self.refuel,
            "purchase": self.purchase,
            "sell_cargo_item": self.sell_cargo_item,
            "buy_cargo_item": self.buy_cargo_item,
            "jettison_cargo_item": self.jettison_cargo_item,
            "fetch_all": self.fetch_all,
            "survey": self.create_survey_method,
            "load_survey": self.load_survey,
            "jump": self.jump,
            "flight_mode": self.flight_mode,
            "chart": self.chart,
            "scan_waypoints": self.scan_waypoints,
        }

    @staticmethod
    def dock(params: GlobalParams, event: QueueEvent) -> HandleResult | None:
        ship_symbol = event.args[0]

        # skip request and save rps if the ship is already on full fuel
        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            if ship.nav.status == ShipNavStatus.DOCKED:
                logger.debug(f"{ship_symbol} skipping dock - already docked")
                return HandleResult.SKIP

        result = dock_ship.sync(client=params.client, ship_symbol=ship_symbol)

        if result.data:
            params.console.print(
                f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] docked at [waypoint]{result.data.nav.waypoint_symbol}[/]"
            )
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.nav = result.data.nav

    @staticmethod
    def orbit(params: GlobalParams, event: QueueEvent) -> HandleResult | None:
        ship_symbol = event.args[0]

        # skip request and save rps if the ship is already on full fuel
        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            if ship.nav.status == ShipNavStatus.IN_ORBIT:
                logger.debug(f"{ship_symbol} skipping orbit - already IN_ORBIT")
                return HandleResult.SKIP

        result = orbit_ship.sync(client=params.client, ship_symbol=ship_symbol)

        if result.data:
            params.console.print(
                f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] entered orbit of "
                f"[waypoint]{result.data.nav.waypoint_symbol}[/]"
            )
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.nav = result.data.nav

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
    def refuel(params: GlobalParams, event: QueueEvent) -> HandleResult | None:
        ship_symbol = event.args[0]

        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            if ship.fuel.current == ship.fuel.capacity:
                logger.debug(f"{ship_symbol} skipping fuel - already on full fuel")
                return HandleResult.SKIP

        result = refuel_ship.sync(client=params.client, ship_symbol=ship_symbol)

        if result.data:
            params.console.print(
                f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] refueled to {result.data.fuel.current}"
            )
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                ship.fuel = result.data.fuel
                params.game_state.agent = result.data.agent

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
        units = event.args[2]

        # if -1 is set, event desires to sell all units of resource - determine how much
        if units == -1:
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                units = get_resource_count(ship.cargo.inventory, symbol)

        if units <= 0:
            logger.debug(f"{ship_symbol} tried to buy {units} {symbol} - skip")
            return HandleResult.SKIP

        if symbol == "ANTIMATTER":
            logger.debug(f"TRIED TO SELL ANTIMATTER")
            return

        body = SellCargoSellCargoRequest(
            symbol=symbol,
            units=units
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
            f"for ${transaction.total_price} (${transaction.price_per_unit} per unit)"
        )

    @staticmethod
    def buy_cargo_item(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        resource_symbol = event.args[1]
        units = event.args[2]

        # if -1 is set, event desires to buy full cargo - determine how much
        if units == -1:
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                units = get_cargo_space(ship)

        if units <= 0:
            logger.debug(f"{ship_symbol} tried to buy {units} {resource_symbol} - skip")
            return HandleResult.SKIP

        body = PurchaseCargoPurchaseCargoRequest(
            symbol=resource_symbol,
            units=units
        )

        result = purchase_cargo.sync(client=params.client, ship_symbol=ship_symbol, json_body=body)
        with params.lock:
            params.game_state.agent = result.data.agent
            params.game_state.ships[ship_symbol].cargo = result.data.cargo

        transaction = result.data.transaction
        params.console.print(
            f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] purchased {units} [resource]{resource_symbol}[/] "
            f"for ${transaction.total_price} (${transaction.price_per_unit} per unit)"
        )

    @staticmethod
    def jettison_cargo_item(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        resource_symbol = event.args[1]
        units = event.args[2]

        # if -1 is set, event desires to buy full cargo - determine how much
        if units == -1:
            with params.lock:
                ship = params.game_state.ships[ship_symbol]
                units = get_resource_count(ship.cargo.inventory, resource_symbol)

        if units <= 0:
            logger.debug(f"{ship_symbol} tried to jettison {units} {resource_symbol} - skip")
            return HandleResult.SKIP

        body = JettisonJsonBody(
            symbol=resource_symbol,
            units=units
        )

        result = jettison.sync(client=params.client, ship_symbol=ship_symbol, json_body=body)
        with params.lock:
            params.game_state.ships[ship_symbol].cargo = result.data.cargo

        params.console.print(
            f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] jettisoned {units} [resource]{resource_symbol}[/]"
        )

    @staticmethod
    def fetch_all(params: GlobalParams, event: QueueEvent):
        result = get_my_ships.sync(client=params.client, limit=20)
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

                with open(f"fetched_json_data/surveys/{survey.signature}.json", "w") as target:
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

    @staticmethod
    def jump(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        system_symbol = event.args[1]

        body = JumpShipJsonBody(
            system_symbol=system_symbol
        )

        result = jump_ship.sync(client=params.client, ship_symbol=ship_symbol, json_body=body)

        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            ship.nav = result.data.nav
            ship.additional_properties["cooldown"] = result.data.cooldown

            cooldown = result.data.cooldown
            cooldown_duration = cooldown.expiration - datetime.now(tz=timezone.utc)

            params.console.print(
                f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] jumped to [system]{system_symbol}[/]. "
                f"On cooldown for [cooldown]{cooldown_duration} "
                f"({cooldown.expiration.isoformat(timespec='seconds')})[/]"
            )

    @staticmethod
    def flight_mode(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        mode = event.args[1]

        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            if ship.nav.flight_mode == ShipNavFlightMode(mode):
                logger.debug(f"{ship_symbol} already in {mode} - skip")
                return HandleResult.SKIP

        body = PatchShipNavJsonBody(
            flight_mode=ShipNavFlightMode(mode)
        )
        result = patch_ship_nav.sync(client=params.client, ship_symbol=ship_symbol, json_body=body)
        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            ship.nav = result.data
            params.console.print(f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] is now in [flight_mode]{mode}[/] flight mode")

    @staticmethod
    def chart(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]

        result = create_chart.sync(client=params.client, ship_symbol=ship_symbol)
        params.console.print(
            f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] created chart [waypoint]{result.data.chart.waypoint_symbol}[/]"
        )

    @staticmethod
    def scan_waypoints(params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]

        result = create_ship_waypoint_scan.sync(client=params.client, ship_symbol=ship_symbol)
        params.console.print(
            f"{SUCCESS_PREFIX}[ship]{ship_symbol}[/] scanned waypoints."
        )
        with params.lock:
            ship = params.game_state.ships[ship_symbol]
            ship.additional_properties["cooldown"] = result.data.cooldown
        pprint(result.data)
