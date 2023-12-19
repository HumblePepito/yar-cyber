from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tcod import Console
    from engine import Engine
    from game_map import GameMap

def get_names_at_location(x: int, y: int, game_map: GameMap) -> str:
   if not game_map.in_bounds(x, y) or not game_map.visible[x, y]:
       return ""

   names = ", ".join(
       entity.name for entity in game_map.entities if entity.x == x and entity.y == y
   )

   return names.capitalize()

def render_ascii_bar(
        console: Console,
        fill_char: str,
        fill_color: (int,int,int),
        empty_char: str,
        empty_color: (int,int,int),
        x: int,
        y: int,
        current_value: int,
        maximum_value: int,
        total_width: int=25
    ) -> None:
    
    bar_width = int(float(current_value) / maximum_value * total_width)

    console.print(x,y,f"{fill_char*bar_width}",fill_color)
    console.print(x+bar_width,y,f"{empty_char*(total_width-bar_width)}",empty_color)

def render_ascii_slider(
        console: Console,
        bar_char: str,
        bar_color: (int,int,int),
        cursor: str,
        cursor_color: (int,int,int),
        x: int,
        y: int,
        current_value: int,
        min_value: int,
        min_string: str,
        max_value: int,
        max_string: str,
        total_width: int=25
    ) -> None:
    
    console.print(x,y,bar_char*total_width,bar_color)
    console.print(x+total_width//2,y,f"{cursor}",bar_color)
    
    cursor_pos = int(float(total_width/(max_value-min_value)*current_value))
    console.print(x+cursor_pos,y,f"{cursor}",cursor_color)
    