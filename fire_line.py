from __future__ import annotations

from typing import Dict, List, Tuple, TYPE_CHECKING

import numpy as np
import util.calc_functions as cf
import line_types
import tcod
from entity import Actor, Entity
from various_enum import SizeClass

if TYPE_CHECKING:
    from game_map import GameMap
    

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

    def __init__(self,game_map: GameMap):
        self.game_map = game_map
        self.shooter:Actor = None
        self.shooter_xy: Tuple[int, int] = None
        self.target: Entity = None
        self.target_xy: Tuple[int, int] = None

        self.path: List[Tuple[int, int]]
        self.end: int
        self.entities: List[Entity] = []
        self.combat_stat: Dict # TODO : populate each time a new entity is aimed at



    def compute(self, shooter: Entity, target_xy: Tuple[int, int]) -> FireLine:
        self.shooter = shooter
        self.shooter_xy = (shooter.x, shooter.y)
        self.target_xy = target_xy

        self.target = self.game_map.get_target_at_location(*target_xy) 
        
        self.path = self.get_path()
        self.end = self.get_end()
        self.path = self.path[0:self.end+1]
        self.entities = self.get_entities()

        
        return self

    def get_path(self) -> List[Tuple[int, int]]:  #np.ndarray:
        """Computes the line of fire with cover.
        Does not include the shooter
        By default, a bresenham line, but also when hunkering, or with a wall in between, a slight bend to avoid the wall.
        
        >>>    S***....  and  S..#....  and S#.....   
        >>>    ....***T       .******T      .***..
        >>>    ........       ........      .#..**T

        To define how to bend, divide the screen into 8 parts (move direction) and et the target sector (1 to 8 clockwise)
        >>> 0->x
            |    
            v     * 8 * 1 *
            y      *  *  *
                7  * * *   2
                    ***
                *****S******
                    ***
                6  * * *   3
                  *  *  *
                 * 5 * 4 *

        This will define the two bending position if direct line of fire is not available
        """
        
        line_cover = 15
        result = []
        is_bend = False
        bend = ""

        # Base case : shooter and target free of walls
        fire_line = tcod.los.bresenham(self.shooter_xy, self.target_xy).tolist()
        line_cover_tmp = 0
    
        for idx,[i, j] in enumerate(reversed(fire_line[1:-1])):
            # check if any wall is in between, starting from the end. Only one wall near target is OK (distance 1 or 2). 
            if not self.game_map.tiles["walkable"][i,j]:
                if idx == 0:
                    line_cover_tmp = 1
                elif idx == 1 and line_cover_tmp == 0:
                    line_cover_tmp = 1
                else:
                    line_cover_tmp = 15
                    break

        # if clear line of fire, we won't get better.
        # And no need to bend if shooter and target are aligned : we won't get better either
        if line_cover_tmp == 0 or self.shooter.x == self.target_xy[0] or self.shooter.y == self.target_xy[1]:  #TODO : check if diag must also be tested
            # print(f"bend {is_bend} - linecover {line_cover_tmp}")
            self.shooter.bend = bend
            return fire_line[1:]

        if line_cover_tmp == 1:
            result = fire_line[1:]
            line_cover = line_cover_tmp


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
            if not self.game_map.tiles["walkable"][bend_x,bend_y]:
                # print(f"bend in a wall impossible {key}")
                continue

            fire_line = tcod.los.bresenham((bend_x,bend_y), self.target_xy).tolist()
            line_cover_tmp = 0
        
            for [i, j] in reversed(fire_line[1:-1]): 
                # check if any wall is in between
                # if ok, return the fire line
                if not self.game_map.tiles["walkable"][i,j]:
                    line_cover_tmp += 1

            if line_cover_tmp == 0:
                line_cover = 0
                is_bend = True
                self.shooter.bend = key
                # print(f"bend {key} - linecover {line_cover}")
                result = fire_line
                return result
            elif line_cover_tmp < line_cover:
                is_bend = True
                self.shooter.bend = key
                # print(f"bend {key} - linecover {line_cover}")
                line_cover = line_cover_tmp
                result = fire_line
        
        # print(f"bend {is_bend} - linecover {line_cover}")
        if is_bend:
            self.shooter.bend = key
        return result

    def get_end(self) -> int:
        """Get the last index of the line of fire"""
        is_blocked = False
        idx = 1
        for [i, j] in self.path[1:]:
            if not self.game_map.tiles["walkable"][i,j]:
                if is_blocked == False:
                    is_blocked = True
                else:
                    return idx-1

            idx += 1
        
        return idx-1
    
    def get_entities(self) -> List[Entity]:
        """Gets the entities along the line of fire, only features, actor and walls.
        Does not include the target"""
        result = []
        for [i, j] in self.path[:-1]:
            entity = self.game_map.get_actor_at_location(i,j)
            if entity:
                result.append(entity)
            entity = self.game_map.get_feature_at_location(i,j)
            if entity:
                result.append(entity)
            if not self.game_map.tiles["walkable"][i,j]:
                entity = self.game_map.wall
                result.append(entity)

        return result
    
    def get_cover(self) -> int:
        """ Cover is a percentage from 0 (clear) to 99 (fully covered).
        There is always a 1% chance to hit.
        Each entity present on the path of fire provide a cover based on its size attribute"""
        pass
        # add cover_bonus to entities and use it
    
    def get_hit_stat(self, target: Entity) -> Tuple[int, int, int]:
        """ Provide ATT, DEF and COVER for the designated target
        and save them in this fire_line"""

        if target in list(self.combat_stat):
            return self.combat_stat[target]
        else:
            cover = 0
            if target:
                target_size = target.size.value
            else:
                target_size = SizeClass.HUGE.value
                # target_size = SizeClass.SMALL.value # TODO : remove after test

            for entity in self.entities:
                cover += max(0, entity.size.value +1 - target_size)

            base_attack = self.shooter.fightable.attack
            base_defense = target.fightable.defense
            
            self.combat_stat[target] = (base_attack, base_defense, cover)
            return (base_attack, base_defense, cover)

            
        

