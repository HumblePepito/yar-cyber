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
from  util.combat import damage_calculation, hit_calculation, stray_fire

from input_handlers import SingleRangedAttackHandler, AreaRangedAttackHandler, ActionOrHandler
from exceptions import Impossible

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
    
class MeleeWeapon(Equippable):
    def __init__(
            self,
            equipment_type: EquipmentSlot,
            attack_bonus: int = 0,
            armor_bonus: int = 0,
            base_damage: int = 1,
    ):
        super().__init__(equipment_type, attack_bonus, armor_bonus)
        self.base_damage = base_damage



class RangedWeapon(Equippable):
    """ Ranged Weapon, attached to an Item of type RANGED_WEAPON.
    Activation is in charge of combat calculations"""

    def __init__(
        self,
        equipment_type: EquipmentSlot,
        attack_bonus: int = 0,
        base_damage: int = 1,
        base_range: int = 1,
        clip_size: int=0,
        radius: int = None,
    ):
        super().__init__(equipment_type=equipment_type, attack_bonus=attack_bonus)
        self.base_damage = base_damage
        self.base_range = base_range
        self.clip_size = clip_size
        self.radius = radius
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
        shooter = action.entity # player or hostile actor
        target = action.target_actor # either Actor, Item or None
        weapon = self.parent

        if not self.engine.game_map.visible[target_xy]:
            raise Impossible("You cannot target an area that you cannot see.")

        fire_line = self.gamemap.get_fire_line(shooter)

        hit_margin, target = hit_calculation(shooter, target)
        if hit_margin < 0 or (hit_margin == 0 and not target):
            # MISSED or shoorting deliberately behind the target
            hit_margin, target = stray_fire(fire_line)

        if hit_margin is not None:
            if self.engine.renderer:
                context = self.engine.renderer.context
                console = self.engine.renderer.console
            else:
                raise NotImplementedError                    

            if self.radius is not None: # self radius can be 0 for a on square only effet
                # TODO : howto join 2 generator ? TODO : use onlus cf.disk to avoid parsing the whole map
                for i,j in cf.disk_coords(target_xy,self.radius):
                    blast_target = self.engine.game_map.get_target_at_location(i,j)
                    if blast_target:
                        damage, armor_reduction = damage_calculation(weapon, blast_target, 0)
                        if blast_target.is_visible:
                            self.engine.message_log.add_message(
                                f"The {blast_target.name} is engulfed in a fiery explosion, taking {damage} damage!"
                            )
                        else:
                            self.engine.message_log.add_message(
                                f"Your hear a nearby screaming."
                            )
                        blast_target.fightable.take_damage(damage)
                        
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
                    if self.engine.game_map.tiles["walkable"][x,y] and self.engine.game_map.visible[x,y]:
                        console.rgb["fg"][self.engine.renderer.shift(x,y)] = color.n_red  # add color of weapon 
                        console.rgb["ch"][self.engine.renderer.shift(x,y)] = ord("*")
                context.present(console, keep_aspect= True, integer_scaling=True)
                time.sleep(0.05)

            else:
                if target == None:
                    self.engine.message_log.add_message(f"{shooter.name.capitalize()} shoots an empty space.")
                    self.current_clip -= 1
                    return

                if target.name == "Wall":
                    self.engine.message_log.add_message(f"{shooter.name.capitalize()}'s shot hits the wall!.")
                    self.current_clip -= 1
                    return

                damage, armor_reduction = damage_calculation(weapon, target, hit_margin)

                # damage = self.attack_bonus - target.fightable.armor
                attack_desc = f"{shooter.name.capitalize()} shoots {target.name}"
                if shooter is self.engine.player:
                    attack_color = color.player_atk
                else:
                    attack_color = color.enemy_atk


                if damage > target.fightable.armor:
                    self.engine.message_log.add_message(f"{attack_desc} for {max(0, damage-armor_reduction)} hit points.",attack_color)
                    target.fightable.hp -= max(0, damage-armor_reduction)
                else:
                    self.engine.message_log.add_message(f"{attack_desc} for {max(0, damage-armor_reduction)} stun points.",attack_color)
                    target.fightable.sp += max(0, damage-armor_reduction)

                # Animation
                for [i, j] in fire_line.path:
                    if self.engine.game_map.get_actor_at_location(i, j):
                        console.rgb["bg"][self.engine.renderer.shift(i,j)] = color.n_red
                        console.rgb["fg"][self.engine.renderer.shift(i,j)] = color.white
                    else:
                        console.rgb["fg"][self.engine.renderer.shift(i,j)] = color.n_red
                        console.rgb["ch"][self.engine.renderer.shift(i,j)] = ord("*")
                context.present(console, keep_aspect= True, integer_scaling=True)
                time.sleep(0.05)
        else:
            if target:
                self.engine.message_log.add_message(f"{shooter.name.capitalize()} missed.")
            else:
                self.engine.message_log.add_message(f"{shooter.name.capitalize()} shoots an empty space.")

        # use ammunition
        self.current_clip -= 1

        # log combat information
        if self.engine.logger.level <= 20:    # 20 for INFO messages
            if target and target.name != "Wall": 
                lof = self.gamemap.get_fire_line(shooter=shooter)
                ATT, DEF, COV = lof.get_hit_stat(target_xy=(target.x, target.y),target=target)
                try:
                    armor_suit = target.equipment.armor_suit.name
                except AttributeError:
                    armor_suit = "None"                
                self.engine.logger.info(msg=f"*** {shooter.name.upper()} fights {target.name.upper()}.")
                self.engine.logger.info(msg=f"Shooter - ATT:{ATT} WEAPON:{self.parent.name}({self.base_damage})")
                self.engine.logger.info(msg=f"Shooter - bend:{shooter.bend}")
                self.engine.logger.info(msg=f"Target  - DEF:{DEF} COV:{COV} {[entity.name for entity in lof.entities]}")
                self.engine.logger.info(msg=f"Target  - AC: {target.fightable.armor} SUIT:{armor_suit}") #{if isinstance(target.equipment.}.")
                self.engine.logger.info(msg=f"HitMargin:{hit_margin} Damage:{damage}")                

        return hit_margin, target

# TODO : move to its own file
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
        super().__init__(equipment_type=EquipmentSlot.WEAPON, base_damage=5, base_range=4, clip_size=6)

class Rifle(RangedWeapon):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON, base_damage=6, base_range=10, clip_size=3)

class GrenadeLauncher(RangedWeapon):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON, base_damage=5, base_range=4, clip_size=1, radius=1)

class Dagger(MeleeWeapon):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON, attack_bonus=3, base_damage = 2)


class Sword(MeleeWeapon):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.WEAPON, attack_bonus=1, base_damage = 5)


class LeatherArmor(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.ARMOR, armor_bonus=3)


class ChainMail(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentSlot.ARMOR, armor_bonus=6)
