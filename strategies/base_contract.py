# base contract resolution
# takes as many mining ships as we have and send to asteroid
# mine until full cargo, sells everything that is not in the contract
# when cargo is full, refuel, deliver, refuel, move back
# repeat until the contract is complete


from space_traders_api_client.models.contract import Contract

from global_params import GlobalParams


class BaseContractStrategy:
    def __init__(self):
        self.active_contract: Contract | None = None

        # hardcoded for now
        self.__asteroid_field = "X1-DC54-89945X"

        self.__desired_resource_names = {}
        self.__pending_extracts = {}

    def start(self, contract: Contract, params: GlobalParams):
        self.active_contract = contract

        for resource in self.active_contract.terms.deliver:
            self.__desired_resource_names[resource.trade_symbol] = resource

        desired_resource_names = ",".join(self.__desired_resource_names.keys())

        # reserve ships (somehow, need to make stuff for it)
        # for now just using all we have

        with params.lock:
            for signature, ship in params.game_state.ships.items():
                extract_id = params.event_queue.put(f"extract_ship {signature}")
                self.__pending_extracts[extract_id] = True
            for signature, ship in params.game_state.ships.items():
                params.event_queue.put(f"sell_all_cargo_except {signature} {desired_resource_names}")
