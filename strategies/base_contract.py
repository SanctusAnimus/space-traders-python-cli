# base contract resolution
# takes as many mining ships as we have and send to asteroid
# mine until full cargo, sells everything that is not in the contract
# when cargo is full, refuel, deliver, refuel, move back
# repeat until the contract is complete

from datetime import timedelta, timezone, datetime

from loguru import logger
from rich.pretty import pprint

from event_queue import event_queue
from event_queue.event_types import EventType
from event_queue.queue_event import QueueEvent
from global_params import GlobalParams
from space_traders_api_client.types import UNSET, Unset

RESERVED_ITEMS = {
    "ANTIMATTER": True
}


# TODO: prevent extraction if cargo is full
#   mainly done via update_ship validation (should schedule selling of orphan items)

# TODO: restore delivery state on restart (check if ship has contract cargo, and how many, and proceed with delivery)

# TODO: acquire new survey if old expired / exhausted
#   and delete old one from memory

class BaseContractStrategy:
    def __init__(self, params: GlobalParams, contract_id: str, asteroid_id: str):
        self.__asteroid_field = asteroid_id  # "X1-DC54-89945X"

        self.__pending_navigates = {}
        self.__pending_extracts = {}
        self.__pending_delivery_navigates = {}

        self.__params = params

        self.assigned_ship_symbols = {}

        self.contract_id = contract_id
        self.survey_signature = None

        self.contract_complete = False

        with params.lock:
            contract = params.game_state.contracts[contract_id]

            self.required_resources = {
                resource.trade_symbol: {
                    "deliver_to": resource.destination_symbol,
                    "units_remaining": resource.units_required - resource.units_fulfilled,
                } for resource in contract.terms.deliver
            }

        pprint(self.required_resources)

        event_queue.subscribe(EventType.SHIP, "extract", self.on_extract)
        event_queue.subscribe(EventType.SHIP, "navigate", self.on_navigate)

        self.start()

    def on_extract(self, event: QueueEvent):
        ship_symbol = self.__pending_extracts.get(event.id, UNSET)
        logger.debug(f"Extract complete: {event} {ship_symbol}")
        if isinstance(ship_symbol, Unset):
            return logger.debug(f"Incoming extract ID was issued externally")
        if ship_symbol is None:
            return logger.debug(f"MISSING SHIP SYMBOL IN PENDING EXTRACT ID {event.id}")

        with self.__params.lock:
            ship = self.__params.game_state.ships[ship_symbol]
            # sell everything that doesn't belong to contract target
            # if we have at least 80% cargo of contract target, refuel, orbit, navigate and deliver
            required_delivery_cargo = ship.cargo.capacity
            contract_items = {}

            for item in ship.cargo.inventory:
                if item.symbol in RESERVED_ITEMS:
                    # reserved items ignored for delivery calcs
                    required_delivery_cargo = required_delivery_cargo - item.units
                    continue
                # update currently held contract resource
                if item.symbol in self.required_resources:
                    contract_items[item.symbol] = item.units
                # everything else is sold
                else:
                    self.__params.event_queue.put(
                        EventType.SHIP, "sell_cargo_item", (ship_symbol, item.symbol, item.units)
                    )

            # TODO: this won't work for multiple resources properly (if ship mines both)!!!
            delivery_target = None
            completed = []
            for symbol, resource in self.required_resources.items():
                contract_requirement = self.required_resources[symbol]
                units_remaining = contract_requirement["units_remaining"]
                held_units = contract_items.get(symbol, None)
                if held_units and held_units >= required_delivery_cargo:
                    logger.debug(f"Cargo is full with contract items, delivering")
                    delivery_target = {
                        "waypoint": resource["deliver_to"],
                        "symbol": symbol,
                        "units": min(held_units, units_remaining),
                        "ship": ship_symbol,
                    }

                    contract_requirement["units_remaining"] -= delivery_target["units"]
                    if contract_requirement["units_remaining"] <= 0:
                        logger.debug(f"Completed contract delivery for {symbol}")
                        completed.append(symbol)
                    break

            for symbol in completed:
                del self.required_resources[symbol]

            # if all resources are scheduled to be delivered, continue mining for selling
            if len(self.required_resources.keys()) <= 0:
                self.contract_complete = True
                logger.debug(f"Completed mining for contract {self.contract_id}")

            when = ship.additional_properties["cooldown"].expiration + timedelta(seconds=5)

            # not enough to deliver, loop mining (respecting cooldown)
            if delivery_target is None:
                event = self.__params.event_queue.new_event(
                    EventType.SHIP, "extract", self.__get_extract_payload(ship_symbol)
                )
                self.__params.event_queue.schedule(when, event)
                self.__pending_extracts[event.id] = ship_symbol
            # enough to deliver, orbit and move to the point
            else:
                orbit_event = self.__params.event_queue.new_event(EventType.SHIP, "orbit", (ship_symbol,)),

                navigate_to_deliver_event = self.__params.event_queue.new_event(
                    EventType.SHIP, "navigate", (ship_symbol, delivery_target["waypoint"])
                )

                self.__pending_delivery_navigates[navigate_to_deliver_event.id] = delivery_target

                self.__params.event_queue.schedule(when, (
                    orbit_event, navigate_to_deliver_event
                ))

    def on_navigate(self, event: QueueEvent):
        logger.debug(f"Navigate complete: {event}")
        # once the navigate request is complete, we know when ship is going to arrive
        # schedule events to perform on arrival

        # navigate to contract delivery executed, schedule dock and delivery
        delivery = self.__pending_delivery_navigates.get(event.id, None)
        if delivery is not None:
            ship_symbol = delivery["ship"]
            with self.__params.lock:
                ship = self.__params.game_state.ships[ship_symbol]
                complete_time = ship.nav.route.arrival + timedelta(seconds=10)
            # these are instant, so we can batch them together
            # THE ORDER IS PRESERVED
            events = [
                self.__params.event_queue.new_event(EventType.SHIP, "dock", (ship_symbol,)),
                self.__params.event_queue.new_event(EventType.SHIP, "refuel", (ship_symbol,)),
                self.__params.event_queue.new_event(EventType.CONTRACT, "deliver", (
                    self.contract_id, ship_symbol, delivery["symbol"], delivery["units"]
                )),
                self.__params.event_queue.new_event(EventType.SHIP, "orbit", (ship_symbol,)),
            ]

            # navigate back and record result expectancy
            navigate_event = self.__params.event_queue.new_event(
                EventType.SHIP, "navigate", (ship_symbol, self.__asteroid_field)
            )
            self.__pending_navigates[navigate_event.id] = ship_symbol
            events.append(navigate_event)

            self.__params.event_queue.schedule(complete_time, events)
            del self.__pending_delivery_navigates[event.id]
            return

        ship_symbol = self.__pending_navigates.get(event.id, None)
        if not ship_symbol:
            return logger.debug(f"Incoming navigate ID was issued externally")

        with self.__params.lock:
            ship = self.__params.game_state.ships[ship_symbol]
            complete_time = ship.nav.route.arrival + timedelta(seconds=10)

        expected_events = [
            self.__params.event_queue.new_event(EventType.SHIP, "dock", (ship_symbol,)),
            self.__params.event_queue.new_event(EventType.SHIP, "refuel", (ship_symbol,)),
        ]

        extract_event = self.__params.event_queue.new_event(
            EventType.SHIP, "extract", self.__get_extract_payload(ship_symbol)
        )
        self.__pending_extracts[extract_event.id] = ship_symbol

        expected_events.append(extract_event)

        self.__params.event_queue.schedule(complete_time, expected_events)
        del self.__pending_navigates[event.id]

    def assign_ship(self, ship_symbol: str):
        self.update_ship(ship_symbol)

    def update_ship(self, ship_symbol: str):
        logger.debug(f"raw update ship: {ship_symbol}")
        with self.__params.lock:
            ship = self.__params.game_state.ships[ship_symbol]

            # restore state of operation for this ship
            # in case of restarts etc

            # ship may be:
            # at asteroid (ensure docked, extract)
            # delivering contract (schedule delivery and trip back)
            # somewhere else (move to asteroid)

            if ship.nav.waypoint_symbol != self.__asteroid_field:
                logger.debug(f"moving ship towards asteroid {ship_symbol}")
                # handle fuel being not full
                # handle dock / orbit states
                nav_id = self.__params.event_queue.put(EventType.SHIP, "navigate", [ship_symbol, self.__asteroid_field])

                self.__pending_navigates[nav_id] = ship_symbol
            else:
                logger.debug(f"initiating mining: {ship_symbol}")
                self.__params.event_queue.put(EventType.SHIP, "dock", [ship_symbol])
                self.__params.event_queue.put(EventType.SHIP, "refuel", [ship_symbol])
                extract_id = self.__params.event_queue.put(
                    EventType.SHIP, "extract", self.__get_extract_payload(ship_symbol)
                )

                self.__pending_extracts[extract_id] = ship_symbol

    def start(self):
        for ship_symbol in self.assigned_ship_symbols:
            self.update_ship(ship_symbol)

    def set_survey(self, survey_signature: str):
        self.survey_signature = survey_signature
        self.__params.console.print(f"Contract strategy set to use {self.survey_signature}")

    def __get_extract_payload(self, ship_symbol):
        current_datetime = datetime.now(tz=timezone.utc)

        if self.survey_signature is not None:
            survey = self.__params.game_state.surveys[self.__asteroid_field][self.survey_signature]
            if survey.expiration > current_datetime:
                return [ship_symbol, self.survey_signature]

        return [ship_symbol, ]
