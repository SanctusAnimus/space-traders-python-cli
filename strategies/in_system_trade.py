# buy X in one waypoint, move to another, sell, return, repeat
# all done within a single system
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta, datetime, timezone
from math import dist

from loguru import logger
from rich.pretty import pprint

from console import console
from event_queue import event_queue, QueueEvent, EventType
from global_params import GlobalParams, RESERVED_ITEMS
from handle_result import HandleResult
from printers import INFO_PREFIX
from space_traders_api_client.models import Waypoint, ShipNavFlightMode, WaypointTraitSymbol, Ship
from strategies.base_strategy import (
    queue_dock, queue_refuel, queue_sell_cargo, queue_buy_cargo, queue_navigate, queue_orbit,
    queue_flight_mode, load_system_waypoints, filter_waypoints_by_traits,
    get_nearest_waypoint_from, queue_fetch_market, queue_jettison_cargo
)


@dataclass(slots=True)
class TradeRoute:
    resource_symbol: str
    source_waypoint: str
    target_waypoint: str

    def __str__(self):
        return f"TradeRoute[<{self.resource_symbol}> {self.source_waypoint} => {self.target_waypoint}]"


# TODO: fuel estimation to avoid over-spending on it and save RPS
#  (only refuel when we need to - when distance is greater than current fuel) - saves a lot of RPS
#  for cross-system trades we'll have to refuel every time we bought (or make proper cost calculator for full path)


class SystemTradeStrategy:
    def __init__(self, params: GlobalParams):
        # market updater part
        self.__market_updater = None
        self.target_system = None
        self.target_waypoints: dict[str, Waypoint] = {}
        self.waypoints_with_marketplace: list[Waypoint] = []
        self.visited_marketplaces: dict[str, bool] = {}
        self.__pending_navigate_market: dict[int, str] = {}
        self.__pending_fetch_market: dict[int, str] = {}

        # trading part
        self.trade_routes: dict[str, TradeRoute] = {}
        self.__pending_navigate_target = {}
        self.__pending_navigate_source = {}
        self.__pending_route_change: dict[str, TradeRoute] = {}
        self.__params = params
        self.__halt_trade = False

        self.assigned_ships = {}

        event_queue.subscribe(EventType.SHIP, "navigate", self.on_navigate)
        event_queue.subscribe(EventType.SYSTEM, "fetch_market", self.on_fetch_market)

    def on_navigate(self, event: QueueEvent):
        ship_symbol_market_updater = self.__pending_navigate_market.get(event.id, None)
        if ship_symbol_market_updater is not None:
            del self.__pending_navigate_market[event.id]
            with self.__params.lock:
                return self.handle_navigate_market_update(ship_symbol_market_updater, event)

        # ship started navigation towards selling target - queue dock, refuel, sell, return to source
        ship_symbol_target = self.__pending_navigate_target.get(event.id, None)
        if ship_symbol_target is not None:
            del self.__pending_navigate_target[event.id]
            with self.__params.lock:
                return self.handle_navigate_target(ship_symbol_target)

        # ship started navigation towards purchase source - queue dock, refuel, purchase, move to target
        ship_symbol_source = self.__pending_navigate_source.get(event.id, None)
        if ship_symbol_source is not None:
            del self.__pending_navigate_source[event.id]
            with self.__params.lock:
                return self.handle_navigate_source(ship_symbol_source)

    def on_fetch_market(self, event: QueueEvent):
        waypoint_symbol = self.__pending_fetch_market.get(event.id, None)
        if waypoint_symbol is None:
            logger.debug(f"{event.id} Fetched external market")
            return

        with self.__params.lock:
            ship = self.__params.game_state.ships[self.__market_updater]
            destination = ship.nav.route.destination

            self.visited_marketplaces[waypoint_symbol] = True

            nearest_wp = get_nearest_waypoint_from(
                (destination.x, destination.y),
                self.get_unvisited_market_places()
            )
            next_run = None
            # we have visited all marketplaces - rebuild trade routes and start a new fetch loop
            if nearest_wp is None:
                self.build_trade_routes()
                self.reset_visited_marketplaces()
                # reset and mark this marketplace as visited - we just scanned it
                self.visited_marketplaces[waypoint_symbol] = True
                nearest_wp = get_nearest_waypoint_from(
                    (destination.x, destination.y),
                    self.get_unvisited_market_places()
                )
                next_run = datetime.now(tz=timezone.utc) + timedelta(minutes=30)

        queue_navigate(
            self.__market_updater, nearest_wp.symbol, when=next_run, record_to=self.__pending_navigate_market
        )
        del self.__pending_fetch_market[event.id]

    def build_trade_routes(self):
        resources = defaultdict(list)
        # list all resources on export and exchange as purchasable;
        # list all resources on import as trade target
        # find correlations and output sorted by profit/cargo
        logger.debug(f"building trade routes in {self.target_system}")

        # basic assumptions for avg trade route efficiency
        assumed_cargo_size = 60
        # minimal price difference between buy and sell
        price_threshold = 20 * assumed_cargo_size
        avg_fuel_price = 240

        for waypoint, market in self.__params.game_state.markets.items():
            if "-".join(waypoint.split("-")[0:2]) != self.target_system:
                logger.debug(f"saved market {waypoint} is outside target system {self.target_system}")
                continue

            for resource in market.trade_goods:
                resources[resource.symbol].append((waypoint, resource.purchase_price, resource.sell_price))

        trade_routes = []

        for resource_name, markets_data in resources.items():
            logger.debug(f"searching for trade routes for {resource_name}")
            by_purchase_price = sorted(markets_data, key=lambda entry: entry[1])
            by_sell_price = sorted(markets_data, key=lambda entry: entry[2], reverse=True)

            for purchase_entry, sell_entry in zip(by_purchase_price, by_sell_price):
                # don't trade on the same waypoint
                p_wp = purchase_entry[0]
                s_wp = sell_entry[0]
                if p_wp == s_wp:
                    continue

                raw_trade_margin = assumed_cargo_size * (sell_entry[2] - purchase_entry[1])

                # distance to calculate fuel costs, assumed CRUISE
                distance = self.get_waypoints_distance(p_wp, s_wp)

                # assuming optimized refueling, two ways so * 2 / 100 = / 50
                fuel_cost = (distance / 50.0) * avg_fuel_price
                trip_margin = raw_trade_margin - fuel_cost
                if trip_margin >= price_threshold:
                    logger.debug(
                        f"{resource_name}: significant trade margin {p_wp} <=> {s_wp} | {raw_trade_margin} {trip_margin}"
                    )
                    trade_routes.append((resource_name, p_wp, s_wp, raw_trade_margin, trip_margin))

        if len(trade_routes) <= 0:
            logger.debug(f"No valid trade routes with expected minimal margin!")
            self.__halt_trade = True
            return

        self.__halt_trade = False

        trade_routes.sort(key=lambda entry: entry[4], reverse=True)

        pprint(trade_routes)
        new_best_route_data = trade_routes[0]
        new_best_route = TradeRoute(
            resource_symbol=new_best_route_data[0],
            source_waypoint=new_best_route_data[1],
            target_waypoint=new_best_route_data[2],
        )
        logger.debug(f"Updated best trade route to {new_best_route}")

        for ship_symbol in self.assigned_ships.keys():
            current_route = self.trade_routes.get(ship_symbol, None)
            # the ship was on standby, assign properly
            if current_route is None:
                logger.debug(f"{ship_symbol} has no current trade route - assigning")
                self.assign_ship(
                    ship_symbol,
                    new_best_route.resource_symbol,
                    new_best_route.source_waypoint,
                    new_best_route.target_waypoint
                )
            elif current_route != new_best_route:
                logger.debug(f"{ship_symbol} changing trade route to {new_best_route}")
                self.__pending_route_change[ship_symbol] = new_best_route
            else:
                logger.debug(f"{ship_symbol} is already on the best trade route")

    def __get_navigate_complete_time(self, ship_symbol: str) -> datetime | None:
        current_time = datetime.now(tz=timezone.utc)
        ship = self.__params.game_state.ships[ship_symbol]
        # if arrival is in the future, return it, otherwise None to queue immediately
        if ship.nav.route.arrival > current_time:
            return ship.nav.route.arrival + timedelta(seconds=10)

    def get_waypoints_distance(self, wp_from_name: str, wp_to_name: str):
        return dist(
            (self.target_waypoints[wp_from_name].x, self.target_waypoints[wp_from_name].y),
            (self.target_waypoints[wp_to_name].x, self.target_waypoints[wp_to_name].y)
        )

    def get_unvisited_market_places(self) -> list[Waypoint]:
        return [
            wp for wp in self.waypoints_with_marketplace
            if self.visited_marketplaces.get(wp.symbol, False) is False
        ]

    def reset_visited_marketplaces(self):
        self.visited_marketplaces = {
            wp.symbol: False for wp in self.waypoints_with_marketplace
        }

    def maybe_queue_refuel(self, ship_symbol: str, trade_route: TradeRoute, when: datetime | None = None):
        ship = self.__params.game_state.ships[ship_symbol]
        estimated_fuel_cost = self.get_waypoints_distance(
            trade_route.source_waypoint, trade_route.target_waypoint
        ) * 2.5
        logger.debug(
            f"{ship_symbol} fuel cost for {trade_route.source_waypoint} <=> {trade_route.target_waypoint}: "
            f"{estimated_fuel_cost} / {ship.fuel.current}"
        )
        if estimated_fuel_cost >= ship.fuel.current:
            logger.debug(f"{ship_symbol} won't have enough fuel - queue refuel")
            queue_refuel(ship_symbol, when=when)

    def handle_route_switch(self, ship_symbol: str, new_trade_route: TradeRoute, arrival: datetime | None):
        logger.debug(f"{ship_symbol} switching trade route to {new_trade_route}")
        console.print(f"{INFO_PREFIX}[ship]{ship_symbol}[/] switching trade route to {new_trade_route}")
        self.trade_routes[ship_symbol] = new_trade_route

        ship = self.__params.game_state.ships[ship_symbol]
        # if the ship is not on source, move there, otherwise process reaching a source
        if ship.nav.route.destination.symbol != new_trade_route.source_waypoint:
            logger.debug(
                f"{ship_symbol} destination differs from new route source: "
                f"{ship.nav.route.destination.symbol} | {new_trade_route.source_waypoint}"
            )
            queue_navigate(
                ship_symbol, new_trade_route.source_waypoint, when=arrival, record_to=self.__pending_navigate_source
            )
        else:
            self.handle_navigate_source(ship_symbol)
        del self.__pending_route_change[ship_symbol]

    def handle_navigate_target(self, ship_symbol: str):
        arrival = self.__get_navigate_complete_time(ship_symbol)
        logger.debug(f"Handling navigate target {ship_symbol} | {arrival}")
        trade_route = self.trade_routes[ship_symbol]
        queue_dock(ship_symbol, when=arrival)
        # queue_refuel(ship_symbol, when=arrival)
        queue_sell_cargo(ship_symbol, trade_route.resource_symbol, -1, when=arrival)
        queue_orbit(ship_symbol, when=arrival)

        # check if ship should do new trade route, otherwise navigate to the next loop
        if new_trade_route := self.__pending_route_change.get(ship_symbol, None):
            queue_refuel(ship_symbol, when=arrival)
            self.handle_route_switch(ship_symbol, new_trade_route, arrival)
            return

        if self.__halt_trade:
            logger.debug(f"Halt trade ordered, {ship_symbol} stops trade on {trade_route}")
            console.print(f"{INFO_PREFIX}[ship]{ship_symbol}[/] stopped trade on {trade_route}")
            return

        queue_navigate(ship_symbol, trade_route.source_waypoint, when=arrival, record_to=self.__pending_navigate_source)

    def handle_navigate_source(self, ship_symbol: str):
        arrival = self.__get_navigate_complete_time(ship_symbol)
        logger.debug(f"Handling navigate source {ship_symbol} | {arrival}")
        trade_route = self.trade_routes[ship_symbol]
        ship = self.__params.game_state.ships[ship_symbol]

        queue_dock(ship_symbol, when=arrival)

        self.maybe_queue_refuel(ship_symbol, trade_route, when=arrival)

        self.discard_orphan_cargo(ship, trade_route.resource_symbol, when=arrival)
        queue_buy_cargo(ship_symbol, trade_route.resource_symbol, -1, when=arrival)
        queue_orbit(ship_symbol, when=arrival)
        queue_navigate(ship_symbol, trade_route.target_waypoint, when=arrival, record_to=self.__pending_navigate_target)

    def handle_navigate_market_update(self, ship_symbol: str, event: QueueEvent | None = None):
        arrival = self.__get_navigate_complete_time(ship_symbol)
        logger.debug(f"{ship_symbol} fetch market scheduled for arrival")
        ship = self.__params.game_state.ships[ship_symbol]
        destination = ship.nav.route.destination
        queue_fetch_market(destination.symbol, when=arrival, record_to=self.__pending_fetch_market)

    @staticmethod
    def discard_orphan_cargo(ship: Ship, current_trade_symbol: str, when: datetime | None = None):
        for resource in ship.cargo.inventory:
            if resource.symbol != current_trade_symbol and resource.symbol not in RESERVED_ITEMS:
                logger.debug(f"{ship.symbol} has left-over cargo: {resource.symbol} {resource.units}")
                queue_jettison_cargo(ship.symbol, resource.symbol, resource.units, when=when)

    def assign_ship(self, ship_symbol: str, resource_symbol: str, source_waypoint: str, target_waypoint: str):
        new_trade_route = TradeRoute(
            resource_symbol=resource_symbol,
            source_waypoint=source_waypoint,
            target_waypoint=target_waypoint
        )
        self.trade_routes[ship_symbol] = new_trade_route

        console.print(
            f"{INFO_PREFIX}Created Trade Route [ship]{ship_symbol}[/]: "
            f"[resource]{resource_symbol}[/] from [waypoint]{source_waypoint}[/] to [waypoint]{target_waypoint}[/]"
        )

        self.assigned_ships[ship_symbol] = True

        logger.debug(f"Creating trade route {ship_symbol}: {resource_symbol} from {ship_symbol} to {target_waypoint}")

        ship = self.__params.game_state.ships[ship_symbol]
        if ship.nav.waypoint_symbol == target_waypoint or ship.nav.route.destination.symbol == target_waypoint:
            logger.debug(f"{ship_symbol} is on target waypoint or moving there")

            self.handle_navigate_target(ship_symbol)
        elif ship.nav.waypoint_symbol != source_waypoint:
            logger.debug(
                f"{ship_symbol} is outside trade route source - {ship.nav.waypoint_symbol} | {source_waypoint}")
            queue_navigate(ship_symbol, source_waypoint, record_to=self.__pending_navigate_source)
        else:
            logger.debug(f"{ship_symbol} is on source waypoint - initiating trade")

            queue_dock(ship_symbol)
            self.maybe_queue_refuel(ship_symbol, new_trade_route)
            self.discard_orphan_cargo(ship, resource_symbol)
            queue_buy_cargo(ship_symbol, resource_symbol, -1)  # -1 mean fill entire cargo
            queue_orbit(ship_symbol)
            queue_navigate(ship_symbol, target_waypoint, record_to=self.__pending_navigate_target)

    def assign_market_updater(self, ship_symbol: str, system: str):
        self.__market_updater = ship_symbol
        self.assign_system(system)

        # TODO: this will have to be removed once they fix it LMAO
        queue_flight_mode(ship_symbol, ShipNavFlightMode.BURN)

        if self.target_waypoints is None:
            logger.critical(f"{system} has no waypoints loaded!")
            return HandleResult.FAIL

        self.waypoints_with_marketplace = filter_waypoints_by_traits(
            list(self.target_waypoints.values()), traits=[WaypointTraitSymbol.MARKETPLACE]
        )
        self.reset_visited_marketplaces()

        ship = self.__params.game_state.ships[ship_symbol]
        destination = ship.nav.route.destination
        destination_symbol = destination.symbol

        unvisited = self.get_unvisited_market_places()

        nearest_wp = get_nearest_waypoint_from(
            (destination.x, destination.y),
            unvisited
        )

        queue_orbit(ship_symbol)
        # if a ship is already at the nearest market, fetch it and move on
        if destination_symbol == nearest_wp.symbol:
            logger.debug(f"{ship_symbol} is on nearest {nearest_wp.symbol}")
            self.handle_navigate_market_update(ship_symbol)
        else:
            queue_navigate(ship_symbol, nearest_wp.symbol, record_to=self.__pending_navigate_market)

    def assign_ship_standby(self, ship_symbol: str):
        """
        Assigns a ship to this strategy, but without doing anything on it - leaving management to future actions
        """
        self.assigned_ships[ship_symbol] = True
        console.print(f"{INFO_PREFIX}[ship]{ship_symbol}[/] is now on trade stand-by")

    def assign_system(self, system_symbol: str):
        self.target_system = system_symbol
        self.target_waypoints = {wp.symbol: wp for wp in load_system_waypoints(system_symbol)}
        logger.debug(f"Assigned trade system: {self.target_system}")
