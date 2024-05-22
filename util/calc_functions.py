from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING

import numpy as np
import math
import line_types
import tcod
import color

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

def progress_color(current_value: int, value:int) -> Tuple[int,int,int]:
    """Returns a color based on evolution if current_value.s
    For HP, for clip, ..."""
    progress: float = current_value / value

    if progress >= 0.7:
        return color.n_green
    elif progress >= 0.4:
        return color.b_orange
    elif progress >= 0.2:
        return color.n_purple
    else:
        return color.n_red

def get_distance(start: Tuple[int,int], end: Tuple[int,int]) -> float:
    return math.sqrt((start[0] - end[0])**2+(start[1] - end[1])**2)

def get_project_point(start: Tuple[int,int], end: Tuple[int,int], dist: int) -> Tuple[int,int]:
    """Returns the coordinates of the point on the (`start,end`) ray at distance `dist` from `start`"""
    x=end[0]-start[0]
    y=end[1]-start[1]
    r=math.sqrt(x*x+y*y)
    alpha=math.acos(x/r)
    if y<0:
        alpha=-alpha

    return (round(start[0]+dist*math.cos(alpha)), round(start[1]+dist*math.sin(alpha)))

def get_cone_points(start: Tuple[int,int], end: Tuple[int,int], cone_radius:int, dist:int =10) -> List[Tuple[int,int]]:
    """Returns all the points in the cone of length `dist` and radius `cone_radius` without `start` point"""
    cone_points=np.array([start],dtype=np.int32)
    result=cone_points
    # extension to 10
    end=get_project_point(start,end,10)
    # a point, on a perpenducular segment
    perp1=( start[1]-end[1]+end[0],
           -start[0]+end[0]+end[1] )

    # # add each rays
    # for i in range(-cone_radius,cone_radius+1):
    #     cone_point=get_project_point(end,perp1,i)
    #     segment=tcod.los.bresenham(start,cone_point)
    #     cone_points=np.vstack((cone_points,segment)) # or concatenate)

    # borders
    cone_point1=get_project_point(end,perp1,-cone_radius)
    cone_point2=get_project_point(end,perp1,cone_radius)
    segment1=tcod.los.bresenham(start,cone_point1)
    segment2=tcod.los.bresenham(start,cone_point2)
    top=tcod.los.bresenham(cone_point1,cone_point2)
    cone_points=np.vstack((segment1,segment2,top)) # or concatenate)

    # fill the area
    xmin=min(start[0],cone_point1[0],cone_point2[0])
    xmax=max(start[0],cone_point1[0],cone_point2[0])

    # https://stackoverflow.com/questions/1962980/selecting-rows-from-a-numpy-ndarray
    for i in range(xmin,xmax+1):
        ymin=np.amin(cone_points[cone_points[:,0]==i][:,1])
        ymax=np.amax(cone_points[cone_points[:,0]==i][:,1])
        result = np.vstack((result,tcod.los.bresenham((i,ymin),(i,ymax))))

    return (x for x in np.unique(result,axis=0).tolist() if x != [*start]) # how to remove start from numpy.array ?

