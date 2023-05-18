from json import load
from os import walk
from os.path import join

from event_queue import QueueEvent, EventType
from global_params import global_params, GlobalParams
from space_traders_api_client.models import Market
from strategies.in_system_trade import SystemTradeStrategy


class StrategyHandler:
    event_type = EventType.STRATEGY

    def __init__(self):
        self.active_strategies = {
            "in_system_trade": SystemTradeStrategy(global_params)
        }

        self.handlers = {
            "trade": self.assign_trade_ship,
            "market_update": self.assign_system_market_updater,
            "trade_routes": self.construct_trade_routes
        }

    def assign_trade_ship(self, params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        resource = event.args[1]
        source = event.args[2]
        target = event.args[3]

        with params.lock:
            self.active_strategies["in_system_trade"].assign_ship(ship_symbol, resource, source, target)

    def assign_system_market_updater(self, params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        system = event.args[1]

        with params.lock:
            self.active_strategies["in_system_trade"].assign_market_updater(ship_symbol, system)

    def construct_trade_routes(self, params: GlobalParams, event: QueueEvent):
        system = event.args[0]

        for root, _, files in walk("fetched_json_data/markets"):
            for file_name in files:
                if not file_name.startswith(system):
                    continue
                with open(join(root, file_name), "r") as src:
                    with params.lock:
                        market = Market.from_dict(load(src))
                        params.game_state.markets[market.symbol] = market

        self.active_strategies["in_system_trade"].__target_system = system
        self.active_strategies["in_system_trade"].build_trade_routes()
