from __future__ import annotations

from typing import Dict, List, Tuple, TYPE_CHECKING

import numpy as np
import util.calc_functions as cf
import line_types
import tcod
from entity import Actor, Entity
from various_enum import ItemType, SizeClass

if TYPE_CHECKING:
    from game_map import GameMap
    from engine import Engine
    

MOVE_KEYS = {
    # Vi keys.
    "K_h": (-1, 0),
    "K_j": (0, 1),
    "K_k": (0, -1),
    "K_l": (1, 0),
    "K_y": (-1, -1),
    "K_u": (1, -1),
    "K_b": (-1, 1),
    "K_n": (1, 1),
}

class FireLine:
    parent: Engine

    def __init__(self,engine: Engine):
        # TODO : try no engine parameters and initialize parent after creation (in calling place) ??
        self.parent = engine
        self.shooter:Actor = None
        self.shooter_xy: Tuple[int, int] = None
        self.target: Entity = None
        self.target_xy: Tuple[int, int] = None

        self.path: List[Tuple[int, int]]
        self.entities: List[Entity] = []
        self.combat_stat: Dict = {}# TODO change to numpy to extend cache
        # self.is_under_cover = []

    def compute(self, shooter: Entity, target_xy: Tuple[int, int]) -> None:
        """ There are only two fire line objects. One for the player, the other for hostile. Maybe new fire lines will be added for allies.
        Compute updates all stats of the fire line based on `shooter` and `target _xy`
           * `path`: as a (x,y) list, without the shooter, with the target
           * `target` if exists (either Actor or Feature)
           * `entities`: list of entities between shooter and target
           * `is_under_cover` : list of protected sector"""
        self.shooter = shooter
        self.shooter_xy = (shooter.x, shooter.y)
        self.target_xy = target_xy
        
        self.path = self.get_path()
        self.target = self.parent.game_map.get_target_at_location(*self.target_xy)
        self.entities = self.get_entities()

        return

    def get_path(self) -> List[Tuple[int, int]]:  #np.ndarray:
        """Computes the path of the line of fire.
        Does not include the shooter
        By default, a bresenham line, but includes a slight bend to avoid the wall (destroys cover)
        
        >>>    S***....  and  S..#....  and S#.....   
        >>>    ....***T       .******T      .***..
        >>>    ........       ........      .#..**T

        To define how to bend, divide the screen into 8 parts (move direction) and et the target sector (1 to 8 clockwise)
        >>> 0->x
            |    
            v    * 8 * 1 *
            y     *  *  *
                7  * * *   2
                    ***
                *****S******
                    ***
                6  * * *   3
                  *  *  *
                 * 5 * 4 *

        This will define the two bending position if direct line of fire is not available
        """
        
        wall_cover = 10
        result = []
        is_bend = False
        bend = ""

        # Base case : shooter and target free of walls
        fire_line = tcod.los.bresenham(self.shooter_xy, self.target_xy).tolist()
        wall_cover_tmp = 0
    
        for [i, j] in reversed(fire_line[1:-1]):
            # check walls. 
            if not self.parent.game_map.tiles["walkable"][i,j]:
                wall_cover_tmp += 1

        # if clear line of fire, we won't get better.
        # And no need to bend if shooter and target are aligned : we won't get better either
        if wall_cover_tmp == 0 or self.shooter.x == self.target_xy[0] or self.shooter.y == self.target_xy[1]:  #TODO : check if diag must also be tested
            # Direct shot! 
            self.shooter.bend = bend
            return fire_line[1:]

        # we keep current results and try to bend afterwards
        result = fire_line[1:]
        self.shooter.bend = bend
        wall_cover = wall_cover_tmp

        # define target sector (player is 0,0, target is x,y). No need to check equality
        x = self.target_xy[0] - self.shooter.x
        y = self.target_xy[1] - self.shooter.y

        target_sector = cf.get_sector(x,y)
        check = [] # check will always start with diagonal bending
        if target_sector == 1:
            check=["K_u","K_k"]
        elif target_sector == 2:
            check=["K_u","K_l"]
        elif target_sector == 3:
            check=["K_n","K_l"]
        elif target_sector == 4:
            check=["K_n","K_j"]
        elif target_sector == 5:
            check=["K_b","K_j"]
        elif target_sector == 6:
            check=["K_b","K_h"]
        elif target_sector == 7:
            check=["K_y","K_h"]
        elif target_sector == 8:
            check=["K_y","K_k"]
        
        # If shooter bends himself, we must not take away first element
        for key in check:   # starts with diagonal
            dx, dy = MOVE_KEYS[key]
            bend_x = self.shooter.x + dx
            bend_y = self.shooter.y + dy
            
            # cannot bend into a wall
            if not self.parent.game_map.tiles["walkable"][bend_x,bend_y]:
                continue

            fire_line = tcod.los.bresenham((bend_x,bend_y), self.target_xy).tolist()
            
            wall_cover_tmp = 0
            for [i, j] in reversed(fire_line[1:-1]): 
                # check if any wall is in between
                if not self.parent.game_map.tiles["walkable"][i,j]:
                    wall_cover_tmp += 1

            if wall_cover_tmp < wall_cover:
                # means that still position led to 15 and we are now at 1
                is_bend = True
                self.shooter.bend = key
                wall_cover = wall_cover_tmp
                result = fire_line      

        return result
    
    def get_entities(self) -> List[Entity]:
        """Gets the entities along the line of fire, only features, actor and walls.
        Does not include the target, nor the shooter."""
        result = []
        skip_walls = True
        for [i, j] in self.path[:-1]:
            if skip_walls and self.parent.game_map.tiles["walkable"][i,j]:
                skip_walls = False

            entity = self.parent.game_map.get_target_at_location(i,j)
            if entity:
                result.append(entity)
            if not self.parent.game_map.tiles["walkable"][i,j]:
                if not skip_walls:
                    entity = self.parent.game_map.wall
                    result.append(entity)

        # for [i, j] in self.path[:-1]:
        #     entity = self.parent.game_map.get_target_at_location(i,j)
        #     if entity:
        #         result.append(entity)
        #     if not self.parent.game_map.tiles["walkable"][i,j]:
        #         entity = self.parent.game_map.wall
        #         result.append(entity)

        return result
    
    def get_hit_stat(self, target_xy:Tuple[int,int], target: Entity = None) -> Tuple[int, int, int]:
        """ Provide ATT, DEF and COVER for the designated target
        and save them in this fire_line"""

        if (self.shooter_xy+target_xy) in list(self.combat_stat):
            # self.parent.logger.debug(f"Fire line combat_stat cache : {(self.shooter_xy+target_xy)}:{self.combat_stat[(self.shooter_xy+target_xy)]}")
            return self.combat_stat[(self.shooter_xy+target_xy)]

        cache = False
        if self.shooter.equipment.weapon is None:
            if self.shooter.distance(*self.target_xy) <= 1:
                cover = 0
                base_attack = self.shooter.fightable.attack
                base_defense = target.fightable.defense
                cache = True
            else:
                cover,base_attack,base_defense = 0,0,0
        elif self.shooter.equipment.weapon.item_type == ItemType.RANGED_WEAPON:
            cover = 0
            if target is None:
                # shoot behind the target (wall or nothing)
                target_size = SizeClass.HUGE.value
                for entity in self.entities:
                    cover += max(0, entity.size.value + 1 - target_size)

                base_attack = self.shooter.fightable.attack
                base_defense = 0
            else:
                target_size = target.size.value
                for entity in self.entities:
                    cover += max(0, entity.size.value + 1 - target_size)
                if target.is_actor and target.hunker_stack and len(self.path) > 1:
                    i,j = self.path[-2]
                    entity = self.parent.game_map.get_target_at_location(i,j)
                    if not entity and not self.parent.game_map.tiles["walkable"][i,j]:
                        entity = self.parent.game_map.wall
                    if entity: 
                        cover+= target.hunker_stack*(entity.size.value + 1 - target_size)

                # TODO : aiming ? range ? or consecutive shots ? and of course : wounds
                base_attack = self.shooter.fightable.attack
                weapon = self.shooter.equipment.weapon
                if weapon and weapon.item_type == ItemType.RANGED_WEAPON:
                    base_attack -=  2*max(0,len(self.path) - weapon.equippable.base_range)
                    base_attack = max(0, base_attack)
                    if self.shooter.aim_stack:
                        base_attack += 3*self.shooter.aim_stack
                        self.parent.logger.debug(f"Aim bonus: lvl{self.shooter.aim_stack}:{3*self.shooter.aim_stack}")

                base_defense = target.fightable.defense
            cache = True
        elif self.shooter.equipment.weapon.item_type == ItemType.MELEE_WEAPON and self.shooter.distance(*self.target_xy) <= 1:
            cover = 0
            base_attack = self.shooter.fightable.attack
            base_defense = target.fightable.defense
            cache = True
        else:
            cover,base_attack,base_defense = 0,0,0

            
        if not (self.shooter is self.parent.player and target is self.parent.player) and cache:
            self.combat_stat[self.shooter_xy+target_xy] = (base_attack, base_defense, cover)
            self.parent.logger.debug(f"Combat_stat add cache : {(self.shooter_xy+target_xy)}:{self.combat_stat[(self.shooter_xy+target_xy)]}")

        return (base_attack, base_defense, cover)

            
        

