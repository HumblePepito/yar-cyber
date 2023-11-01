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

