from __future__ import annotations

import copy
import random

from typing import TYPE_CHECKING

import util.calc_functions as cf

import color
import entity_factories
import components.ai
from exceptions import Dead

from components.base_component import BaseComponent
from components.equippable import RangedWeapon
from render_order import RenderOrder
from actions import ItemAction, DropItem

# if TYPE_CHECKING:
from entity import Actor, Entity, Feature

class Fightable(BaseComponent):
    parent: Entity

    def __init__(self, hp: int, base_defense: int = 0, base_armor: int = 0, base_attack: int = 0):
        self.max_hp = hp
        self._hp = hp*100
        self.base_defense = base_defense
        self.base_armor = base_armor
        self.base_attack = base_attack
        self.stun_point = 0 # TODO : use _sp as float and sp as int, sp = round-(_sp)
        self.regen_rate = 0

    @property
    def hp(self) -> int:
        return self._hp//100
    
    @property
    def defense(self) -> int:
        return max(0,self.base_defense + self.defense_bonus - self.stun_point//3 - (self.max_hp-self.hp)//6)

    @property
    def armor(self) -> int:
        return self.base_armor + self.armor_bonus

    @property
    def attack(self) -> int:
        return max(0,self.base_attack + self.attack_bonus - self.stun_point//3 - (self.max_hp-self.hp)//6)


    @property
    def defense_bonus(self) -> int:
        if isinstance(self.parent, Actor):
            if self.parent.equipment:
                return self.parent.equipment.defense_bonus

        return 0

    @property
    def armor_bonus(self) -> int:
        if isinstance(self.parent, Actor):
            if self.parent.equipment:
                return self.parent.equipment.armor_bonus

        return 0

    @property
    def attack_bonus(self) -> int:
        if isinstance(self.parent, Actor):
            if self.parent.equipment:
                return self.parent.equipment.attack_bonus
        
        return 0

    @hp.setter
    def hp(self, value: int) -> None:
        self._hp = max(0, min(value*100, self.max_hp*100))
        if self.hp <= 0: #and self.parent.ai:
            self.die()

    def die(self) -> None:
        raise NotImplementedError
        
    def heal(self, amount: int) -> int:
        if self.hp == self.max_hp:
            return 0

        heal_value = min(self.max_hp*100, self._hp + amount*100) - self._hp
        self._hp += heal_value

        return heal_value//100

    def take_damage(self, amount:int) -> None:
        self.hp -= amount

    def take_stun(self, amount:int) -> None:
        self.stun_point += amount

    def recover_stun(self, amount:int) -> None:
        self.stun_point = max(0, self.stun_point-amount)


class Fighter(Fightable):
    parent: Actor

    def __init__(self, hp: int, base_defense: int = 0, base_armor: int = 0, base_attack: int = 0, regen_rate: int = 20):
        super().__init__(hp, base_defense, base_armor, base_attack)
        self.regen_rate: int = regen_rate # for 100 turns

    def die(self) -> None:
        death_message = None
        if self.engine.player is self.parent:
            death_message = "You died!"
            death_message_color = color.player_die
        else:
            if self.parent.is_visible:
                death_message = f"{self.parent.name} is dead!"
                death_message_color = color.enemy_die
            else:
                if self.parent.size.value > 3:
                    death_message = f"Something seems dead!"
                    death_message_color = color.enemy_die
        if death_message:
            self.engine.message_log.add_message(death_message,death_message_color)

        self.parent.render_order = RenderOrder.CORPSE

        # Drop inventory
        if self.parent.inventory.items:
            for item in self.parent.inventory.items:
                # DropItem(self.parent, item).perform()
                self.parent.inventory.items.remove(item)
                item.place(self.parent.x, self.parent.y, self.gamemap)
            if self.parent == self.engine.player:
                msg = f"You dropped your inventory."
            else:
                msg = f"The {self.parent.name} drops its inventory."
            self.engine.message_log.add_message(msg)

        if self.engine.player is self.parent:
            raise Dead

        self.parent.ai = components.ai.BaseAI(self.parent)
        self.engine.player.level.add_xp(self.parent.level.xp_given)
        self.parent.char="†"
        self.parent.char="%"
        self.parent.blocks_movement = False
        self.parent.name = f"remains of {self.parent.name}"
        self.engine.turnqueue.unschedule(self.parent, self.engine.active_entity)

    def regen_hp(self, turn:int = 1) -> None:
        if self.hp == self.max_hp:
            return 0

        regen_value = min(self.max_hp*100, self._hp + self.regen_rate*turn) - self._hp
        self._hp += regen_value


class Barrel(Fightable):
    parent: Feature
    
    def die(self) -> None:
        death_message = f"{self.parent.name} explodes!"
        death_message_color = color.enemy_die

        self.engine.message_log.add_message(death_message,death_message_color)
 
        # seems the simplest turnaround
        grenade_launcher = copy.deepcopy(entity_factories.grenade_launcher)
        grenade_launcher.parent = self.gamemap
        item_action = ItemAction(self.parent, grenade_launcher)
        grenade_launcher.equippable.activate(item_action)

        self.parent.remove()

class ToxicBarrel(Fightable):
    parent: Feature

    def __init__(self, hp: int, base_defense: int = 0, base_attack: int = 0, radius: int = 1):
        super().__init__(hp, base_defense, base_attack)
        self.radius = radius

    def die(self) -> None:
        death_message = f"{self.parent.name} explodes!"
        death_message_color = color.enemy_die

        self.engine.message_log.add_message(death_message,death_message_color)
        self.parent.remove()

        # seems the simplest turnaround
        grenade_launcher = copy.deepcopy(entity_factories.grenade_launcher)
        grenade_launcher.parent = self.gamemap
        item_action = ItemAction(self.parent, grenade_launcher)
        grenade_launcher.equippable.activate(item_action)

        # smoke cloud gen
        entity = entity_factories.toxic_smoke
        for (x,y) in cf.disk_coords((self.parent.x, self.parent.y), self.radius):
            if self.gamemap.tiles["walkable"][x,y]:
                smoke = entity.spawn(self.gamemap,x,y)
                smoke.ai = components.ai.Vanish(entity=smoke, previous_ai=smoke.ai, turns_remaining=4+random.randint(-1,1),)

class ExplosiveBarrel(Fightable):
    parent: Feature

    def __init__(self, hp: int, base_defense: int = 0, base_attack: int = 0, radius: int = 1):
        super().__init__(hp, base_defense, base_attack)
        self.radius = radius

    def die(self) -> None:
        death_message = f"{self.parent.name} explodes!"
        death_message_color = color.enemy_die

        self.engine.message_log.add_message(death_message,death_message_color)
        self.parent.remove()

        # seems the simplest turnaround
        grenade_launcher = copy.deepcopy(entity_factories.grenade_launcher)
        grenade_launcher.parent = self.gamemap
        
        self.gamemap.hostile_lof.compute(shooter=self.parent,target_xy=(self.parent.x,self.parent.y))
        item_action = ItemAction(entity=self.parent, item=grenade_launcher) # TODO : self.parent already removed... but self.parent = barrel and item = grenade_laucher
        grenade_launcher.equippable.activate(item_action)

        # smoke cloud gen
        entity = entity_factories.fire_cloud
        for (x,y) in cf.disk_coords((self.parent.x, self.parent.y), self.radius):
            if self.gamemap.tiles["walkable"][x,y]:
                smoke = entity.spawn(self.gamemap,x,y)
                smoke.ai = components.ai.Vanish(entity=smoke, previous_ai=smoke.ai, turns_remaining=10+random.randint(-2,2),)

class Smoke(Fightable): # does it need to be a Fightable? I don't think so
    parent: Feature

    def take_damage(self, amount:int) -> None:
        return

    @property
    def attack_bonus(self) -> int:
        return 0

    def die(self) -> None:
        self.engine.turnqueue.unschedule(self.parent, self.engine.active_entity)

class ToxicSmoke(Fightable):
    parent: Feature

    def take_damage(self, amount:int) -> None:
        return

    @property
    def attack_bonus(self) -> int:
        return 0

    def die(self) -> None:
        self.engine.turnqueue.unschedule(self.parent, self.engine.active_entity)

class FireCloud(Fightable):
    parent: Feature

    def take_damage(self, amount:int) -> None:
        return

    @property
    def attack_bonus(self) -> int:
        return 0
    
    def die(self) -> None:
        self.engine.turnqueue.unschedule(self.parent, self.engine.active_entity)


