from os import getenv
from queue import Empty
from sys import stdout
from threading import Thread, get_ident as get_thread_id
from time import sleep

from dotenv import load_dotenv
from loguru import logger

from database import bind_db
from event_queue import QueueEvent
from event_queue import event_queue
from event_queue.event_types import EventType
from global_params import global_params
from handle_result import HandleResult
from handlers import handle_event

EXIT_CMD = "exit"


def thread_command_runner():
    thread_id = get_thread_id()

    while True:
        global_params.event_queue.update_scheduled()
        try:
            event: QueueEvent = global_params.event_queue.get(timeout=0.6)
        except Empty:
            continue

        if event.event_name == "exit":
            logger.debug(f"[thread {thread_id}] exiting...")
            break

        logger.debug(f"[thread {thread_id}] executing {event}")

        result = handle_event(global_params, event)

        if result == HandleResult.SKIP:
            logger.debug(f"{event} has been skipped by handler")
            continue
        # notify event queue that processing for this event is complete
        # this also notifies all subscribers
        global_params.event_queue.event_done(event, result)
        # sleeping on a timer to respect rate limits (2r/s)
        # could do it smarter with headers and burst limit handling, but I'm lazy
        sleep(0.55)


def main():
    load_dotenv()
    bind_db()

    _thread = Thread(target=thread_command_runner, daemon=True)
    _thread.start()

    logger.remove(0)  # remove default
    # only write errors in stdout
    logger.add(stdout, level="ERROR")
    logger.add("exec.log", rotation="1 day", retention="2 days", enqueue=True)
    logger.add("error.log", rotation="1 day", retention="2 days", enqueue=True, level="ERROR")

    token = getenv("TOKEN", "undefined")
    is_token_present = token != "undefined"
    logger.info(f"Token: {'found' if is_token_present else 'NOT FOUND'}")

    if is_token_present:
        global_params.console.rule("Fetching game data", style="red", align="left")
        global_params.client.token = token
        # fetch all relevant base data
        global_params.event_queue.put(EventType.AGENT, "fetch")
        global_params.event_queue.put(EventType.SHIP, "fetch_all")
        global_params.event_queue.put(EventType.CONTRACT, "fetch_all")

        with open("autorun.txt", "r") as autorun_src:
            for line in autorun_src:
                if not line or line.startswith("#") or len(line) < 5:
                    continue
                event_type, event_name, *args = line.split()
                global_params.event_queue.put(EventType(event_type), event_name, args)
    else:
        global_params.console.print(
            f"[red]Token not found (or no valid .env in root).[/]\n"
            f"Please register with `register <symbol> <faction> <email>"
        )

    while True:
        try:
            command = input("Awaiting your command...\n")
        except KeyboardInterrupt:
            logger.info("keyboard interrupt triggered, exiting...")
            global_params.event_queue.put(EventType.DEFAULT, EXIT_CMD)
            break

        if command == EXIT_CMD:
            global_params.event_queue.put(EventType.DEFAULT, EXIT_CMD)
            break
        else:
            # logger.debug(f"queueing {command} for executor")
            event_type_str, event_name, *args = command.split()

            try:
                event_type = EventType(event_type_str)
            except ValueError:
                logger.error(f"Incorrect event type - {event_type_str}! Request skipped")
                continue

            if event_type in (EventType.VIEW, EventType.STRATEGY):
                # logger.debug(f"Executing view event immediately")
                handle_event(global_params, event_queue.new_event(
                    event_type=event_type,
                    event_name=event_name,
                    args=args
                ))
            else:
                global_params.event_queue.put(event_type, event_name, args)

    # wait for processing thread to finish
    _thread.join()
    logger.info("...done")


if __name__ == "__main__":
    main()
