from os import getenv

from loguru import logger

from event_queue import event_queue
from event_queue.queue_event import QueueEvent
from global_params import GlobalParams
from printers import SUCCESS_PREFIX
from space_traders_api_client.api.agents import get_my_agent
from space_traders_api_client.api.default import register
from space_traders_api_client.client import Client
from space_traders_api_client.models.register_json_body import RegisterJsonBody, RegisterJsonBodyFaction


class AgentHandler:
    event_type = "agent"

    def __init__(self):
        self.handlers = {
            "register": self.register,
            "fetch": self.fetch
        }

        event_queue.subscribe("agent", "fetch", self.fetch_complete)

    def fetch_complete(self, event: QueueEvent):
        logger.debug(f"[AgentHandler] fetch event complete - {event} - {self}")

    @staticmethod
    def register(params: GlobalParams, event: QueueEvent):
        if getenv("TOKEN", None):
            params.console.print(f"Auth token already present and set, registration discarded!")
            return
        # authenticated client always includes bearer
        # which invalidates requests
        # use base client and save token into auth
        auth_base_client = Client(base_url="https://api.spacetraders.io/v2", timeout=30)
        body = RegisterJsonBody(
            faction=RegisterJsonBodyFaction.VOID,
            symbol=event.args[1],
            email=event.args[2],
        )
        result = register.sync(client=auth_base_client, json_body=body)
        logger.info(f"TOKEN: {result.data.token}")

        with params.lock:
            params.game_state.agent = result.data.agent
            params.game_state.contracts = [result.data.contract, ]
            params.game_state.faction = result.data.faction
            params.game_state.ships = [result.data.ship, ]

        logger.info(f"Registered new account")

        params.client.token = result.data.token

    @staticmethod
    def fetch(params: GlobalParams, event: QueueEvent):
        result = get_my_agent.sync(client=params.client)

        with params.lock:
            params.game_state.agent = result.data
        params.console.print(
           f"{SUCCESS_PREFIX}[bold magenta]Account[/]: [agent]{result.data.symbol}[/] [dim]{result.data.account_id}[/]"
        )
