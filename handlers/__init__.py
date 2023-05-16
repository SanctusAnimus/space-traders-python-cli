from traceback import format_exc

from loguru import logger

from event_queue.queue_event import QueueEvent
from global_params import GlobalParams
from .agent import AgentHandler
from .contract import ContractHandler
from .ship import ShipHandler
from .system import SystemHandler
from .view import ViewHandler

__HANDLERS = {
    ShipHandler.event_type: ShipHandler(),
    ContractHandler.event_type: ContractHandler(),
    SystemHandler.event_type: SystemHandler(),
    AgentHandler.event_type: AgentHandler(),
    ViewHandler.event_type: ViewHandler(),
}


def get_handle(event_type: str):
    return __HANDLERS[event_type]


# event routing core
def handle_event(params: GlobalParams, event: QueueEvent) -> bool:
    event_type_handler = __HANDLERS.get(event.event_type, None)

    if not event_type_handler:
        params.console.print(f"NO EVENT TYPE HANDLER FOR {event.event_type}", style="red")
        return False

    event_handler = event_type_handler.handlers.get(event.event_name, None)

    if not event_handler:
        params.console.print(f"NO EVENT NAME HANDLER FOR {event.event_name}", style="red")
        return False

    try:
        event_handler(params, event)
        return True
    except Exception as e:
        logger.error(f"Error in event runner: {e}\n{format_exc()}")
        return False
