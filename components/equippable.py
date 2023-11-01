from __future__ import annotations

import math, random

from typing import Optional, Tuple, TYPE_CHECKING

import actions
import color
import time
import tcod.los

import util.calc_functions as cf

from components.base_component import BaseComponent
from various_enum import EquipmentSlot, SizeClass

from input_handlers import SingleRangedAttackHandler, AreaRangedAttackHandler, ActionOrHandler
from exceptions import Impossible

if TYPE_CHECKING:
    from entity import Actor, Entity, Item

class Equippable(BaseComponent):
    parent: Item

    def __init__(
        self,
        equipment_type: EquipmentSlot,
        attack_bonus: int = 0,
        armor_bonus: int = 0,
    ):
        self.equipment_type = equipment_type # add equipment slot
        self.attack_bonus = attack_bonus
        self.armor_bonus = armor_bonus
        self.is_ranged = False # TODO : or an enum of value to define the different weapon
    
class RangedWeapon(Equippable):
    """ item, equippable with its set of attributes"""
    # TODO : I keep parent: Item, should we change to parent: Equippable ??  My guess : no because Equippable is "just" a component.

    def __init__(
        self,
        equipment_type: EquipmentSlot,
        attack_bonus: int = 0,
        base_damage: int = 1,
        base_range: int = 0,
        clip_size: int=0,
        radius: int = None,
    ):
        super().__init__(equipment_type=equipment_type, attack_bonus=attack_bonus)
        self.base_damage = base_damage
        self.base_range = base_range
        self.clip_size = clip_size
        self.radius = radius
        self.is_ranged   = True
        self.current_clip = clip_size
    
    def get_fire_action(self, shooter: Actor) -> Optional[ActionOrHandler]:
        self.engine.message_log.add_message(
            "Select a target location.", color.needs_target
        )

        if self.current_clip == 0:
            self.engine.message_log.add_message("No more ammo. Reload.")
            return

        if self.radius:
            return AreaRangedAttackHandler(
                self.engine,
                self.radius,
                callback=lambda xy: actions.ItemAction(shooter, self.parent, xy),
                default_select="enemy",
                extra_confirm="f",
            )

        else:
            return SingleRangedAttackHandler(
                self.engine,
                callback=lambda xy: actions.ItemAction(shooter, self.parent, xy),
                default_select="enemy",
                extra_confirm="f",
            )
        
        
    def activate(self, action: actions.ItemAction) -> None:
        target_xy = action.target_xy
        shooter = action.entity
        target = action.target_actor # either Actor, Item or None

        if not self.engine.game_map.visible[target_xy]:
            raise Impossible("You cannot target an area that you cannot see.")

        if shooter.distance(*target_xy) > self.base_range:
            raise Impossible("Target is too far away.")

        hit_margin, target = self.hit_calculation(shooter, target)

        if hit_margin is not None:
            if self.engine.renderer:
                context = self.engine.renderer.context
                console = self.engine.renderer.console
            else:
                raise NotImplementedError                    
            # console.clear()
            # self.engine.render(self.engine.renderer)

            if self.radius is not None: # self radius can be 0 for a on square only effet
                # TODO : howto join 2 generator ? TODO : use onlus cf.disk to avoid parsing the whole map
                for i,j in cf.disk_coords(target_xy,self.radius):
                    blast_target = self.engine.game_map.get_target_at_location(i,j)
                    if blast_target:
                        damage = self.damage_calculation(shooter, blast_target, 0)
                        if blast_target.is_visible:
                            self.engine.message_log.add_message(
                                f"The {blast_target.name} is engulfed in a fiery explosion, taking {damage} damage!"
                            )
                        else:
                            self.engine.message_log.add_message(
                                f"Your hear a nearby screaming."
                            )
                        blast_target.fightable.take_damage(damage)
                # for actor in set(self.engine.game_map.actors) | set(self.engine.game_map.features):
                #     if actor.distance(*target_xy) <= self.radius:
                #         damage = self.damage_calculation(shooter, target, 0)
                #         if actor.is_visible:
                #             self.engine.message_log.add_message(
                #                 f"The {actor.name} is engulfed in a fiery explosion, taking {damage} damage!"
                #             )
                #         else:
                #             self.engine.message_log.add_message(
                #                 f"Your hear a nearby screaming."
                #             )
                #         actor.fightable.take_damage(damage)
                        
                # Animation
                # TODO move to renderer or other dedicated module/class
                # call draw_line, draw_explosion, draw_bullet, draw_xxx with origin, target, color, char, delay,...
                fire_line = tcod.los.bresenham((shooter.x, shooter.y),target_xy).tolist()
                fire_line.pop(0)
                for [i, j] in fire_line:
                    if self.engine.game_map.get_target_at_location(i, j):
                        console.rgb["bg"][self.engine.renderer.shift(i,j)] = color.n_red
                        console.rgb["fg"][self.engine.renderer.shift(i,j)] = color.white
                    else:
                        console.rgb["fg"][self.engine.renderer.shift(i,j)] = color.n_red
                        console.rgb["ch"][self.engine.renderer.shift(i,j)] = ord("*")

                for (x,y) in cf.disk_coords(target_xy, self.radius):
                    console.rgb["fg"][self.engine.renderer.shift(x,y)] = color.n_red  # add color of weapon 
                    console.rgb["ch"][self.engine.renderer.shift(x,y)] = ord("*")
                context.present(console)
                time.sleep(0.05)

            else:
                if target == None:
                    self.engine.message_log.add_message("You shoot an empty space.")
                    self.current_clip -= 1
                    return
                        
                damage = self.damage_calculation(shooter, target,hit_margin)

                # damage = self.attack_bonus - target.fightable.armor
                attack_desc = f"{shooter.name.capitalize()} shoots {target.name}"
                if shooter is self.engine.player:
                    attack_color = color.player_atk
                else:
                    attack_color = color.enemy_atk

                if damage > 0:
                    self.engine.message_log.add_message(f"{attack_desc} for {damage} hit points.",attack_color)
                    target.fightable.hp -= damage
                else:
                    self.engine.message_log.add_message(f"{attack_desc} but does no damage.", attack_color)

                # Animation
                fire_line = tcod.los.bresenham((shooter.x, shooter.y),target_xy).tolist()
                fire_line.pop(0)
                for [i, j] in fire_line:
                    if self.engine.game_map.get_actor_at_location(i, j):
                        console.rgb["bg"][self.engine.renderer.shift(i,j)] = color.n_red
                        console.rgb["fg"][self.engine.renderer.shift(i,j)] = color.white
                    else:
                        console.rgb["fg"][self.engine.renderer.shift(i,j)] = color.n_red
                        console.rgb["ch"][self.engine.renderer.shift(i,j)] = ord("*")
                context.present(console)
                time.sleep(0.05)
        else:
            if target:
                self.engine.message_log.add_message(f"{shooter.name.capitalize()} missed.")
            else:
                self.engine.message_log.add_message(f"{shooter.name.capitalize()} shoots an empty space.")

        # use ammunition
        self.current_clip -= 1

    def hit_calculation(self, shooter: Actor, target: Entity) -> Tuple(int, Entity):
        """ Combat calculation
        Returns
            int: None = missed, >=0 = hit margin
            entity: who is hit"""
        fire_line = self.gamemap.fire_line


        if target:
            base_attack, base_defense, cover = fire_line.get_hit_stat(target)
    
            attack = base_attack # TODO : aiming ? range ? or consecutive shots ? and of course : wounds
            defense = base_defense + cover

            # Roll !
            attack_success = 0
            defense_success = 0
            for i in range(0,attack):
                if random.randint(1,3) == 3:
                    attack_success += 1
            for i in range(0,defense):
                if random.randint(1,3) == 3:
                    defense_success += 1

            hit_margin = attack_success - defense_success
        else:
            hit_margin = 0


        """ Two situations :
        * target is missed
            1. 50% the shot is lost
            2. 50% the shot hit an opponent in between, chances based on size
        * shooter shoots an empty space
            same proportion but instead of a lost shot, the shot reach the target area
        """
        if hit_margin < 0 or (hit_margin == 0 and not target):
            # MISSED or shoorting deliberately behind the target
            if random.randint(0,1) == 0:
                if target:
                    # TODO : take into account global size of cover ? Excluding wall ?
                    # TODO : 50% is more than what you will get with agile opponent. How to avoid this exploit (fire behind) ?
                    hit_margin = None
                    target = None
            else:
                # TODO : increase weight for first targets
                if fire_line.entities:
                    entity_weighted_chance_values = []
                    for entity in fire_line.entities:
                        entity_weighted_chance_values.append(entity.size.value)

                    entity = random.choices(fire_line.entities,entity_weighted_chance_values)
                    hit_margin = 0
                    target = entity[0]
                else:
                    if target:
                        hit_margin = None
                        target = None
                    else:
                        hit_margin = 0

        if target is None and hit_margin is None:
            #TODO : define the hit in fov or out fov
            pass

        return hit_margin, target

    def damage_calculation(self, shooter: Actor, target: Entity, hit_margin) -> int:

        damage = self.base_damage + hit_margin # TODO : bonus ??
        armor = target.fightable.armor # TODO : bonus ?

        for i in range(0,armor):
            if random.randint(1,3) == 3:
               damage -= 1

        return max(0,damage)


# TODO : move to its own file
# TODO : create class of weapon (with default values, including name) and call them with all parameters ??? careful about entity_factory and copies
class Sling(RangedWeapon):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON, base_damage=2, base_range=5, clip_size=1)

class Gun(RangedWeapon):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON,
                         base_damage=3, 
                         base_range=6, 
                         clip_size=8)

class Revolver(RangedWeapon):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON, base_damage=5, base_range=5, clip_size=6)

class Rifle(RangedWeapon):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON, base_damage=6, base_range=10, clip_size=3)

class GrenadeLauncher(RangedWeapon):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON, base_damage=5, base_range=4, clip_size=1, radius=1)

class Dagger(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON, attack_bonus=2) #TODO : attack_bonus vs bae damage for melee weapon


class Sword(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON, attack_bonus=4)


class LeatherArmor(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.ARMOR, armor_bonus=1)


class ChainMail(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.ARMOR, armor_bonus=3)