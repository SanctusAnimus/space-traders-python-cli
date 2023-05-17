from datetime import datetime, timedelta
from queue import PriorityQueue

from event_queue.queue_event import QueueEvent

current_datetime = datetime.now()

priority_queue = PriorityQueue()

events = [
    QueueEvent(id=440, event_name="1", event_type="ships", args=None),
    QueueEvent(id=220, event_name="XXXX", event_type="ships", args=None),
    QueueEvent(id=2, event_name="3", event_type="ships", args=None),
    QueueEvent(id=3, event_name="4", event_type="ships", args=None),
]

priority_queue.put((current_datetime, events[0]))
priority_queue.put((current_datetime, events[1]))
priority_queue.put((current_datetime, events[2]))
priority_queue.put((current_datetime - timedelta(minutes=30), events[3]))


while True:
    item = priority_queue.get()
    print(str(item))
    priority_queue.task_done()