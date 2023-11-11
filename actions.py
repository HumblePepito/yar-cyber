from __future__ import annotations

import numpy as np
import time
import random

from typing import List, Optional, Tuple, TYPE_CHECKING
from entity import Actor
from various_enum import ItemType

import exceptions
import color
import tcod

if TYPE_CHECKING:
    from engine import Engine
    from entity import Actor, Entity, Item
    from components.equippable import RangedWeapon


class Action:
    def __init__(self, entity: Actor) -> None:
        super().__init__()
        self.entity = entity

    @property
    def engine(self) -> Engine:
        """Return the engine this action belongs to."""
        return self.entity.gamemap.engine

    def perform(self) -> None:
        """Perform this action with the objects needed to determine its scope.
        `self.engine` is the scope this action is being performed in.
        `self.entity` is the object performing the action.
        This method must be overridden by Action subclasses.
        """
        raise NotImplementedError()

class PickupAction(Action):
    def __init__(self, entity:Actor, item: Optional[Item] = None) -> None:
        super().__init__(entity)
        self.item = item
    
    def perform(self) -> None:
        if self.item:
            item = self.item    
        else:
            item:Item = self.engine.game_map.get_item_at_location(self.entity.x, self.entity.y)
        
        if item:
            if len(self.entity.inventory.items) < self.entity.inventory.capacity:
                self.entity.inventory.add(item)
                item.parent = self.entity.inventory
                self.engine.message_log.add_message(f"You put the {item.name} in the inventory.")
                # suppression de l'objet sur game_map
                #self.engine.game_map.entities.remove(item)
                item.remove()
            else:
                raise exceptions.Impossible("Your inventory is full.")
        else:
            raise exceptions.Impossible("No object to pickup here.")

class ItemAction(Action):
    def __init__(self, entity: Actor, item: Item, target_xy: Optional[Tuple[int,int]] = None):
        super().__init__(entity)
        self.item = item
        if not target_xy:
            target_xy = entity.x, entity.y
        self.target_xy = target_xy
    
    @property
    def target_actor(self) -> Optional[Entity]:
        """Return the actor or the feature at the desired destination"""        
        target = self.engine.game_map.get_target_at_location(*self.target_xy)
        return target        

    def perform(self) -> None:
        """Invoke the items ability, this action will be given to provide context."""
        # TODO : warning, activate is not for all equippable
        if self.item.equippable:
            self.item.equippable.activate(self)  # TODO : check if still relevant
        if self.item.consumable:
            self.item.consumable.activate(self)

class DropItem(ItemAction):
    def perform(self) -> None:
        if self.entity.equipment.item_is_equipped(self.item):
            self.entity.equipment.toggle_equip(self.item)
        self.entity.inventory.drop(self.item)


class DropLastAction(Action):    
    def perform(self) -> None:
        # unequip in inventory, not here      
        self.entity.inventory.droplast()

class EquipAction(Action):
    def __init__(self, entity: Actor, item: Item):
        super().__init__(entity)

        self.item = item

    def perform(self) -> None:
        self.entity.equipment.toggle_equip(self.item)

class WaitAction(Action):
    """ Wait also improve efficiency of cover and add aim bonus"""
    def perform(self) -> None:
        self.entity.hunker_stack = min(self.entity.hunker_stack+1, 2)
        self.entity.aim_stack = min(self.entity.aim_stack+1, 3)

class DescendAction(Action):
    def __init__(self, entity:Actor) -> None:
        super().__init__(entity)
    
    def perform(self) -> None:
        """
        Take the stairs, if any exist at the entity's location.
        """
        #if self.engine.game_map.tiles[self.entity.x, self.entity.y] == tile_types.down_stairs:
        if (self.entity.x, self.entity.y) == self.engine.game_map.downstairs_location:
            self.engine.game_world.generate_floor()
            self.engine.renderer.camera.x = self.engine.renderer.x = self.engine.player.x
            self.engine.renderer.camera.y = self.engine.renderer.y = self.engine.player.y
            self.engine.message_log.add_message(
                "You descend the staircase.", color.descend
            )

        else:
            raise exceptions.Impossible("There are no stairs here.")

class AscendAction(Action):
    
    def perform(self) -> None:
        """
        Escape upstairs, if any exist at the entity's location.
        """
        #if self.engine.game_map.tiles[self.entity.x, self.entity.y] == tile_types.down_stairs:
        if (self.entity.x, self.entity.y) == self.engine.game_map.upstairs_location:
            #self.engine.game_world.generate_floor()
            self.engine.message_log.add_message(
                "You can't escape.", color.descend
            )

        else:
            raise exceptions.Impossible("There are no stairs here.")

class ActionWithDirection(Action):

    def __init__(self, entity: Actor, dx: int, dy: int):
        super().__init__(entity)
        self.dx = dx
        self.dy = dy

    @property
    def dest_xy(self) -> Tuple[int, int]:
        """Returns this actions destination."""
        return self.entity.x + self.dx, self.entity.y + self.dy

    @property
    def blocking_entity(self) -> Optional[Entity]:
        """Return the blocking entity at this actions destination."""
        return self.engine.game_map.get_blocking_entity_at_location(*self.dest_xy)
    
    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this actions destination."""
        return self.engine.game_map.get_actor_at_location(*self.dest_xy)

    def perform(self) -> None:
        raise NotImplementedError()


class MeleeAction(ActionWithDirection):
    
    def perform(self) -> None:

        target = self.target_actor
        
        if not target:
            raise exceptions.Impossible("Nothing to attack.")

        fire_line = self.engine.game_map.get_fire_line(self.entity)
        base_attack, base_defense, cover = fire_line.get_hit_stat((target.x,target.y),target)

        # TODO : extra modifiers (most are in get_hit_stat)
        attack = base_attack
        defense = base_defense

        # Roll !
        attack_success = 0
        defense_success = 0
        for i in range(0,attack):
            if random.randint(1,3) == 3:
                attack_success += 1
        for i in range(0,defense):
            if random.randint(1,3) == 3:
                defense_success += 1
        
        self.engine.logger.debug(f"Att:{attack_success} success on {attack}, Def:{defense_success} on {defense}")


        if attack_success:
            hit_margin = attack_success - defense_success
        else:
            hit_margin = -1 # no success is always a miss

        attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
        if self.entity is self.engine.player:
            attack_color = color.player_atk
        else:
            attack_color = color.enemy_atk

        if hit_margin >= 0:
            damage = self.entity.fightable.attack + hit_margin

            self.engine.message_log.add_message(f"{attack_desc} for {damage} hit points.",attack_color)
            target.fightable.hp -= damage
        else:
            self.engine.message_log.add_message(f"{attack_desc} but missed.", attack_color)

        
        # damage = self.entity.fightable.attack - target.fightable.armor
        # attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
        # if self.entity is self.engine.player:
        #     attack_color = color.player_atk
        # else:
        #     attack_color = color.enemy_atk

        # if damage > 0:
        #     self.engine.message_log.add_message(f"{attack_desc} for {damage} hit points.",attack_color)
        #     target.fightable.hp -= damage
        # else:
        #     self.engine.message_log.add_message(f"{attack_desc} but does no damage.", attack_color)


class MovementAction(ActionWithDirection):
    
    def perform(self) -> None:
        dest_x, dest_y = self.dest_xy

        if not self.engine.game_map.in_bounds(dest_x, dest_y):
            raise exceptions.Impossible("Destination is out of bounds.")
        if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
            raise exceptions.Impossible("Destination is blocked by a tile.")
        if self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y):
            raise exceptions.Impossible("Destination is blocked by an entity... impossible ?? (vs MeleeAction)")

        self.entity.move(self.dx, self.dy)
         
        # Player only : camera and pickup (for monster, check ai)
        if self.engine.player == self.entity:
            self.engine.renderer.camera.move(self.dx, self.dy)
            # while ( self.engine.game_map.get_item_at_location(self.entity.x, self.entity.y)
            #         and self.entity.auto_pickup
            #         and self.engine.game_map.get_item_at_location(self.entity.x, self.entity.y).item_type.value in self.entity.auto_pickup_list):
            #     PickupAction(self.entity).perform()
            items = set(self.engine.game_map.get_items_at_location(self.entity.x, self.entity.y))
            msg = ""
            for item in items:
                if self.entity.auto_pickup_list and item.item_type.value in self.entity.auto_pickup_list:
                    PickupAction(entity=self.entity, item=item).perform()
                else:
                    msg += item.name + ", "
            
            if msg:
                self.engine.message_log.add_message(f"You see: {msg[:-2]}")

class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        #dest_x, dest_y = self.dest_xy

        if self.target_actor:
        #if self.engine.game_map.get_actor_at_location( dest_x, dest_y):
            return MeleeAction(self.entity, self.dx, self.dy).perform()
        else:
            return MovementAction(self.entity, self.dx, self.dy).perform()

class FireAction(Action):
    """ The Fire action fires the equipped ranged weapon on the nearest target unless target is provided
       * Verifies the weapon in hand
       * Gets the item action with a target through get_fire_action
       * Get_fire_action complete the ItemAction with the target through the xxxAttackIndexHandler
       * Resolve damage."""

    def __init__(self, entity: Actor, target: Optional[Actor] = None) -> None:
        super().__init__(entity)
        self.item = entity.equipment.weapon  
        self.target = target 
        try:
            if self.item.item_type == ItemType.RANGED_WEAPON: 
                self.ranged_weapon: RangedWeapon = self.item.equippable
        except AttributeError:
            self.ranged_weapon = None

    def perform(self) -> None:
        if not self.ranged_weapon:
            raise exceptions.Impossible("You must have a working ranged weapon.")
        if self.ranged_weapon.current_clip == 0:
            raise exceptions.Impossible("No more ammo. Reload.") # TODO : what happens for monters ?

        # if self.entity.distance(self.target.x, self.target.y) > self.ranged_weapon.base_range:
        #     raise exceptions.Impossible("Target is too far away.")

        """ fire-line has been computed by
         * either the fire handler
         * either the autottack
         * either the ai
        target is now superseded by the computed target of fire_line
        """
        
        # Instead of dealing directly the damage computation, use fonction from the eqquipable
        fire_line = self.engine.game_map.get_fire_line(self.entity)
        item_action = ItemAction(self.entity, self.ranged_weapon.parent, tuple(fire_line.path[-1]))

        self.ranged_weapon.activate(item_action)

class Reload(Action):
    """Reload equipped weapon."""

    def __init__(self, entity: Actor, target: Optional[Actor] = None) -> None:
        super().__init__(entity)
        self.item = entity.equipment.weapon  
        self.target = target 
        try:
            if self.item.item_type == ItemType.RANGED_WEAPON:
                self.ranged_weapon: RangedWeapon = self.item.equippable
        except AttributeError:
            self.ranged_weapon = None

    def perform(self) -> None:
        if not self.ranged_weapon or self.ranged_weapon.current_clip == self.ranged_weapon.clip_size:
            raise exceptions.Impossible("No weapon to reload.")
        
        self.ranged_weapon.current_clip = self.ranged_weapon.clip_size



class AutoAttack(FireAction):
    def perform(self) -> None:
        if not self.entity.see_actor:
            raise exceptions.Impossible("No enemy in sight.")

        # nearest enemy is target
        target = None
        min_dist = 100
        for actor in set(self.engine.game_map.visible_actors) - {self.entity}:
            dist = self.entity.distance(actor.x, actor.y)
            # TODO : check HP to choose the weakest one than can be dispatched quickly
            if dist < min_dist:
                min_dist = dist
                target = actor

        if target == None:
            raise exceptions.Impossible("No visible target.")
        
        # Melee Weapon  // TODO: deal bare handed fight
        if self.item.item_type == ItemType.MELEE_WEAPON:            
            path = tcod.los.bresenham((self.entity.x, self.entity.y),(target.x, target.y)).tolist()
            # TODO : block in certain situation (through wall)
            x, y = path[1]

            return BumpAction(entity=self.entity, dx=x-self.entity.x, dy=y-self.entity.y).perform()
        # Ranged Weapon
        elif self.item.item_type == ItemType.RANGED_WEAPON:
            if self.entity.distance(target.x, target.y) > self.ranged_weapon.base_range:
                path = tcod.los.bresenham((self.entity.x, self.entity.y),(target.x, target.y)).tolist()
                # TODO : block in certain situation (through wall)
                x, y = path[1]
                return MovementAction(entity=self.entity, dx=x-self.entity.x, dy=y-self.entity.y).perform()
            else:
                self.engine.game_map.player_lof.compute(shooter=self.entity, target_xy=(target.x,target.y))
                return FireAction(self.entity, target).perform()
                
class SwitchAutoPickup(Action):
    def perform(self) -> None:
        self.entity.auto_pickup = not self.entity.auto_pickup
        self.engine.message_log.add_message(f"Autopickup set to {self.entity.auto_pickup}.")

class ChokeAction(Action):

    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this actions destination."""
        return self.engine.game_map.get_actor_at_location(self.entity.x,self.entity.y)

    def perform(self) -> None:

        target = self.target_actor

        damage = self.entity.fightable.attack
        attack_desc = f"The {target.name} chokes in {self.entity.name}"
        if self.entity is self.engine.player:
            attack_color = color.player_atk
        else:
            attack_color = color.enemy_atk

        if damage > 0:
            self.engine.message_log.add_message(f"{attack_desc} for {damage} hit points.",attack_color)
            target.fightable.hp -= damage
        else:
            self.engine.message_log.add_message(f"{attack_desc} but takes no damage.", attack_color)

