from __future__ import annotations

import random
from typing import Optional, Tuple, TYPE_CHECKING


from entity import Entity, Actor, Item

def roll(pool: int) -> int:
    success = 0
    for i in range(0,pool):
        if random.randint(1,3) == 3:
            success += 1
    return success

def hit_calculation(shooter: Actor, target: Entity) -> Tuple(int, Entity):
    """ Combat calculation
    Returns
        int: None = missed, >=0 = hit margin
        entity: who is hit"""
    fire_line = shooter.gamemap.get_fire_line(shooter)

    if target:
        base_attack, base_defense, cover = fire_line.get_hit_stat((target.x,target.y),target)

        # TODO : extra modifiers (most are in get_hit_stat)
        attack = base_attack
        defense = base_defense + cover

        # Roll !
        attack_success = roll(attack)
        defense_success = roll(defense)
        
        shooter.gamemap.engine.logger.debug(f"Att:{attack_success} success on {attack}, Def:{defense_success} on {defense}")

        if attack_success:
            hit_margin = attack_success - defense_success
        else:
            hit_margin = -1 # no success is always a miss
    else:
        hit_margin = 0
    
    return hit_margin, target

def stray_fire(fire_line) -> Tuple(int, Entity):
    """ Two situations :
    * target is missed
        1. 50% the shot is lost
        2. 50% the shot hit an opponent in between, chances based on size
    * shooter shoots an empty space
        same proportion but instead of a lost shot, the shot reach the target area
    """
    target = fire_line.target
    hit_margin = 0
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
            fire_line.parent.engine.logger.debug(f"Interception:{target.name}")
        else:
            if target:
                hit_margin = None
                target = None
            else:
                hit_margin = 0

    if target is None and hit_margin is None:
        # stray fire
        # TODO : define the hit in fov or out fov
        pass

    return hit_margin, target


def damage_calculation(weapon: Item, target: Entity, hit_margin) -> Tuple[int,int]:
    """ Calculate damage for a weapon on a target.
    takes into account ths shooter if applicable"""
    try:
        # item < inventory < actor
        shooter: Actor = weapon.parent.parent
    except AttributeError:
        shooter = None

    damage = weapon.equippable.base_damage + hit_margin # TODO : bonus ??
    armor = target.fightable.armor # TODO : bonus ?

    armor_reduction = roll(armor)

    target.gamemap.engine.logger.debug(f"Armor damage reduction:{armor_reduction} success on {armor}")
    if shooter:
        damage += shooter.aim_stack
        shooter.gamemap.engine.logger.debug(f"Damage aim bonus:{shooter.aim_stack}")

    return damage,armor_reduction

