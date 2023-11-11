from __future__ import annotations

from typing import Tuple,TYPE_CHECKING

import numpy as np

from camera import Camera

if TYPE_CHECKING:
    from tcod.console import Console
    from tcod.context import Context
    from engine import Engine

class Renderer:
    """ Renderer class, can be called through the engine.
    It is initialized at the beginning of the main loop and added to the game engine.
    Before the save, engine is purged
    
    Bad practise : a class is not to be used only to provide access to information."""
    def __init__(self, context: Context, console: Console):
        self.context = context
        self.console = console
        self.view_width = 39    # = initial width 79 -30
        self.view_height = 23   # = initial height 24 -1
        self.camera = Camera(0,0)

    def shift(self,x,y) -> (int,int):
        return (x-self.camera.x+self.view_width//2,y-self.camera.y+self.view_height//2)

