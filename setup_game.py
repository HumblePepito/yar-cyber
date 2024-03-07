"""Handle the loading and initialization of game sessions."""
from __future__ import annotations

import copy
from typing import Optional

import tcod
from tcod import libtcodpy

import lzma
import pickle
import traceback

import color
import util.var_global as uv

from engine import Engine
import entity_factories
import input_handlers
from game_map import GameWorld
from renderer import Renderer
from various_enum import ItemType

# Load the background image and remove the alpha channel.
background_image = tcod.image.load("./png/menu_background.png")[:, :, :3]


def new_game() -> Engine:
    """Return a brand new game session as an Engine instance."""
    map_width = 80
    map_height = 60

    room_max_size = 12
    room_min_size = 4
    max_rooms = 30

    player = copy.deepcopy(entity_factories.player)

    # TODO 
    # One last thing we can do is give the player a bit of equipment to start. We’ll spawn a dagger and leather armor, and immediately add them to the player’s inventory.
    # https://rogueliketutorials.com/tutorials/tcod/v2/part-13/

    engine = Engine(player=player)

    # Player initialization
    # Equip first weapon
    player.equipment.toggle_equip(player.inventory.get_first_weapon(), add_message=False)
    # auto_pickup lit
    player.auto_pickup_list = [ItemType.POTION.value, ItemType.DRUG.value, ItemType.SCROLL.value, ItemType.GRENADE.value,]
    # place in turn queue
    engine.turnqueue.schedule(0, player)

    engine.game_world = GameWorld(
        engine = engine,
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        map_width=map_width,
        map_height=map_height,
        seed_init=uv.seed_init,
    )

    engine.game_world.set_floor(depth=1)
    # engine.player_lof.parent = engine.game_map
    # engine.hostile_lof.parent = engine.game_map
    engine.update_fov()

    engine.message_log.add_message(
        "Welcome to another sci-fi Roguelike, prepared with love, patience and python", color.welcome_text
    )

    return engine

def load_game(filename: str) -> Engine:
    """Load an Engine instance from a file."""
    with open(filename, "rb") as f:
        engine = pickle.loads(lzma.decompress(f.read()))
    assert isinstance(engine, Engine)
    return engine

class MainMenu(input_handlers.BaseEventHandler):
    """Handle the main menu rendering and input."""

    def on_render(self, renderer: Renderer) -> None:
        """Render the main menu on a background image."""
        console = renderer.console
        console.draw_semigraphics(background_image, 0, 0)

        console.print(
            console.width // 2,
            console.height // 2 - 4,
            "Running in the Shadows",
            fg=color.menu_title,
            alignment=libtcodpy.CENTER,
        )
        console.print(
            console.width // 2,
            console.height - 2,
            "By Pepito",
            fg=color.menu_title,
            alignment=libtcodpy.CENTER,
        )

        menu_width = 24
        for i, text in enumerate(
            ["[N] Play a new game", "[C] Continue last game", "[Q] Quit"]
        ):
            console.print(
                console.width // 2,
                console.height // 2 - 2 + i,
                text.ljust(menu_width),
                fg=color.menu_text,
                bg=color.black,
                alignment=libtcodpy.CENTER,
                bg_blend=libtcodpy.BKGND_ALPHA(64),
            )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[input_handlers.BaseEventHandler]:
        if event.sym in (tcod.event.KeySym.q, tcod.event.KeySym.ESCAPE):
            raise SystemExit()
        elif event.sym == tcod.event.KeySym.c:
            try:
                return input_handlers.MainGameEventHandler(load_game("savegame.sav"))
            except FileNotFoundError:
                return input_handlers.PopupMessage(self, "No saved game to load.")
            except Exception as exc:
                traceback.print_exc()  # Print to stderr.
                return input_handlers.PopupMessage(self, f"Failed to load save:\n{exc}")
        elif event.sym == tcod.event.KeySym.n:
            return input_handlers.MainGameEventHandler(new_game())

        return None