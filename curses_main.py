#!/usr/bin/env python3
import traceback
import logging
import os

import tcod
import curses

from typing import Any,Iterator

import util.var_global
import util.event

import exceptions
import input_handlers
import color
import setup_game
from engine import Engine
from input_handlers import MainGameEventHandler, GameOverEventHandler

from curses_renderer import Renderer
        
def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
    """If the current event handler has an active Engine then save it."""
    if isinstance(handler, input_handlers.EventHandler):
        handler.engine.save_as(filename)
        print("Game saved.")

def set_shorter_esc_delay_in_os():
    # TODO : change in python 3.9 to curses.set_escdelay(25)
    # https://stackoverflow.com/questions/27372068/why-does-the-escape-key-have-a-delay-in-python-curses
    os.environ.setdefault('ESCDELAY', '5')

def main(stdscr) -> None:
    # global xterm
    util.var_global.xterm = stdscr

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

    curses.start_color()
    curses.use_default_colors()
    for i in range(0, 16):
        curses.init_pair(i + 1, i, -1)
    
    # Same loop in color
    i=0
    for bg in range(0,16):
        for fg in range(0,16):
            i+=1
            curses.init_pair(i,fg,bg)
    

    handler: input_handlers.BaseEventHandler = setup_game.MainMenu() # gets back with MainGameEventHandler

    renderer = Renderer(stdscr=stdscr, console=tcod.Console(screen_width, screen_height, order="F"))

    renderer.console.clear()
    handler.on_render(renderer=renderer)
    renderer.context.present(renderer.console)

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
                    # Some initialization
                    handler.engine.message_log.add_message("Engine initialized",color.debug)
                    engine_ok = True
                    engine: Engine = handler.engine
                    renderer.map_width = engine.game_map.width
                    renderer.map_height = engine.game_map.height
                    renderer.camera.x = engine.player.x
                    renderer.camera.y = engine.player.y
                    engine.logger = logger
                except AttributeError:
                    engine_ok = False

            if go_draw:
                renderer.console.clear()
                handler.on_render(renderer=renderer)
                renderer.context.present(renderer.console)

            try:
                # menus before game start
                if not engine_ok:   
                        for event in util.event.wait():
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
                        # Pause ai whenever a key is pressed
                        for event in util.event.get():
                            if isinstance(event, tcod.event.KeyDown):
                                engine.player.ai.is_auto = False
                                engine.message_log.add_message(f"Auto-mode {engine.player.ai.is_auto}",color.debug)
                                handler = MainGameEventHandler(engine)

                        ##### Events that stops the auto loop #####
                        # Check FOV
                        if engine.player.see_actor:
                            engine.player.ai.is_auto = False
                            engine.message_log.add_message(f"Auto-mode {engine.player.ai.is_auto}",color.debug)
                            handler = MainGameEventHandler(engine)
                        # Check if player is still alive (needless but just in case)
                        # if not engine.player.is_alive:
                        #     handler = GameOverEventHandler(engine)
                        
                        handler.handle_action(engine.player.ai)

            except Exception:  # Handle exceptions in game.
                logger.critical(traceback.format_exc())
                handler.engine.message_log.add_message("Exception raised at Main level. Check logfile.", color.error) # nuance avec isinstance    

        event = next(util.event.wait(stdscr=stdscr))
        stdscr.addstr(i,i,type(event).__name__)

    except exceptions.QuitWithoutSaving:
        raise
    except SystemExit:  # Save and quit.
        save_game(handler, "savegame.sav")
        raise
    except BaseException:  # Save on any other unexpected exception.
        save_game(handler, "savegame.sav")
        raise



    renderer.context.message(stdscr)
    stdscr.getch()
    # stdscr.getkey()


set_shorter_esc_delay_in_os()

if __name__ == "__main__":
    curses.wrapper(main)