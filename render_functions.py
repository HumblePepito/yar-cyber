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
        empty_char: str,
        x: int,
        y: int,
        current_value: int,
        maximum_value: int,
        total_width: int=24
    ) -> None:
    
    bar_width = int(float(current_value) / maximum_value * total_width)

    ascii_bar = f"{fill_char*bar_width}{empty_char*(total_width-bar_width)}"
    console.print(x,y,ascii_bar)



