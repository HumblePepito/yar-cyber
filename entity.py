from __future__ import annotations

import copy
import math
from typing import Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union

from various_enum import ItemType, RenderOrder, SizeClass


if TYPE_CHECKING:
    from components.ai import BaseAI
    from components.fightable import Fighter, Fightable
    from components.equipment import Equipment
    from components.consumable import Consumable
    from components.equippable import Equippable
    from components.activable import Activable
    from components.inventory import Inventory
    from game_map import GameMap
    from components.level import Level

T = TypeVar("T", bound="Entity")


class Entity:
    """
    A generic object to represent players, enemies, items, etc.
    TODO : how to combine diffrent ai ? => different slots, ai through component (ai is already a component) ?
    """

    parent: Union[GameMap,Inventory]

    def __init__(
        self,
        parent: Optional[GameMap] = None, # TODO, careful : I plan this to default to the gammap instead of None
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        blocks_movement: bool = False,
        render_order: RenderOrder = RenderOrder.CORPSE,
        size: SizeClass = SizeClass.MEDIUM,
    ):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks_movement = blocks_movement
        self.render_order = render_order
        self.size = size
        if parent:
            # If parent isn't provided now then it will be set later.
            self.parent = parent
            parent.entities.add(self)

    @property
    def gamemap(self) -> GameMap:
        return self.parent.gamemap

    @property
    def is_visible(self) -> bool:
        """Entity is visible in the FOV"""
        if self.depth == self.gamemap.engine.game_world.current_floor:
            return self.gamemap.visible[self.x, self.y]

    @property
    def is_actor(self) -> bool:
        return isinstance(self, Actor)

    @property
    def depth(self) -> int:
        return self.gamemap.depth

    def spawn(self: T, gamemap: GameMap, x: int, y: int) -> T:
        """Spawn a copy of this instance at the given location."""
        clone = copy.deepcopy(self)
        clone.x = x
        clone.y = y
        clone.parent = gamemap
        gamemap.entities.add(clone)

        # at init, place itself into the turnqueue
        if isinstance(self, Actor) or isinstance(self,Hazard):
            # current_time = 0
            # if gamemap.engine.turnqueue.heap:
            #     current_time = gamemap.engine.turnqueue.heap[0].time
            gamemap.engine.turnqueue.schedule(0, clone)  

        return clone

    def place(self, x: int, y: int, gamemap: Optional[GameMap] = None) -> None:
        """Place this entity at a new location.  Handles moving across GameMaps."""
        self.x = x
        self.y = y
        if gamemap:
            # je ne sais pas pourquoi : ces 3 lignes font une erreur KeyError: <entity.Item object at 0x7f0301f4c6d0>
            # et je ne sais pas à quoi elles servent
            # if hasattr(self, "parent"):  # Possibly uninitialized.
            #     if self.parent is self.gamemap:
            #         self.gamemap.entities.remove(self)
            self.parent = gamemap
            gamemap.entities.add(self)

    def distance(self,x:int, y:int) -> float:
        """Chebyshev distance between player and x,y coordinates"""
        #return math.sqrt((self.x-x)**2+(self.y-y)**2)
        return max(abs(self.x-x), abs(self.y-y)) # Chebyshev distance.

    def move(self, dx: int, dy: int) -> None:
        # Move the entity by a given amount
        self.x += dx
        self.y += dy

    def remove (self) -> None:
        # je suppose que Gamemap est initialisé... cf les 3 lignes en commentaires hasattr...
        self.gamemap.entities.remove(self)


    def get_nearest_actor(self) -> Optional[Actor]:
        min_dist: float = 10
        dist: float = 0
        target: Actor = None

        for actor in set(self.gamemap.visible_actors) - {self}:
            dist = self.distance(actor.x, actor.y)
            if dist < min_dist and actor.is_alive:
                min_dist = dist
                target = actor

        return target


class Actor(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        ai_cls: Type[BaseAI],
        equipment: Equipment,
        fightable: Fighter,
        inventory: Inventory,
        level: Level,
        size: SizeClass = SizeClass.MEDIUM,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=True,
            size=size,
            render_order=RenderOrder.ACTOR,
        )

        self.ai: Optional[BaseAI] = ai_cls(self)
        self.equipment: Equipment = equipment
        self.equipment.parent = self
        self.fightable = fightable
        self.fightable.parent = self
        self.inventory: Inventory = inventory
        self.inventory.parent = self
        self.level = level
        self.level.parent = self

        self.bend = ""
        self.auto_pickup = True
        self.auto_pickup_list = []
        self.hunker_stack = 0
        self.aim_stack = 0
        self.effects = {}
        self.base_speed = 60  # by default, every action take 60

    @property
    def is_alive(self) -> bool:
        """Returns True as long as this actor can perform actions."""
        return bool(self.fightable.hp)
    
    @property
    def see_actor(self) -> bool:
        return bool(set(self.gamemap.visible_actors)-{self})   

    @property
    def action_speed(self) -> int:
        return self.base_speed + self.fightable.stun_point//3 + (self.fightable.max_hp-self.fightable.hp)//6


# TODO : consumable and equippable can also be two different classes for specialization sake (<> simplicity)
class Item(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        item_type: ItemType = ItemType.ITEM,
        consumable: Optional[Consumable] = None,
        equippable: Optional[Equippable] = None,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=False,
            render_order=RenderOrder.ITEM,
        )
        self.item_type = item_type
        self.consumable = consumable
        if self.consumable:
            self.consumable.parent = self
        self.equippable = equippable
        if self.equippable:
            self.equippable.parent = self        

class Feature(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        render_order=RenderOrder.ITEM,
        activable: Optional[Activable] = None, # doors, buttons, terminals, comlink, lift, etc
        fightable: Optional[Fightable] = Entity(),
        blocks_movement=True,
        blocks_view = False,
        blocks_stack = False,
        pushable = False,
        size: SizeClass = SizeClass.MEDIUM,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=blocks_movement,
            render_order=render_order,
            size=size,
        )
        self.activable = activable
        self.fightable = fightable
        self.fightable.parent = self
        self.blocks_view = blocks_view
        self.blocks_stack = blocks_stack
        self.pushable = pushable

class Hazard(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        render_order=RenderOrder.CLOUD,
        ai_cls: Type[BaseAI],
        fightable: Optional[Fightable] = Entity(),
        blocks_movement=True,
        blocks_view = False,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=blocks_movement,
            render_order=render_order,
        )
        self.ai: Optional[BaseAI] = ai_cls(self)
        self.fightable = fightable
        self.fightable.parent = self
        self.blocks_view = blocks_view
        self.base_speed = 60  # by default, every action take 60

    @property
    def is_alive(self) -> bool:
        """Returns True as long as this actor can perform actions."""
        return bool(self.fightable.hp)
    
    @property
    def action_speed(self) -> int:
        return self.base_speed
    