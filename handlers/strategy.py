from event_queue import QueueEvent, EventType
from game_state import global_params, GlobalParams

from strategies.in_system_trade import SystemTradeStrategy


class StrategyHandler:
    event_type = EventType.STRATEGY

    def __init__(self):
        self.active_strategies = {
            "trade": SystemTradeStrategy(global_params)
        }

        self.handlers = {
            "trade": self.assign_trade_ship
        }

    def assign_trade_ship(self, params: GlobalParams, event: QueueEvent):
        ship_symbol = event.args[0]
        resource = event.args[1]
        source = event.args[2]
        target = event.args[3]

        self.active_strategies["trade"].assign_ship(ship_symbol, resource, source, target)
