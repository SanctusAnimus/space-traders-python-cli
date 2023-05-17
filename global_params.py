from collections import defaultdict
from threading import Lock

from console import console
from event_queue import EventQueue, event_queue
from space_traders_api_client import AuthenticatedClient
from space_traders_api_client.models import Agent, Ship, Contract, Faction, Survey


class GameState:
    __slots__ = ["agent", "ships", "contracts", "faction"]

    agent: Agent
    ships: dict[str, Ship]
    contracts: dict[str, Contract]
    faction: Faction | None
    # waypoint to dict of signature to survey
    surveys: dict[str, dict[str, Survey]] = defaultdict(dict)


class GlobalParams:
    __slots__ = ["lock", "event_queue", "game_state", "console", "client"]

    def __init__(self):
        self.lock = Lock()
        self.event_queue: EventQueue = event_queue
        self.game_state: GameState = GameState()

        self.console = console

        self.client = AuthenticatedClient(
            base_url="https://api.spacetraders.io/v2",
            token="", follow_redirects=True, verify_ssl=True, raise_on_unexpected_status=True, timeout=30
        )
