from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING

import numpy as np
import line_types
import tcod

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


def circle_coords(center: Tuple[int,int], radius:int) -> List[Tuple[int,int]]:
    """Returns the list of coordinates of the circle around center using Chebyshev distance"""
    result: List = []
    x0 = center[0]
    y0 = center[1]
    if radius < 0:
        raise ValueError("Radius must be greater than zero")
    if radius == 0:
        return center
    for i in range(x0-radius, x0+radius+1):
        result.append([i,y0+radius])
        result.append([i,y0-radius])
    for j in range(y0-radius+1, y0+radius):
        result.append([x0-radius,j])
        result.append([x0+radius,j])
    return result

def disk_coords(center: Tuple[int,int], radius:int) -> List[Tuple[int,int]]:
    """Returns the list of coordinates of the disk around center using Chebyshev distance"""
    result: List = []
    x0 = center[0]
    y0 = center[1]
    if radius < 0:
        raise ValueError("Radius must be greater than zero")
    for i in range(x0-radius, x0+radius+1):
        for j in range(y0-radius, y0+radius+1):
            result.append([i,j])
    return result

def move_path(map_fov: np.ndarray, shooter_xy: Tuple[int,int], target_xy: Tuple[int,int] ) -> np.ndarray:
    """ Computes the path between shooter and target
    Returns a np array with the list of cells to cross and their obstacle"""

    cost = np.array(map_fov["walkable"], dtype=np.int8)
    graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
    pathfinder = tcod.path.Pathfinder(graph)

    pathfinder.add_root(shooter_xy)
    path = pathfinder.path_to(target_xy)

    path_line = np.full((len(path),1), fill_value=line_types.default, order="F")
    path_line["path"][:,0,:] = path  # same as fire_line["path"].squeeze(axis=(1,)) ; also check expand_dims

    return path_line

def get_sector(x: int, y: int) -> int:
    """ Define the sector of the target relative to 0
        >>> 0->x
        |    
        v     * 8 * 1 *
        y      *  *  *
             7  * * *   2
                 ***
             *****O******
                 ***
             6  * * *   3
               *  *  *
              * 5 * 4 *
    """
    target_sector = 0
    if x > 0:
        if y < 0:
            if y < -x:
                target_sector = 1 # check N and NE
            else:
                target_sector = 2 # check E and NE
        else:
            if y < x:
                target_sector = 3 # check E and SE
            else:
                target_sector = 4 # check S ans SE
    else:
        if y > 0:
            if y > -x:
                target_sector = 5 # check S and SW
            else:
                target_sector = 6 # check W and SW
        else:
            if y > x:
                target_sector = 7 # check W and NW
            else:
                target_sector = 8 # check N and NW
    return target_sector

def fire_line(map_fov: np.ndarray, shooter_xy: Tuple[int,int], target_xy: Tuple[int,int]) -> List:  #np.ndarray:
    """Computes the line of fire with cover.
    By default, a bresenham line, but also when hunkering, or with a wall in between, a slight bend to avoid the wall. Once only
    
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

    # Base case : shooter and target free of walls
    fire_line: List = tcod.los.bresenham(shooter_xy, target_xy).tolist()
    line_cover_tmp = 0
 
    for idx,[i, j] in enumerate(reversed(fire_line[1:-1])):
        # check if any wall is in between, starting from the end. Only one wall near target is OK. 
        if not map_fov["walkable"][i,j]:
            if idx == 0:
                line_cover_tmp += 1
            else:
                line_cover_tmp = 15
                break

    if line_cover_tmp == 0 or shooter_xy[0] == target_xy[0] or shooter_xy[1] == target_xy[1]:  #TODO : check if diag must also be tested
        print(f"bend {is_bend} - linecover {line_cover_tmp}")
        return fire_line[1:]

    if line_cover_tmp == 1:
        result = fire_line[1:]
        line_cover = line_cover_tmp


    # define target sector (player is 0,0, target is x,y). No need to check equality
    x = target_xy[0] - shooter_xy[0]
    y = target_xy[1] - shooter_xy[1]

    target_sector = 0
    check = [] # check will always start with diagonal bending
    if x > 0:
        if y < 0:
            if y < -x:
                target_sector = 1 # check N and NE
                check=["K_u","K_k"]
            else:
                target_sector = 2 # check E and NE
                check=["K_u","K_l"]
        else:
            if y < x:
                target_sector = 3 # check E and SE
                check=["K_n","K_l"]
            else:
                target_sector = 4 # check S ans SE
                check=["K_n","K_j"]
    else:
        if y > 0:
            if y > -x:
                target_sector = 5 # check S and SW
                check=["K_b","K_j"]
            else:
                target_sector = 6 # check W and SW
                check=["K_b","K_h"]
        else:
            if y > x:
                target_sector = 7 # check W and NW
                check=["K_y","K_h"]
            else:
                target_sector = 8 # check N and NW
                check=["K_y","K_k"]
    
    # If shooter bends himself, we must not take away first element
    for key in check:   # starts with diagonal
        dx, dy = MOVE_KEYS[key]
        bend_x = shooter_xy[0] + dx
        bend_y = shooter_xy[1] + dy
        
        # cannot bend into a wall
        if not map_fov["walkable"][bend_x,bend_y]:
            print(f"bend in a wall impossible {key}")
            continue

        fire_line: List = tcod.los.bresenham((bend_x,bend_y), target_xy).tolist()
        line_cover_tmp = 0
    
        for [i, j] in reversed(fire_line[1:-1]): 
            # check if any wall is in between
            # if ok, return the fire line
            if not map_fov["walkable"][i,j]:
                line_cover_tmp += 1

        if line_cover_tmp == 0:
            line_cover = 0
            is_bend = True
            print(f"bend {key} - linecover {line_cover}")
            result = fire_line
            return result
        elif line_cover_tmp < line_cover:
            is_bend = True
            print(f"bend {key} - linecover {line_cover}")
            line_cover = line_cover_tmp
            result = fire_line
    
    print(f"bend {is_bend} - linecover {line_cover}")
    return result
