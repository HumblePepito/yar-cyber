from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

import copy
import random

from components.base_component import BaseComponent
from exceptions import Impossible

from components.equippable import RangedWeapon

if TYPE_CHECKING:
    from entity import Actor, Item

class Inventory(BaseComponent):
    parent: Actor

    def __init__(self, capacity:int, initial_inventory: List[Item] = []):
        self.capacity = capacity
        self.items: List[Item] = []

        # if len(initial_inventory) > initial_size:
        #     # reduce to one only
        #     item = random.choice(initial_inventory)
        #     initial_inventory = [item]

        # at creation of entity, put all items in inventory. Except for player, purge will be done when placing Actors in procgen
        for initial_item in initial_inventory:
            if initial_item:
                clone = copy.deepcopy(initial_item)
                clone.parent = self
                self.add(clone)

    def drop(self, item:Item) -> None:
        self.items.remove(item)
        item.place(self.parent.x, self.parent.y, self.gamemap)

        if self.parent == self.engine.player:
            msg = f"You dropped the {item.name}."
        else:
            msg = f"The {self.parent.name} drops the {item.name}."

        self.engine.message_log.add_message(msg)

        # self.engine.message_log.add_message(f"You dropped the {item.name}.")

    def droplast(self) -> None:
        try:
            last_item:Item = self.items.pop()
            if self.parent.equipment.item_is_equipped(last_item):  #unequipe item
                self.parent.equipment.toggle_equip(last_item)
            
            last_item.place(self.parent.x, self.parent.y, self.gamemap)
            self.engine.message_log.add_message(f"You dropped the {last_item.name}.")
        except IndexError:
            raise Impossible("No item to drop.")

    def add(self, item:Item) -> None:
        self.items.append(item)

    def get_first_weapon(self) -> Item:
        # return self.items[0]
        for item in self.items:
            if isinstance(item.equippable, RangedWeapon):
                return item

        return None

        