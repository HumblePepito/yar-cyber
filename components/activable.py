from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import actions
import color

from game_map import GameMap
from components.base_component import BaseComponent
from exceptions import Impossible
from render_order import RenderOrder
from entity import Feature

if TYPE_CHECKING:
    from entity import Actor, Item

class Activable(BaseComponent):
    parent: Feature

class Destructable(Activable):
    def __init__(self, hp: int, base_defense: int):
        self.max_hp = hp
        self._hp = hp
        self.base_defense = base_defense


    @property
    def hp(self) -> int:
        return self._hp
    
    @property
    def defense(self) -> int:
        return self.defense_bonus

    @hp.setter
    def hp(self, value: int) -> None:
        self._hp = max(0, min(value, self.max_hp))
        if self.hp <= 0:
            self.explode()

    def explode(self) -> None:

        death_message = f"{self.parent.name} is dead!"
        death_message_color = color.enemy_die

        self.parent.char="%"
        self.parent.color = (121, 0, 0)
        self.parent.blocks_movement = False
        self.parent.name = f"remains of {self.parent.name}"
        self.parent.render_order = RenderOrder.CORPSE
        
        self.engine.message_log.add_message(death_message,death_message_color)
