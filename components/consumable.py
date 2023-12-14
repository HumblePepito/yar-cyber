from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import actions
import color
import components.ai

from components.inventory import Inventory
from components.base_component import BaseComponent
from exceptions import Impossible
from input_handlers import SingleRangedAttackHandler, AreaRangedAttackHandler, ActionOrHandler
from various_enum import EffectType

if TYPE_CHECKING:
    from entity import Actor, Item

class Consumable(BaseComponent):
    parent: Item

    def get_action(self, consumer: Actor) -> Optional[ActionOrHandler]:
        """Try to return the action for this item."""
        return actions.ItemAction(consumer, self.parent)
    
    def activate(self, action: actions.ItemAction) -> None:
        """ Invoke this item ability 
        
        action is the context for this activation"""
        raise NotImplementedError()
    
    def consume(self) -> None:
        """Remove the consumed item from its containing inventory."""
        entity = self.parent
        inventory = entity.parent

        if isinstance(inventory, Inventory):
            inventory.items.remove(entity) 
        #self.engine.player.inventory.items.remove(entity) # là, c'est sûr que c'est un Inventory
    
class HealingConsumable(Consumable):
    def __init__(self, amount: int):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        amount_recovered = consumer.fightable.heal(self.amount)

        if amount_recovered > 0:
            self.engine.message_log.add_message(
                f"You consume the {self.parent.name}, and recover {amount_recovered} HP!",color.health_recovered
            )
            self.consume()
        else:
            raise Impossible("Your health is already full." )

class SpeedConsumable(Consumable):
    def __init__(self, duration: int, speed:int):
        self.duration = duration
        self.speed = speed

    def activate(self, action: actions.ItemAction) -> None:
        action.entity.effects[EffectType.SPEED.value] = {"duration": self.duration, "speed": self.speed, "name": "Speed"}
        self.consume()


class LightningDamageConsumable(Consumable):
    def __init__(self, damage: int):
        self.damage = damage

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        # nearest monster
        min_dist: float = 10
        dist: float = 0
        target: Actor = None

        for actor in set(self.engine.game_map.visible_actors) - {consumer}:
            dist = consumer.distance(actor.x, actor.y)
            if dist < min_dist:
                min_dist = dist
                target = actor
        
        if target:
            self.engine.message_log.add_message(
                f"A lighting bolt strikes the {target.name} with a loud thunder, for {self.damage} damage!"
            )
            target.fightable.take_damage(self.damage)
            self.consume()
        else:
            raise Impossible("No valid target.")

class ConfusionConsumable(Consumable):
    def __init__(self, number_of_turns: int):
        self.number_of_turns = number_of_turns

    def get_action(self, consumer: Actor) -> Optional[ActionOrHandler]:
        """ Complete the call to ItemAction with the (x,y) coordinates of the SelectIndexHandler."""
        self.engine.message_log.add_message(
            "Select a target location.", color.needs_target
        )
        return SingleRangedAttackHandler(
            self.engine,
            callback=lambda xy: actions.ItemAction(consumer, self.parent, xy),
        )
        # lambda = inline anonymous function 
        #     Called by callback(xy) => return the ItemAction with the parameter xy"

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        target = action.target_actor

        if not target:
            raise Impossible("You must select an enemy to target.")
        if target is consumer:
            raise Impossible("You cannot confuse yourself.")

        self.engine.message_log.add_message(
            f"The eyes of the {target.name} look vacant, as it starts to stumble around!",
            color.status_effect_applied,
        )
        target.ai = components.ai.ConfusedEnemy(
            entity=target, previous_ai=target.ai, turns_remaining=self.number_of_turns,
        )
        self.consume()

class FireballConsumable(Consumable):
    def __init__(self, radius: int, damage: int):
        self.radius = radius
        self.damage = damage

    def get_action(self, consumer: Actor) -> Optional[ActionOrHandler]:
        self.engine.message_log.add_message(
            "Select a target location.", color.needs_target
        )
        return AreaRangedAttackHandler(
            self.engine,
            self.radius,
            callback=lambda xy: actions.ItemAction(consumer, self.parent, xy),
        )
    
    def activate(self, action: actions.ItemAction) -> None:
        target_xy = action.target_xy

        if not self.engine.game_map.visible[target_xy]:
            raise Impossible("You cannot target an area that you cannot see.")

        targets_hit = False
        for actor in self.engine.game_map.actors:
            if actor.distance(*target_xy) <= self.radius:
                if actor.is_visible:
                    self.engine.message_log.add_message(
                        f"The {actor.name} is engulfed in a fiery explosion, taking {self.damage} damage!"
                    )
                else:
                    self.engine.message_log.add_message(
                        f"Your hear a nearby screaming."
                    )
                actor.fightable.take_damage(self.damage)
                targets_hit = True

        if not targets_hit:
            raise Impossible("There are no targets in the radius.")
        
        self.consume()

