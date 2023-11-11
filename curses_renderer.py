from __future__ import annotations

from typing import Tuple,TYPE_CHECKING

import numpy as np
import curses

import color
from camera import Camera


if TYPE_CHECKING:
    from tcod.console import Console
    from engine import Engine

class Renderer:
    """ Renderer class, can be called through the engine.
    It is initialized at the beginning of the main loop and added to the game engine.
    Before the save, engine is purged
    
    Bad practise : a class is not to be used only to provide access to information."""

    def __init__(self, stdscr: curses._CursesWindow, console: Console):
        self.stdscr = stdscr
        self.console = console
        self.view_width = 39    # = initial width 79 -30
        self.view_height = 23   # = initial height 24 -1
        self.camera = Camera(0,0)

        self.context = Context(stdscr)


    def shift(self,x,y) -> (int,int):
        return (x-self.camera.x+self.view_width//2,y-self.camera.y+self.view_height//2)

class Context:
    stdscr: curses._CursesWindow

    def __init__(self, stdscr) -> None:
        self.stdscr = stdscr

    def present(self, console: Console):
        width = console.width
        height = console.height

        # for i in range(0,width):
        #     for j in range(0,height):
        #         fg: np.ndarray = console.fg[i,j]
        #         bg: np.ndarray = console.bg[i,j]
        #         try:
        #             pair_fg = color.COLOR_CODE[tuple(fg)]
        #             pair_bg = color.COLOR_CODE[tuple(bg)]
        #             self.stdscr.attroff(curses.A_BOLD)
        #         except KeyError:
        #             pair_fg = 0
        #             self.stdscr.attroff(curses.A_REVERSE)
                
        #         if pair_fg >= 9:
        #             pair_fg -= 8
        #             self.stdscr.attron(curses.A_BOLD)
        #             # self.stdscr.attron(curses.A_DIM)
                  
        #         self.stdscr.addch(j,i,chr(console.ch[i,j]), curses.color_pair(pair_fg))

        # for i in range(0,width):
            # for j in range(0,height):
            #     fg: np.ndarray = console.fg[i,j]
            #     bg: np.ndarray = console.bg[i,j]
            #     try:
            #         pair_fg = color.COLOR_CODE[tuple(fg)]
            #         pair_bg = color.COLOR_CODE[tuple(bg)]
            #     except KeyError:
            #         pair_fg = 0
            #         self.stdscr.attroff(curses.A_REVERSE)
                
            #         # self.stdscr.attron(curses.A_DIM)
            #     if pair_bg == 1:
            #         self.stdscr.attroff(curses.A_REVERSE)
            #     else:
            #         self.stdscr.attron(curses.A_REVERSE)
                
            #     self.stdscr.addch(j,i,chr(console.ch[i,j]), curses.color_pair(pair_fg))
    
        # self.stdscr.refresh()

        for i in range(0,width):
            for j in range(0,height):
                fg: np.ndarray = console.fg[i,j]
                bg: np.ndarray = console.bg[i,j]
                try:
                    # pair_fg = color.COLOR_CODE[tuple(fg)]
                    # pair_bg = color.COLOR_CODE[tuple(bg)]
                    # print(tuple(fg)+tuple(bg))
                    # print(color.COLOR_PAIR)
                    color_pair = color.COLOR_PAIR[tuple(fg)+tuple(bg)]
                except KeyError:
                    color_pair = 5
                
                    # self.stdscr.attron(curses.A_DIM)
                # if pair_bg == 1:
                #     self.stdscr.attroff(curses.A_REVERSE)
                # else:
                #     self.stdscr.attron(curses.A_REVERSE)
                
                self.stdscr.addch(j,i,chr(console.ch[i,j]), curses.color_pair(color_pair))
    
        self.stdscr.refresh()