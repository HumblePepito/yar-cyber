import heapq
from typing import List, NamedTuple
from entity import Entity

class Ticket(NamedTuple):
    time: int
    ticket_id: int
    entity: Entity

class TurnQueue:
    def __init__(self) -> None:
        self.current_time = 0
        self.last_time = 0
        self.ticket_id = 0  # Used to sort same "current time" tickets
        self.heap: List[Ticket] = []

    def schedule(self, interval: int, entity: Entity) -> None:
        """Add the entity to the turn queue.
           * `interval` is the time to wait from the current time.
           * `entity` is the entity thant will act at scheduled time.
        """
        ticket = Ticket(self.current_time + interval, self.ticket_id, entity)
        heapq.heappush(self.heap, ticket)
        self.ticket_id += 1

    def reschedule(self, interval: int, entity: Entity) -> None:
        """Reschedule a new Ticket in place of the existing one.
           * `interval` is the time to wait from the current time.
           * `entity` is the entity to invoke at the scheduled time.
        """
        ticket = Ticket(self.current_time + interval, self.ticket_id, entity)
        heapq.heappush(self.heap, ticket) # put the entity's ticket at its new position
        self.ticket_id += 1

    def unschedule(self, entity: Entity, active_entity: Entity) -> None:
        """Explicitly remove the current entity.
        If it is the current entity, it is already removed.
        
        `unshedule()` *must* be called each time a creature is removed or dies
        """        
        if entity is active_entity:
            # for smoke, fire or other self destruct entity
            return
        for idx, ticket in enumerate(self.heap):
            if entity == ticket.entity:
                self.heap.pop(idx)

    def invoke_next(self) -> Entity:
        """Call the next scheduled entity.
        
        Until end of its turn, entity is not anymore in the queue and is referenced in `engine.active_entity`
        """
        time, ticket_id, entity = heapq.heappop(self.heap)
        self.current_time = time

        return entity

