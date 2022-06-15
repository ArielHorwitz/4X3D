
from loguru import logger
from collections import deque, namedtuple
from operator import attrgetter
import bisect
from util import is_number


Event = namedtuple('Event', ('uid', 'tick', 'callback', 'description'))


class EventQueue:
    def __init__(self):
        self.queue = deque()

    def add(self, uid, tick, callback, description=None):
        assert is_number(tick)
        assert callable(callback)
        if description is None:
            description = 'Event description not available.'
        event = Event(uid, tick, callback, description)
        insert_idx = bisect.bisect_right(self.queue, event.tick, key=attrgetter('tick'))
        self.queue.insert(insert_idx, event)
        # logger.debug(f'Added {event} at index {insert_idx} of event queue')
        return insert_idx

    @property
    def next(self):
        return self.queue[0]

    def pop_next(self, tick=float('inf')):
        if self.queue[0].tick <= tick:
            return self.queue.popleft()
        return None

    def __len__(self):
        return len(self.queue)
