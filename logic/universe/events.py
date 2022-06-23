import random
from heapq import heappush, heappop
from dataclasses import dataclass, field
from util import is_number
from typing import Callable, NewType

EventCallback = Callable[[int], None]
EventUid = NewType('EventUid', float)

NULL_EVENT_UID = EventUid(-1.)
NO_DESCRIPTION = 'Event description not available.'

def get_event_uid() -> EventUid:
    return EventUid(random.random())


@dataclass(order=True, slots=True)
class Event:
    tick : int
    callback : EventCallback = field(compare=False, repr=False)
    description : str = field(compare=False)
    uid : EventUid= field(default_factory=get_event_uid, compare=False, repr=False)


class EventQueue:
    def __init__(self):
        self.__queue = []

    def add(self, tick: int, 
            callback: EventCallback, 
            description: str=NO_DESCRIPTION, 
            uid: EventUid=NULL_EVENT_UID):
        assert is_number(tick)
        assert callable(callback)
        if uid is NULL_EVENT_UID:
            uid = get_event_uid()
        event = Event(tick, callback, description, uid)
        heappush(self.__queue, event)

    @property
    def next(self):
        return self.__queue[0]

    def pop_next(self, tick=float('inf')):
        if self.__queue[0].tick <= tick:
            return heappop(self.__queue)
        return None

    def __len__(self):
        return len(self.__queue)
