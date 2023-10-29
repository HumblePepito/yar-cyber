from __future__ import annotations

from typing import Tuple
import numpy as np



class Camera:
    """An object for tracking the camera position and for screen/world conversions.

    `x` and `y` are the camera center position.
    """

    def __init__(self,x: int,y: int):
        self.x = x
        self.y = y

    def get_view_slice(self, world_shape: Tuple[int, int], view_shape: Tuple[int, int]) -> Tuple[Tuple[slice, slice], Tuple[slice, slice]]:
        """Return viewslice as 2D slices for use with NumPy.

        These views are used to slice their respective arrays.
        """
        # start : world_left,world_top
        world_left = max(0,self.x-view_shape[0]//2)
        world_top = max(0,self.y-view_shape[1]//2)
        # end : world_right,world_bottom
        world_right = min(world_shape[0],self.x+view_shape[0]//2+1)
        world_bottom = min(world_shape[1],self.y+view_shape[1]//2+1)

        world_slice = np.s_[world_left:world_right, world_top:world_bottom]

        # start view x
        if self.x+view_shape[0]//2 > world_shape[0]-1:
            view_right = world_shape[0]-self.x+view_shape[0]//2
            view_left = 0
        elif self.x-view_shape[0]//2 < 0:
            view_right = view_shape[0]
            view_left = view_shape[0]//2 - self.x
        else:
            view_right = view_shape[0]
            view_left = 0
        # start view y
        if self.y+view_shape[1]//2 > world_shape[1]-1:
            view_top = 0
            view_bottom = world_shape[1]-self.y+view_shape[1]//2
        elif self.y-view_shape[1]//2 < 0:
            view_top = view_shape[1]//2 - self.y
            view_bottom = view_shape[1]
        else:
            view_top = 0
            view_bottom = view_shape[1]

        view_slice = np.s_[view_left:view_right, view_top:view_bottom]
        
        return world_slice, view_slice

    def move(self, dx: int, dy: int) -> None:
        # Move the entity by a given amount
        self.x += dx
        self.y += dy
