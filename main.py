#!/usr/bin/env python3
import traceback
import logging
import os

import tcod

import util.var_global
import util.event
from util.charmap import CHARMAP_CP437_pepito

import exceptions
import input_handlers

import color
import setup_game
from engine import Engine
from input_handlers import MainGameEventHandler

from renderer import Renderer

def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
    """If the current event handler has an active Engine then save it."""
    if isinstance(handler, input_handlers.EventHandler):
        handler.engine.save_as(filename)
        print("Game saved.")

def main() -> None:

    FLAGS = tcod.context.SDL_WINDOW_RESIZABLE
    # size of console
    screen_width = 79
    screen_height = 24 #50
#https://python-tcod.readthedocs.io/en/latest/tcod/getting-started.html#dynamically-sized-console

    # log tool
    Log_Format = "%(levelname)s %(asctime)s - %(message)s"
    logging.basicConfig(
        filename="logfile.log", filemode="w", format=Log_Format, level=logging.DEBUG
    )
    logger = logging.getLogger()
    util.var_global.logger = logger

    tileset = tcod.tileset.load_tilesheet(
        # "./png/mono6x12.png", 32,8, tcod.tileset.CHARMAP_TCOD
        # "./png/mono12x24.png", 32,8, tcod.tileset.CHARMAP_TCOD
        # "./png/Cheepicus_16x16.png", 16, 16, CHARMAP_CP437_pepito
        "./png/Bisasam_20x20_ascii.png", 16, 16, CHARMAP_CP437_pepito
    #     "./png/chozo32.png", 40, 27, tcod.tileset.CHARMAP_TCOD
    
    )

    handler: input_handlers.BaseEventHandler = setup_game.MainMenu() # gets back with MainGameEventHandler

    context = tcod.context.new(
        x=0,
        y=0,
        columns=screen_width,
        rows=screen_height,
        width=1580,
        height=480,
        tileset=tileset,
        title="Sci-fi Roguelike Tutorial",
        vsync=True,
        sdl_window_flags=FLAGS
    )
    # Use of renderer instead of console in order to add both Console & Context to the engine and use it in auto-Handlers
    renderer = Renderer(context=context, console=context.new_console(min_columns=screen_width, min_rows=screen_height, order="F"))

    # Boucle principale !!
    go_draw = True
    engine_ok = False
    try:
        while True:
            size = renderer.context.recommended_console_size()
            renderer.view_width=size[0]-40
            renderer.view_height=size[1]-1
            if size[0] <screen_width or size[1] < screen_height:
                print("Min size of console is 79x24.")
                raise SystemExit

            if not engine_ok:
                try:
                    # Some initialization
                    engine_ok = True
                    engine: Engine = handler.engine
                    renderer.camera.x = engine.player.x
                    renderer.camera.y = engine.player.y
                    engine.logger = logger
                    logger.info("Engine initialized")
                except AttributeError:
                    engine_ok = False

            if go_draw:
                renderer.console.clear()
                handler.on_render(renderer=renderer)
                renderer.context.present(renderer.console, keep_aspect= True, integer_scaling=True)

            try:
                # menus before game start
                if not engine_ok:   # menus before game start
                        for event in util.event.wait():
                            #context.convert_event(event) # for mouse
                            handler = handler.handle_events(event)
                # normal mode
                elif engine_ok and not engine.player.ai.is_auto:
                        go_draw = False
                        for event in util.event.wait():
                            if isinstance(event, tcod.event.KeyDown):
                                go_draw = True
                            handler = handler.handle_events(event)
                # auto mode
                else:
                    if engine.player.ai.is_auto:
                        for event in util.event.get():
                            # Stop auto if a key is pressed
                            if isinstance(event, tcod.event.KeyDown):
                                engine.player.ai.is_auto = False
                                engine.logger.info(f"Auto-mode {engine.player.ai.is_auto}")
                                handler = MainGameEventHandler(engine)

                        ##### Events that stops the auto loop #####
                        # Check FOV
                        if engine.player.see_actor:
                            engine.player.ai.is_auto = False
                            engine.logger.info(f"Auto-mode {engine.player.ai.is_auto}")
                            handler = MainGameEventHandler(engine)
                        # Check if player is still alive (needless but just in case)
                        # if not engine.player.is_alive:
                        #     handler = GameOverEventHandler(engine)
                        
                        handler.handle_action(engine.player.ai)

            except Exception:  # Handle exceptions in game.
                logger.critical(traceback.format_exc())
                handler.engine.message_log.add_message("Exception raised at Main level. Check logfile.", color.error) # nuance avec isinstance    
    except exceptions.QuitWithoutSaving:
        raise
    except SystemExit:  # Save and quit.
        save_game(handler, "savegame.sav")
        raise
    except BaseException:  # Save on any other unexpected exception.
        save_game(handler, "savegame.sav")
        raise

if __name__ == "__main__":
    main()