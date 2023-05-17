# base contract resolution
# takes as many mining ships as we have and send to asteroid
# mine until full cargo, sells everything that is not in the contract
# when cargo is full, refuel, deliver, refuel, move back
# repeat until the contract is complete
from dataclasses import dataclass
from datetime import timedelta, timezone, datetime
from math import floor

from loguru import logger
from rich.pretty import pprint

from event_queue import event_queue
from event_queue.event_types import EventType
from event_queue.queue_event import QueueEvent
from global_params import GlobalParams, RESERVED_ITEMS
from space_traders_api_client.models.ship import Ship
from space_traders_api_client.models.ship_nav_status import ShipNavStatus
from space_traders_api_client.types import UNSET, Unset
from strategies.base_strategy import queue_create_survey, queue_dock, queue_refuel, queue_navigate


# TODO: prevent extraction if cargo is full
#   mainly done via update_ship validation (should schedule selling of orphan items)

# TODO: restore delivery state on restart (check if ship has contract cargo, and how many, and proceed with delivery)


@dataclass(slots=True)
class ContractDelivery:
    waypoint: str
    symbol: str
    units: int
    ship: str

    fulfill: bool = False


class BaseContractStrategy:
    def __init__(self, params: GlobalParams, contract_id: str, asteroid_id: str):
        self.__asteroid_field = asteroid_id  # "X1-DC54-89945X"

        self.__pending_navigates: dict[int, str] = {}
        self.__pending_extracts: dict[int, str] = {}
        self.__pending_delivery_navigates: dict[int, ContractDelivery] = {}

        self.__params = params

        self.assigned_ship_symbols = {}

        self.contract_id = contract_id
        self.survey_signature = None

        self.assigned_surveyor = None

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
        event_queue.subscribe(EventType.SHIP, "survey", self.on_create_survey)

        self.start()

    def __validate_survey(self, signature: str) -> bool:
        # completed contract auto-runs for diamonds without a survey
        if self.contract_complete:
            return True

        if signature is None:
            return False
        # try to fetch from game state, may already be erased!
        survey = self.__params.game_state.surveys[self.__asteroid_field].get(signature, None)
        if survey is None:
            return False

        # make sure it's not expired
        current_date = datetime.now(tz=timezone.utc)

        if survey.expiration < current_date:
            return False

        return True

    @staticmethod
    def __get_required_cargo(ship: Ship) -> int:
        required_delivery_cargo = ship.cargo.capacity

        for item in ship.cargo.inventory:
            if item.symbol in RESERVED_ITEMS:
                # reserved items ignored for delivery calcs
                required_delivery_cargo = required_delivery_cargo - item.units

        return floor(required_delivery_cargo * 0.8)

    def __sell_cargo(self, ship: Ship) -> dict[str, int]:
        contract_items = {}

        for item in ship.cargo.inventory:
            # skip reserved
            if item.symbol in RESERVED_ITEMS:
                continue
            # update currently held contract resource
            if item.symbol in self.required_resources:
                contract_items[item.symbol] = item.units
            # everything else is sold
            else:
                event_queue.put(
                    EventType.SHIP, "sell_cargo_item", (ship.symbol, item.symbol, item.units)
                )

        return contract_items

    def __get_extract_payload(self, ship_symbol):
        current_datetime = datetime.now(tz=timezone.utc)

        if self.survey_signature is not None:
            survey = self.__params.game_state.surveys[self.__asteroid_field].get(self.survey_signature, None)
            if survey is not None and survey.expiration > current_datetime:
                return [ship_symbol, self.survey_signature]

        return [ship_symbol, ]

    def __extract(self, ship_symbol: str, when: datetime | None = None):
        event = event_queue.new_event(
            EventType.SHIP, "extract", self.__get_extract_payload(ship_symbol)
        )
        if when is not None:
            event_queue.schedule(when, event)
        else:
            event_queue.put(event=event)
        self.__pending_extracts[event.id] = ship_symbol

    def __navigate(self, ship_symbol: str, waypoint: str, when: datetime | None = None):
        event = event_queue.new_event(
            EventType.SHIP, "navigate", [ship_symbol, waypoint]
        )
        if when is not None:
            event_queue.schedule(when, event)
        else:
            event_queue.put(event=event)
        self.__pending_navigates[event.id] = ship_symbol

    def on_create_survey(self, event: QueueEvent):
        ship_symbol = self.assigned_surveyor
        if ship_symbol is None:
            return

        logger.debug(f"Survey complete: {event}")

        with self.__params.lock:
            expired = []
            ship = self.__params.game_state.ships[ship_symbol]

            for signature, survey in self.__params.game_state.surveys.get(self.__asteroid_field, {}).items():
                if survey.symbol != self.__asteroid_field:
                    continue
                # mark to erase signatures that have expired (can't do that while iterating)
                if not self.__validate_survey(signature):
                    logger.debug(f"Survey is invalid: {signature} {survey.expiration}")
                    expired.append(signature)
                    continue
                for deposit in survey.deposits:
                    if deposit.symbol in self.required_resources:
                        logger.debug(f"Found suitable survey for {deposit.symbol}")
                        self.assign_survey(signature)

            for expired_survey_signature in expired:
                del self.__params.game_state.surveys[self.__asteroid_field][expired_survey_signature]

            # surveying puts ship on cooldown
            when = ship.additional_properties["cooldown"].expiration + timedelta(seconds=5)

            # if a suitable survey is found, schedule mining;
            # otherwise schedule another try
            if self.survey_signature is not None:
                queue_dock(ship_symbol, when)
                self.__extract(ship_symbol, when)
            else:
                queue_create_survey(ship_symbol, when)

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
            required_delivery_cargo = self.__get_required_cargo(ship)
            contract_items = self.__sell_cargo(ship)

            # TODO: this won't work for multiple resources properly (if ship mines both)!!!
            delivery_target = None
            completed = []
            for resource_symbol, resource in self.required_resources.items():
                contract_requirement = self.required_resources[resource_symbol]
                units_remaining = contract_requirement["units_remaining"]
                held_units = contract_items.get(resource_symbol, None)
                if held_units and held_units >= required_delivery_cargo:
                    logger.debug(f"Cargo is full with contract items, delivering")
                    delivery_target = ContractDelivery(
                        resource["deliver_to"], resource_symbol, min(held_units, units_remaining), ship_symbol
                    )

                    contract_requirement["units_remaining"] -= delivery_target.units
                    if contract_requirement["units_remaining"] <= 0:
                        logger.debug(f"Completed contract delivery for {resource_symbol}")
                        completed.append(resource_symbol)
                    break

            for resource_symbol in completed:
                del self.required_resources[resource_symbol]

            # if all resources are scheduled to be delivered, continue mining for selling
            if len(self.required_resources.keys()) <= 0:
                self.contract_complete = True
                delivery_target.fulfill = True
                logger.debug(f"Completed mining for contract {self.contract_id}")

            when = ship.additional_properties["cooldown"].expiration + timedelta(seconds=5)

            # not enough to deliver, loop mining (respecting cooldown)
            if delivery_target is None:
                # if we no longer have our survey intact, may want to fetch a new one if possible
                if not self.__validate_survey(self.survey_signature):
                    self.survey_signature = None
                    if ship_symbol == self.assigned_surveyor:
                        logger.debug(
                            f"Previously-used survey {self.survey_signature} became invalid, "
                            f"creating new with {ship_symbol}"
                        )
                        queue_create_survey(ship_symbol, when)
                        return

                self.__extract(ship_symbol, when)
            # enough to deliver; orbit and move to the point
            else:
                orbit_event = event_queue.new_event(EventType.SHIP, "orbit", (ship_symbol,)),

                # have to create navigate explicitly to record into a different pending list
                navigate_to_deliver_event = event_queue.new_event(
                    EventType.SHIP, "navigate", (ship_symbol, delivery_target.waypoint)
                )

                self.__pending_delivery_navigates[navigate_to_deliver_event.id] = delivery_target

                event_queue.schedule(when, (
                    orbit_event, navigate_to_deliver_event
                ))

    def __handle_navigate_delivery(self, delivery: ContractDelivery, event: QueueEvent):
        ship_symbol = delivery.ship
        with self.__params.lock:
            ship = self.__params.game_state.ships[ship_symbol]
            arrival_time = ship.nav.route.arrival + timedelta(seconds=10)
        # these are instant, so we can batch them together
        # THE ORDER IS PRESERVED

        events_payload = [
            (EventType.SHIP, "dock", (ship_symbol,)),
            (EventType.SHIP, "refuel", (ship_symbol,)),
            (EventType.CONTRACT, "deliver", (
                self.contract_id, ship_symbol, delivery.symbol, delivery.units
            )),
        ]
        if delivery.fulfill:
            events_payload.append((EventType.CONTRACT, "fulfill", (self.contract_id,)))
        events_payload.append((EventType.SHIP, "orbit", (ship_symbol,)))

        events = event_queue.new_events_from(*events_payload)
        event_queue.schedule(arrival_time, events)

        queue_navigate(ship_symbol, self.__asteroid_field, when=arrival_time, record_to=self.__pending_navigates)

        del self.__pending_delivery_navigates[event.id]

    def on_navigate(self, event: QueueEvent):
        logger.debug(f"Navigate complete: {event}")
        # once the navigate request is complete, we know when ship is going to arrive
        # schedule events to perform on arrival

        # navigate to contract delivery executed, schedule dock and delivery
        delivery = self.__pending_delivery_navigates.get(event.id, None)
        if delivery is not None:
            self.__handle_navigate_delivery(delivery, event)
            return

        ship_symbol = self.__pending_navigates.get(event.id, None)
        if not ship_symbol:
            return logger.debug(f"Incoming navigate ID was issued externally")

        with self.__params.lock:
            ship = self.__params.game_state.ships[ship_symbol]
            complete_time = ship.nav.route.arrival + timedelta(seconds=10)

        expected_events = event_queue.new_events_from(
            (EventType.SHIP, "dock", (ship_symbol,)),
            (EventType.SHIP, "refuel", (ship_symbol,)),
        )
        event_queue.schedule(complete_time, expected_events)
        self.__extract(ship_symbol, when=complete_time)

        del self.__pending_navigates[event.id]

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
                queue_navigate(ship_symbol, self.__asteroid_field, record_to=self.__pending_navigates)
            else:
                if self.assigned_surveyor is not None and ship_symbol == self.assigned_surveyor and self.survey_signature is None:
                    logger.debug(f"creating survey: {ship_symbol}")
                    queue_create_survey(ship_symbol)
                    return

                logger.debug(f"initiating mining: {ship_symbol}")
                if ship.nav.status == ShipNavStatus.IN_ORBIT:
                    queue_dock(ship_symbol)

                # refuel only if needed - saving rps
                if ship.fuel.current < ship.fuel.capacity:
                    queue_refuel(ship_symbol)

                self.__extract(ship_symbol)

    def start(self):
        for ship_symbol in self.assigned_ship_symbols:
            self.update_ship(ship_symbol)

    def assign_surveyor(self, ship_symbol: str):
        self.assigned_surveyor = ship_symbol

    def assign_ship(self, ship_symbol: str):
        self.update_ship(ship_symbol)

    def assign_survey(self, survey_signature: str):
        self.survey_signature = survey_signature
        self.__params.console.print(f"Contract {self.contract_id} strategy set to use {self.survey_signature}")
