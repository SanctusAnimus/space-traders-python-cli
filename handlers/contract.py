from rich.pretty import pprint

from event_queue import QueueEvent, event_queue
from global_params import GlobalParams
from printers import print_contracts, SUCCESS_PREFIX, FAIL_PREFIX
from space_traders_api_client.api.contracts import get_contracts, accept_contract, fulfill_contract, deliver_contract

from space_traders_api_client.models.deliver_contract_json_body import DeliverContractJsonBody


class ContractHandler:
    event_type = "contracts"

    def __init__(self):
        self.handlers = {
            "accept": self.accept,
            "fetch_all": self.fetch_all,
            "deliver": self.deliver,
            "fulfill": self.fulfill,
        }

        event_queue.subscribe("ships", "extract", self.on_extract)

    def on_extract(self, extract_event: QueueEvent):
        print(f"extract event complete - {extract_event}")

    def initiate_strategy(self):
        pass

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
            params.console.print(f"{SUCCESS_PREFIX}Delivered [u]{trade_symbol}[/] x {units} for contract {contract_id}")

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
