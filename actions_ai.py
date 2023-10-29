from __future__ import annotations

import numpy as np
import time

from typing import List,TYPE_CHECKING
from entity import Actor

import tcod
import util.calc_functions as cf
import components.ai
import exceptions
import color

from actions import Action, MovementAction

# Action are not durable : each turn, objects are created and destroyed. To keep
# things going on several turn, we choose to use an ai object that remains
# attached to the player/entity
# AI is "just" an action that stick to the entity
# TODO : check if the change of AI can be made directly in MainGameEventHandler
class ExploreAIAction(Action):
    def perform(self) -> None:
        self.engine.player.ai = components.ai.ExploreMap(self.entity, self.entity.ai)
        self.engine.player.ai.perform()

class TravelAIAction(Action):
    def __init__(self, entity: Actor, destination:str) -> None:
        super().__init__(entity)
        self.destination = destination

    def perform(self) -> None:
        self.engine.player.ai = components.ai.MoveTo(self.entity, self.entity.ai, self.destination)
        self.engine.player.ai.perform()
