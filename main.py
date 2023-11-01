#!/usr/bin/env python3
import traceback
import logging
import os

import tcod

import util.var_global
import util.event

import exceptions
import input_handlers

import color
import setup_game
from engine import Engine
from input_handlers import MainGameEventHandler, GameOverEventHandler

from renderer import Renderer

def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
    """If the current event handler has an active Engine then save it."""
    if isinstance(handler, input_handlers.EventHandler):
        handler.engine.save_as(filename)
        print("Game saved.")

def main() -> None:

    # size of console
    screen_width = 79
    screen_height = 24 #50

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
        # "./png/Cheepicus_16x16.png", 16, 16, tcod.tileset.CHARMAP_CP437
        "./png/Bisasam_20x20_ascii.png", 16, 16, tcod.tileset.CHARMAP_CP437
    #     "./png/chozo32.png", 40, 27, tcod.tileset.CHARMAP_TCOD
    
    )

    handler: input_handlers.BaseEventHandler = setup_game.MainMenu() # gets back with MainGameEventHandler

    context = tcod.context.new(
        x=0,
        y=0,
        columns=screen_width,
        rows=screen_height,
        tileset=tileset,
        title="Sci-fi Roguelike Tutorial",
        vsync=True,
    )
    # Use of renderer instead of console in order to add both Console & Context to the engine and use it in auto-Handlers
    renderer = Renderer(context=context, console=tcod.console.Console(screen_width, screen_height, order="F"))

    # Boucle principale !!
    """
    try:
        while True:
            # version intiale (v6) : engine.render(console=root_console, context=context)
            #   le clear et le present dans engine ; pas de on_render ni de convert (pour la souris)
            # version 13
            # root_console.clear()
            # handler.on_render(console=root_console)
            # context.present(root_console)
            renderer.console.clear()
            handler.on_render(renderer=renderer)
            renderer.context.present(renderer.console)

            try:
                for event in tcod.event.wait():
                    #context.convert_event(event) # ca, c'est pour la souris
                    handler = handler.handle_events(event)
            except Exception:  # Handle exceptions in game.
                traceback.print_exc()  # Print error to stderr.
                # Then print the error to the message log.
                handler.engine.message_log.add_message(traceback.format_exc(), color.error) # nuance avec isinstance
    except exceptions.QuitWithoutSaving:
        raise
    except SystemExit:  # Save and quit.
        save_game(handler, "savegame.sav")
        raise
    except BaseException:  # Save on any other unexpected exception.
        save_game(handler, "savegame.sav")
        raise
    """
    go_draw = True
    engine_ok = False
    try:
        while True:
            # version intiale (v6) : engine.render(console=root_console, context=context)
            #   le clear et le present dans engine ; pas de on_render ni de convert (pour la souris)
            # version 13
            # root_console.clear()
            # handler.on_render(console=root_console)
            # context.present(root_console)

            if not engine_ok:
                try:
                    handler.engine.message_log.add_message("Engine initialized",color.debug)
                    engine_ok = True
                    engine: Engine = handler.engine
                    player = engine.player
                    renderer.map_width = engine.game_map.width
                    renderer.map_height = engine.game_map.height
                    renderer.camera.x = player.x
                    renderer.camera.y = player.y
                    engine.logger = logger
                except AttributeError:
                    engine_ok = False

            if go_draw:
                renderer.console.clear()
                handler.on_render(renderer=renderer)
                renderer.context.present(renderer.console)

            try:
                if not engine_ok:   # menus before game start
                        for event in util.event.wait():
                            #context.convert_event(event) # for mouse
                            handler = handler.handle_events(event)
                elif engine_ok and not player.ai.is_auto:   # normal mode
                        go_draw = False
                        for event in util.event.wait():
                            if isinstance(event, tcod.event.KeyDown):
                                go_draw = True
                            handler = handler.handle_events(event)
                else:
                    if engine.player.ai.is_auto:
                        for event in util.event.get():
                            # Stop auto if a key is pressed
                            if isinstance(event, tcod.event.KeyDown):
                                player.ai.is_auto = False
                                engine.message_log.add_message(f"Auto-mode {player.ai.is_auto}",color.debug)
                                handler = MainGameEventHandler(engine)

                        ##### Events that stops the auto loop #####
                        # Check FOV
                        if player.see_actor:
                            player.ai.is_auto = False
                            engine.message_log.add_message(f"Auto-mode {player.ai.is_auto}",color.debug)
                            handler = MainGameEventHandler(engine)
                        # Check if player is still alive (needless but just in case)
                        if not player.is_alive:
                            handler = GameOverEventHandler(engine)
                        
                        handler.handle_action(player.ai)

            except Exception:  # Handle exceptions in game.
                logger.critical(traceback.format_exc())
                # traceback.print_exc()  # Print error to stderr.
                # Then print the error to the message log.
                handler.engine.message_log.add_message(traceback.format_exc(), color.error) # nuance avec isinstance
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