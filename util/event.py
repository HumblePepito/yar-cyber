from __future__ import annotations

from typing import Any,Iterator, Callable, TYPE_CHECKING

import curses
import tcod
import util.var_global as uv

# if TYPE_CHECKING:

# def wait(stdscr: curses._CursesWindow = None) -> Iterator[Any]:
def wait() -> Iterator[Any]:
    if not uv.xterm:
        return tcod.event.wait()
    else:
        # scancode https://python-tcod.readthedocs.io/en/latest/tcod/event.html#tcod.event.Scancode
        # keysim https://python-tcod.readthedocs.io/en/latest/tcod/event.html#tcod.event.KeySym
        # mod https://python-tcod.readthedocs.io/en/latest/tcod/event.html#tcod.event.Modifier
        uv.xterm.nodelay(False)
        key = uv.xterm.getch()
        mod = 0
        if key >= 97 and key <= 122:
            mod = 0
        elif key >= 65 and key <= 90:
            mod = 3 # shift
            key += 32
        elif key == 62: # shift+G
            key = 60
            mod = 3
        elif key == 16: # ctrl+P
            key = 112
            mod = 192       
        elif key == 63: # shift+,
            mod=3
            key=44


        event = tcod.event.KeyDown(scancode=0,sym=key,mod=mod)
        event.type = "KEYDOWN"

        # if key == curses.KEY_RESIZE or key == curses.KEY_MAX:
        #     event = tcod.event.WindowEvent()
        
        return [event] # TODO : iterator ??

def get() -> Iterator[Any]:

    if not uv.xterm:
        levent = tcod.event.get()
        yield from (
            event
            for event in levent
            if isinstance(event, tcod.event.KeyDown)
        )
    else:
        uv.xterm.nodelay(True)
        key = uv.xterm.getch()
        mod = 0
        if key == -1:
            return None
        else:
            event = tcod.event.KeyDown(scancode=0,sym=key,mod=mod)
            event.type = "KEYDOWN"

            yield event
        