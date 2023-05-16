from rich.pretty import pprint

from event_queue import QueueEvent
from global_params import GlobalParams
from printers import print_contracts, SUCCESS_PREFIX, FAIL_PREFIX
from space_traders_api_client.api.contracts import get_contracts, accept_contract, fulfill_contract, deliver_contract
from space_traders_api_client.models.deliver_contract_json_body import DeliverContractJsonBody
from strategies.base_contract import BaseContractStrategy


class ContractHandler:
    event_type = "contracts"

    def __init__(self):
        self.handlers = {
            "accept": self.accept,
            "fetch_all": self.fetch_all,
            "deliver": self.deliver,
            "fulfill": self.fulfill,
            "strategy": self.initiate_strategy,
            "assign_ship": self.assign_strategy_ship,
            "assign_survey": self.assign_strategy_survey,
        }

        self.active_strategy: dict[str, BaseContractStrategy] = {}

    def initiate_strategy(self, params: GlobalParams, event: QueueEvent):
        contract_id = event.args[0]
        asteroid_symbol = event.args[1]

        if contract_id in self.active_strategy:
            params.console.print(f"{FAIL_PREFIX}Already have active strategy for contract [b]{contract_id}[/]")
            return

        with params.lock:
            contract = params.game_state.contracts.get(contract_id, None)
            if contract is None:
                params.console.print(f"{FAIL_PREFIX}No contract with id [b]{contract_id}[/]")
                return

        self.active_strategy[contract_id] = BaseContractStrategy(params, contract_id, asteroid_symbol)

    def assign_strategy_ship(self, params: GlobalParams, event: QueueEvent):
        contract_id = event.args[0]
        ship_symbol = event.args[1]
        # TODO: validate ship
        self.active_strategy[contract_id].assign_ship(ship_symbol)

    def assign_strategy_survey(self, params: GlobalParams, event: QueueEvent):
        contract_id = event.args[0]
        survey_signature = event.args[1]
        # TODO: validate survey
        self.active_strategy[contract_id].set_survey(survey_signature)

    @staticmethod
    def accept(params: GlobalParams, event: QueueEvent):
        contract_id = event.args[0]

        result = accept_contract.sync(client=params.client, contract_id=contract_id)
        if result.data:
            result_contract = result.data.contract
            with params.lock:
                params.game_state.agent = result.data.agent
                params.game_state.contracts[result_contract.id] = result_contract
            params.console.print(f"{SUCCESS_PREFIX}Accepted contract [b]{result_contract.id}[/]")
            pprint(result.data.contract)

            # maybe auto-initiate strategy?
            # may be worth to automate contract accepting too!
        else:
            params.console.print(f"{FAIL_PREFIX}Failed to accept contract")

    @staticmethod
    def fulfill(params: GlobalParams, event: QueueEvent):
        contract_id = event.args[0]
        result = fulfill_contract.sync(client=params.client, contract_id=contract_id)
        if result.data:
            with params.lock:
                params.game_state.agent = result.data.agent
                params.game_state.contracts[contract_id] = result.data.contract

            params.console.print(f"{SUCCESS_PREFIX}Contract [b]{contract_id}[/] fulfilled!")

    @staticmethod
    def deliver(params: GlobalParams, event: QueueEvent):
        contract_id = event.args[0]
        ship_symbol = event.args[1]
        trade_symbol = event.args[2]
        units = event.args[3]

        body = DeliverContractJsonBody(
            ship_symbol=ship_symbol,
            trade_symbol=trade_symbol,
            units=units
        )

        result = deliver_contract.sync(client=params.client, contract_id=contract_id, json_body=body)
        if result.data:
            with params.lock:
                params.game_state.contracts[contract_id] = result.data.contract
                params.game_state.ships[ship_symbol].cargo = result.data.cargo
            params.console.print(f"{SUCCESS_PREFIX}Delivered [b]{units}[/] [u]{trade_symbol}[/] for contract [b]{contract_id}[/]")

    @staticmethod
    def fetch_all(params: GlobalParams, event: QueueEvent):
        result = get_contracts.sync(client=params.client)
        # NOTE: might need pagination handling in the future
        params.console.print(SUCCESS_PREFIX, f"Contracts: [b u]{len(result.data)}[/]")
        with params.lock:
            params.game_state.contracts = {
                contract.id: contract for contract in result.data
            }
            print_contracts(params.console, params.game_state.contracts.values())
