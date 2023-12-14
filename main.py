#!/usr/bin/env python3
import traceback
import logging
import os
import argparse

import tcod
import curses

import util.var_global
import util.event
from util.charmap import CHARMAP_CP437_pepito

import exceptions
import input_handlers

import color
import setup_game
from engine import Engine
from input_handlers import GameOverEventHandler

from renderer import Renderer
import curses_renderer

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

    # log tool
    Log_Format = "%(levelname)s %(asctime)s - %(message)s"
    logging.basicConfig(
        filename="logfile.log", filemode="w", format=Log_Format, level=logging.DEBUG
    )
    logger = logging.getLogger()
    util.var_global.logger = logger
    logger.info(f"Commandline parameters: {config}")

    handler: input_handlers.BaseEventHandler = setup_game.MainMenu() # gets back with MainGameEventHandler

    if config['curses']:
        # global xterm
        util.var_global.xterm = stdscr
        screen_width, screen_height = curses.COLS-1, curses.LINES
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

        renderer = curses_renderer.Renderer(stdscr=stdscr, console=tcod.console.Console(screen_width, screen_height, order="F"))
    else:
        FLAGS = tcod.context.SDL_WINDOW_RESIZABLE
        # size of console
        screen_width = 80
        screen_height = 24
        #https://python-tcod.readthedocs.io/en/latest/tcod/getting-started.html#dynamically-sized-console
        if png:
            tileset_filename=png
        else:
            tileset_filename="./png/Cheepicus_14x14.png"
            # tileset_filename="./png/Bisasam_20x20_ascii.png"

        tileset = tcod.tileset.load_tilesheet(
            tileset_filename, 16, 16, CHARMAP_CP437_pepito
        )

        context = tcod.context.new(
            x=0,
            y=0,
            columns=screen_width,
            rows=screen_height,
            # width=1600,
            # height=480,
            tileset=tileset,
            title="Sci-fi Roguelike Tutorial",
            vsync=True,
            sdl_window_flags=FLAGS
        )
        # Use of renderer instead of console in order to add both Console & Context to the engine and use it in auto-Handlers
        renderer = Renderer(context=context, console=context.new_console(min_columns=screen_width, min_rows=screen_height, order="F"))

    # renderer.console.clear()
    # handler.on_render(renderer=renderer)
    # renderer.context.present(renderer.console)

    # Boucle principale !!
    engine_ok = False
    resize = False
    try:
        while True:
            if resize:
                resize = False
                size = renderer.context.recommended_console_size()
                logger.debug(f"context cols={size[0]} lines={size[1]}")
                renderer.view_width=size[0]-41
                if renderer.view_width//2 == renderer.view_width/2:
                    renderer.view_width -= 1
                renderer.view_height=size[1]-1
                if renderer.view_height//2 == renderer.view_height/2:
                    renderer.view_height -= 1
                
                renderer.console = context.new_console(order="F")

                # renderer.view_width=size[0]-40
                # renderer.view_height=size[1]-1
                logger.debug(f"width={renderer.view_width} height={renderer.view_height}")
                if size[0] <screen_width or size[1] < screen_height:
                    print("Min size of console is 80x24.")
                    raise SystemExit

            if not engine_ok:
                try:
                    # Some initialization
                    engine_ok = True
                    engine: Engine = handler.engine
                    engine.renderer = renderer
                    renderer.camera.x = engine.player.x
                    renderer.camera.y = engine.player.y
                    engine.logger = logger
                    engine.logger.info("Engine initialized")
                except AttributeError:
                    engine_ok = False
            
            try:
                # menus before game start
                if not engine_ok or isinstance(handler,GameOverEventHandler):   # menus before or after game
                    renderer.console.clear()
                    handler.on_render(renderer=renderer)
                    renderer.context.present(renderer.console, keep_aspect= True, integer_scaling=True)
                    for event in util.event.wait():
                        #context.convert_event(event) # for mouse
                        handler = handler.handle_events(event)
                elif engine_ok:
                    if not engine.player.ai.is_auto:
                        # normal mode
                        handler = engine.turn_loop(handler)
                    else:
                        # auto mode
                        handler = engine.turn_loop_auto(handler)
                    
            except IndexError:
                # turnqueue pb is the most common
                logger.critical(traceback.format_exc())
                raise
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



parser = argparse.ArgumentParser(description='Dive into cyber alternative life.',epilog='Have fun and stay alive...')
parser.add_argument('-c', '--curses', action='store_true', help='use curses rendering in terminal')
parser.add_argument('-s', '--seed', type=int, help='fixed seed for static generation')
parser.add_argument('-t', '--tiles', dest='png' , type=str, help="path to a specific PNG tiles file (charmap CP437)")
parser.add_argument('-w', '--wizard', action='store_true', help='start in wizard mode')
args = parser.parse_args()
config = vars(args)

if __name__ == "__main__":
    if config['seed'] or config['wizard']:
        print("Not yet implemented")

    if config['curses']:
        set_shorter_esc_delay_in_os()
        curses.wrapper(main)
    else:
        png = config['png']
        main('dummy')
