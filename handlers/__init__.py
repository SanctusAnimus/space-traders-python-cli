from traceback import format_exc

from loguru import logger

from event_queue.queue_event import QueueEvent
from global_params import GlobalParams
from handle_result import HandleResult
from .agent import AgentHandler
from .contract import ContractHandler
from .ship import ShipHandler
from .strategy import StrategyHandler
from .system import SystemHandler
from .view import ViewHandler

__HANDLERS = {
    ShipHandler.event_type: ShipHandler(),
    ContractHandler.event_type: ContractHandler(),
    SystemHandler.event_type: SystemHandler(),
    AgentHandler.event_type: AgentHandler(),
    ViewHandler.event_type: ViewHandler(),
    StrategyHandler.event_type: StrategyHandler()
}


def handle_event(params: GlobalParams, event: QueueEvent) -> HandleResult:
    event_type_handler = __HANDLERS.get(event.event_type, None)

    if not event_type_handler:
        logger.error(f"NO EVENT TYPE HANDLER FOR {event.event_type}")
        return HandleResult.FAIL

    event_handler = event_type_handler.handlers.get(event.event_name, None)

    if not event_handler:
        logger.error(f"NO EVENT NAME HANDLER FOR {event.event_name}")
        return HandleResult.FAIL

    try:
        return event_handler(params, event) or HandleResult.SUCCESS
    except Exception as e:
        logger.critical(f"Error in event runner: {e}\n{format_exc()}")
        return HandleResult.FAIL
