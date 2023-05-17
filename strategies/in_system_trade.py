# buy X in one waypoint, move to another, sell, return, repeat
# all done within a single system
from dataclasses import dataclass
from datetime import timedelta, datetime, timezone

from loguru import logger

from event_queue import event_queue, QueueEvent, EventType
from global_params import GlobalParams, RESERVED_ITEMS
from printers import INFO_PREFIX
from space_traders_api_client.models import ShipNavStatus
from strategies.base_strategy import queue_dock, queue_refuel, queue_sell_cargo, queue_buy_cargo, queue_navigate, \
    queue_orbit


@dataclass(slots=True)
class TradeRoute:
    resource_symbol: str
    source_waypoint: str
    target_waypoint: str

# TODO: market trade route profit autodiscovery
# TODO: update internal market state after trade
# TODO: suspend trade route if profit falls below threshold (requires event modification?)
# TODO: fuel estimation to avoid over-spending on it and save RPS
#  (if two navigates cost less than full charge, we can only refuel once)


class SystemTradeStrategy:
    def __init__(self, params: GlobalParams):
        self.trade_routes: dict[str, TradeRoute] = {}
        self.__pending_navigate_target = {}
        self.__pending_navigate_source = {}
        self.__params = params

        event_queue.subscribe(EventType.SHIP, "navigate", self.on_navigate)

    def on_navigate(self, event: QueueEvent):
        # ship started navigation towards selling target - queue dock, refuel, sell
        ship_symbol_target = self.__pending_navigate_target.get(event.id, None)
        if ship_symbol_target is not None:
            return self.handle_navigate_target(ship_symbol_target)

        # ship started navigation towards purchase source - queue dock, refuel, purchase
        ship_symbol_source = self.__pending_navigate_source.get(event.id, None)
        if ship_symbol_source is not None:
            return self.handle_navigate_source(ship_symbol_source)

    def __get_navigate_complete_time(self, ship_symbol: str) -> datetime | None:
        current_time = datetime.now(tz=timezone.utc)
        with self.__params.lock:
            ship = self.__params.game_state.ships[ship_symbol]
            # if arrival is in the future, return it, otherwise None to queue immediately
            if ship.nav.route.arrival > current_time:
                return ship.nav.route.arrival + timedelta(seconds=10)

    def handle_navigate_target(self, ship_symbol: str):
        arrival = self.__get_navigate_complete_time(ship_symbol)
        logger.debug(f"Handling navigate target {ship_symbol} | {arrival}")
        trade_route = self.trade_routes[ship_symbol]
        queue_dock(ship_symbol, when=arrival)
        queue_refuel(ship_symbol, when=arrival)
        queue_sell_cargo(ship_symbol, trade_route.resource_symbol, -1, when=arrival)
        queue_orbit(ship_symbol, when=arrival)
        queue_navigate(ship_symbol, trade_route.source_waypoint, when=arrival, record_to=self.__pending_navigate_source)

    def handle_navigate_source(self, ship_symbol: str):
        arrival = self.__get_navigate_complete_time(ship_symbol)
        logger.debug(f"Handling navigate source {ship_symbol} | {arrival}")
        trade_route = self.trade_routes[ship_symbol]
        queue_dock(ship_symbol, when=arrival)
        queue_refuel(ship_symbol, when=arrival)
        queue_buy_cargo(ship_symbol, trade_route.resource_symbol, -1, when=arrival)
        queue_orbit(ship_symbol, when=arrival)
        queue_navigate(ship_symbol, trade_route.target_waypoint, when=arrival, record_to=self.__pending_navigate_target)

    def assign_ship(self, ship_symbol: str, resource_symbol: str, source_waypoint: str, target_waypoint: str):
        self.trade_routes[ship_symbol] = TradeRoute(
            resource_symbol=resource_symbol,
            source_waypoint=source_waypoint,
            target_waypoint=target_waypoint
        )
        self.__params.console.print(
            f"{INFO_PREFIX}Created Trade Route [ship]{ship_symbol}[/]: "
            f"[resource]{resource_symbol}[/] from [waypoint]{source_waypoint}[/] to [waypoint]{target_waypoint}[/]"
        )

        logger.debug(f"Creating trade route {ship_symbol}: {resource_symbol} from {ship_symbol} to {target_waypoint}")

        with self.__params.lock:
            ship = self.__params.game_state.ships[ship_symbol]
            # TODO: handle in-transit state
            # TODO: handle already having full trade cargo
            if ship.nav.waypoint_symbol != source_waypoint:
                logger.debug(f"{ship_symbol} is outside trade route source - {ship.nav.waypoint_symbol} | {source_waypoint}")
                queue_navigate(ship_symbol, source_waypoint, record_to=self.__pending_navigate_source)
            else:
                logger.debug(f"{ship_symbol} is on source waypoint - initiating trade")
                # TODO: ideally event handler should handle the state by itself and skip redundant requests
                #   instead of doing it like this
                if ship.nav.status == ShipNavStatus.IN_ORBIT:
                    queue_dock(ship_symbol)

                # refuel only if needed - saving rps
                if ship.fuel.current < ship.fuel.capacity:
                    queue_refuel(ship_symbol)

                for resource in ship.cargo.inventory:
                    if resource.symbol != resource_symbol and resource.symbol not in RESERVED_ITEMS:
                        logger.debug(f"{ship_symbol} has left-over cargo: {resource.symbol} {resource.units}")
                        queue_sell_cargo(ship_symbol, resource.symbol, resource.units)
                queue_buy_cargo(ship_symbol, resource_symbol, -1)  # -1 mean fill entire cargo
                queue_orbit(ship_symbol)
                queue_navigate(ship_symbol, target_waypoint, record_to=self.__pending_navigate_target)
