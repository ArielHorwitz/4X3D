
from loguru import logger
from collections import deque, namedtuple
from operator import attrgetter
import bisect


class EventQueue:
    def __init__(self):
        self.queue = deque()

    def add(self, tick, callback):
        assert isinstance(tick, int)
        assert callable(callback)
        event = Event(tick, callback)
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


Event = namedtuple('Event', ('tick', 'callback'))
