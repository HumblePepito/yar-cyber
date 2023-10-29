from __future__ import annotations
import os
import time

from typing import Callable, List, Optional, Tuple, TYPE_CHECKING, Union

import tcod.event
import tcod.tileset
import actions
import fire_line
from actions import (Action, BumpAction, WaitAction)

import color
import exceptions
import components.ai
import util.calc_functions as cf

from renderer import Renderer

if TYPE_CHECKING:
    from engine import Engine
    from entity import Item, Actor
    from components.equippable import RangedWeapon
    from renderer import Renderer

MOVE_KEYS = {
    # Vi keys.
    tcod.event.K_h: (-1, 0),
    tcod.event.K_j: (0, 1),
    tcod.event.K_k: (0, -1),
    tcod.event.K_l: (1, 0),
    tcod.event.K_y: (-1, -1),
    tcod.event.K_u: (1, -1),
    tcod.event.K_b: (-1, 1),
    tcod.event.K_n: (1, 1),
}
WAIT_KEYS = {
    tcod.event.K_PERIOD,
    tcod.event.K_s,
}
CURSOR_Y_KEYS = {
   tcod.event.K_UP: -1,
   tcod.event.K_DOWN: 1,
   tcod.event.K_PAGEUP: -10,
   tcod.event.K_PAGEDOWN: 10,
}
CONFIRM_KEYS = {
    tcod.event.K_RETURN,
    tcod.event.K_KP_ENTER,
}


ActionOrHandler = Union[Action, "BaseEventHandler"]
"""An event handler return value which can trigger an action or switch active handlers.

If a handler is returned then it will become the active handler for future events.
If an action is returned it will be attempted and if it's valid then
MainGameEventHandler will become the active handler.
"""

class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler :
        """Handle an event and return the next active event handler."""
        state = self.dispatch(event)
        if isinstance(state, BaseEventHandler):
            return state
        assert not isinstance(state, Action), f"{self!r} can not handle actions."
        return self

    def on_render(self, renderer: Renderer) -> None:
        raise NotImplementedError()

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()
    
class EventHandler(BaseEventHandler):
    """Handler for the main part of the game. In the main game loop, on_render is called,
    then the event is catched and passed to handle_event that dispatch this event based on its type (ev_*).
    
    The dispatch either returns an action or another handler.
    If this is an action, perfom() is called for the player, then for the other actors 
    and the controls goes back to the mail loop with the MainGameEventHandler"""
    def __init__(self, engine: Engine):
        self.engine = engine

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle events for input handlers with an engine."""
        action_or_state = self.dispatch(event)
        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state
        if self.handle_action(action_or_state):
            # A valid action was performed.
            if not self.engine.player.is_alive:
                # The player was killed sometime during or after the action.
                return GameOverEventHandler(self.engine)
            elif self.engine.player.level.requires_level_up:
                return LevelUpEventHandler(self.engine)
            # elif self.engine.player.autoexplore:
            #     return AutoExploreHandler(self.engine)
            return MainGameEventHandler(self.engine)  # Return to the main handler, waiting for a keystroke
        
        return self

    def handle_action(self, action: Optional[Action]) -> bool:
        """Handle actions returned from the event methods.

        Return True if the action will advance a turn"""

        if action is None:
            return False
        
        try:
            action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            return False # skip enemy turn on exception
        
        self.engine.handle_enemy_turns()
        self.engine.update_fov() # Update the FOV before the players next action.
        return True

    def on_render(self, renderer: Renderer) -> None:
        # Main rendering call -> engine.reder will take care of all inputs in the console
        self.engine.render(renderer)


class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """By default any key exits this input handler."""
        if event.sym in {  # Ignore modifier keys.
            tcod.event.K_LSHIFT,
            tcod.event.K_RSHIFT,
            tcod.event.K_LCTRL,
            tcod.event.K_RCTRL,
            tcod.event.K_LALT,
            tcod.event.K_RALT,
        }:
            return None
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        """Called when the user is trying to exit or cancel an action.

        By default this returns to the main event handler.
        """
        return MainGameEventHandler(self.engine)

class SelectIndexHandler(AskUserEventHandler):
    """Handles asking the user for an index on the map."""

    def __init__(self, engine: Engine, default_select:str = "player", extra_confirm: Optional(str) = None):
        """Sets the cursor to the player when this handler is constructed."""
        super().__init__(engine)
        player = self.engine.player
        target: Actor = player.get_nearest_actor()
        if default_select == "enemy" and target is not None:
            self.x = target.x
            self.y = target.y
        else:    
            self.x=player.x
            self.y=player.y
        self.extra_confirm = extra_confirm

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """Check for key movement or confirmation keys."""
        key = event.sym

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            self.x, self.y = self.clamp(dx,dy)            

            return None
        elif key in CONFIRM_KEYS or key == tcod.event.K_v:
            return self.on_index_selected(self.x,self.y)
        elif self.extra_confirm:
            if key == tcod.event.KeySym(ord(self.extra_confirm)):
                return self.on_index_selected(self.x,self.y)
            else:
                return super().ev_keydown(event)
        else:
            #return self.on_exit(), equivalent à
            return super().ev_keydown(event)

    def clamp(self, dx,dy) -> Tuple[int,int]:
        """Clamp the cursor index to the map size."""
        return (max(0, min(self.x+dx, self.engine.game_map.width - 1)),
                max(0, min(self.y+dy, self.engine.game_map.height - 1)))


    def on_render(self, renderer: Renderer) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(renderer)
        console = renderer.console
        if self.engine.game_map.visible[self.x,self.y]:
            console.tiles_rgb["bg"][renderer.shift(self.x,self.y)] = color.white
            console.tiles_rgb["fg"][renderer.shift(self.x,self.y)] = color.black
        else:
            self.engine.message_log.add_message("You can't see here.")
            console.tiles_rgb["bg"][renderer.shift(self.x,self.y)] = color.gray
            console.tiles_rgb["fg"][renderer.shift(self.x,self.y)] = color.black

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Called when an index is selected."""
        raise NotImplementedError()


class PopupMessage(BaseEventHandler):
    """Display a popup text window."""

    def __init__(self, parent_handler: BaseEventHandler, text: str):
        self.parent = parent_handler
        self.text = text

    def on_render(self, renderer: Renderer) -> None:
        """Render the parent and dim the result, then print the message on top."""
        console = renderer.console
        self.parent.on_render(renderer)
        console.tiles_rgb["fg"] //= 8
        console.tiles_rgb["bg"] //= 8

        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg=color.white,
            bg=color.black,
            alignment=tcod.CENTER,
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        """Any key returns to the parent handler."""
        return self.parent

class CharacterScreenEventHandler(AskUserEventHandler):
    TITLE = "Character Information"

    def on_render(self, renderer: Renderer) -> None:
        super().on_render(renderer)
        console = renderer.console

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0

        width = len(self.TITLE) + 4

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=7,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(
            x=x + 1, y=y + 1, string=f"Level: {self.engine.player.level.current_level}"
        )
        console.print(
            x=x + 1, y=y + 2, string=f"XP: {self.engine.player.level.current_xp}"
        )
        console.print(
            x=x + 1,
            y=y + 3,
            string=f"XP for next Level: {self.engine.player.level.experience_to_next_level}",
        )

        console.print(
            x=x + 1, y=y + 4, string=f"Attack: {self.engine.player.fightable.attack}"
        )
        console.print(
            x=x + 1, y=y + 5, string=f"Defense: {self.engine.player.fightable.defense}"
        )
        console.print(
            x=x + 1, y=y + 6, string=f"Armor: {self.engine.player.fightable.armor}"
        )

class LevelUpEventHandler(AskUserEventHandler):
    TITLE = "Level Up"

    def on_render(self, renderer: Renderer) -> None:
        super().on_render(renderer)
        console = renderer.console

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        console.draw_frame(
            x=x,
            y=0,
            width=35,
            height=8,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(x=x + 1, y=1, string="Congratulations! You level up!")
        console.print(x=x + 1, y=2, string="Select an attribute to increase.")

        console.print(
            x=x + 1,
            y=4,
            string=f"a) Constitution (+20 HP, from {self.engine.player.fightable.max_hp})",
        )
        console.print(
            x=x + 1,
            y=5,
            string=f"b) Strength (+1 attack, from {self.engine.player.fightable.base_attack})", # TODO : check !!!
        )
        console.print(
            x=x + 1,
            y=6,
            string=f"c) Agility (+1 defense, from {self.engine.player.fightable.base_defense})", # TODO : check !!!
        )
        console.print(
            x=x + 1,
            y=7,
            string=f"d) Resistance (+1 armor, from {self.engine.player.fightable.base_armor})", # TODO : check !!!
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.K_a

        if 0 <= index <= 2:
            if index == 0:
                player.level.increase_max_hp()
            elif index == 1:
                player.level.increase_power()
            else:
                player.level.increase_defense()
        else:
            self.engine.message_log.add_message("Invalid entry.", color.invalid)

            return None

        return super().ev_keydown(event)

class InventoryEventHandler(AskUserEventHandler):
    """This handler lets the user select an item.

    What happens then depends on the subclass.
    """

    TITLE = "<missing title>"

    def on_render(self, renderer: Renderer) -> None:
        """Render an inventory menu, which displays the items in the inventory, and the letter to select them.
        Will move to a different position based on where the player is located, so the player can always see where
        they are.
        """
        super().on_render(renderer)
        console = renderer.console

        number_of_items_in_inventory = len(self.engine.player.inventory.items)

        height = number_of_items_in_inventory + 2

        if height <= 3:
            height = 3

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0

        width = len(self.TITLE) + 4

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if number_of_items_in_inventory > 0:
            for i, item in enumerate(self.engine.player.inventory.items):
                item_key = chr(ord("a") + i)
                item_string = f"{item_key} - {item.name}"

                if self.engine.player.equipment.item_is_equipped(item):
                    item_string = f"{item_string} (E)"

                console.print(x + 1, y + i + 1, item_string)
        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.K_a

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Called when the user selects a valid item."""
        raise NotImplementedError()
   
class InventoryActivateHandler(InventoryEventHandler):
    """Handle using an inventory item."""

    TITLE = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Return the action for the selected item : consumable or equipment"""
        if item.consumable:
            # Return the action for the selected item.
            return item.consumable.get_action(self.engine.player)
        elif item.equippable:
            return actions.EquipAction(self.engine.player, item)
        else:
            return None

class InventoryDropHandler(InventoryEventHandler):
    """Handle dropping an inventory item."""

    TITLE = "Select an item to drop"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Drop this item."""
        return actions.DropItem(self.engine.player, item)

class LookHandler(SelectIndexHandler):
    """Lets the player look around using the keyboard."""

    # TODO : add neatly the v charater to confirm the view ; cf FireEvent
    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Return to main handler."""
        lookup_list:list = []
        for entity in self.engine.game_map.get_entities_at_location(self.x, self.y):
            lookup_list.append(entity.name)

        if len(lookup_list) > 0:
            self.engine.message_log.add_message(f"You see: {lookup_list}")
        else:
            self.engine.message_log.add_message(f"Nothing here.")
        
        return MainGameEventHandler(self.engine)

    def on_render(self, renderer: Renderer) -> None:
        super().on_render(renderer)
        renderer.console.print(x=50,y=3,string=f"x={self.x}, y={self.y}")

class SingleRangedAttackHandler(SelectIndexHandler):
    """Handles targeting a single enemy. Only the enemy selected will be affected."""

    def __init__(
        self, 
        engine: Engine, 
        callback: Callable[[Tuple[int, int]], Optional[Action]],
        default_select:str = "player",
        extra_confirm: Optional(str) = None,
    ):
        super().__init__(engine=engine, default_select=default_select, extra_confirm=extra_confirm)
        self.callback = callback

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))

    def clamp(self, dx,dy) -> Tuple[int,int]:
        """Clamp the cursor index to the visible area."""
        if not self.engine.game_map.visible[self.x+dx,self.y+dy]:
            return (self.x, self.y)

        return (max(0, min(self.x+dx, self.engine.game_map.width - 1)),
                max(0, min(self.y+dy, self.engine.game_map.height - 1)))

    def on_render(self, renderer: Renderer) -> None:
        super().on_render(renderer)
        console = renderer.console

        # fire_line: List = tcod.los.bresenham((self.engine.player.x, self.engine.player.y), (self.x, self.y)).tolist()
        # fire_line: List = cf.move_path(map_fov=self.engine.game_map.tiles, shooter_xy=(self.engine.player.x, self.engine.player.y),target_xy=(self.x, self.y))["path"].squeeze(axis=(1,)).tolist() 
        # fire_line.pop(0)
        # fire_line = cf.fire_line(map_fov=self.engine.game_map.tiles, shooter_xy=(self.engine.player.x, self.engine.player.y),target_xy=(self.x, self.y))
        lof = self.engine.game_map.fire_line.compute(shooter= self.engine.player, target_xy=(self.x, self.y))

        # Combat stat
        if lof.target and lof.target != lof.shooter:
            ATT, DEF, COV = lof.get_hit_stat(target=lof.target)
            # console.print(x=0,y=25,string=f"ATT: {ATT} vs DEF: {DEF} + COV: {COV} ")
            console.print(x=40,y=5,string=f"ATT: {ATT} vs DEF: {DEF} + COV: {COV} ")

        for [i, j] in lof.path: 
            if self.engine.game_map.tiles["light"]["ch"][i,j] == ord("#"):
                console.tiles_rgb["bg"][renderer.shift(i,j)] = color.gray
                console.tiles_rgb["fg"][renderer.shift(i,j)] = color.white
            elif self.engine.game_map.get_actor_at_location(i, j):
                console.tiles_rgb["bg"][renderer.shift(i,j)] = color.gray
                console.tiles_rgb["fg"][renderer.shift(i,j)] = color.white
            else:
                console.tiles_rgb["fg"][renderer.shift(i,j)] = color.gray
                console.tiles_rgb["ch"][renderer.shift(i,j)] = ord("*")
        
           

class AreaRangedAttackHandler(SelectIndexHandler):
    """Handles targeting a zone. All enemies in the zone will be affected, including player."""

    def __init__(
        self, 
        engine: Engine,
        radius: int,
        callback: Callable[[Tuple[int, int]], Optional[Action]],
        default_select:str = "player",
        extra_confirm: Optional(str) = None,
    ):
        super().__init__(engine=engine, default_select=default_select, extra_confirm=extra_confirm)
        self.radius = radius
        self.callback = callback

    def clamp(self, dx,dy) -> Tuple[int,int]:
        """Clamp the cursor index to the visible area."""
        if not self.engine.game_map.visible[self.x+dx,self.y+dy]:
            return (self.x, self.y)

        return (max(0, min(self.x+dx, self.engine.game_map.width - 1)),
                max(0, min(self.y+dy, self.engine.game_map.height - 1)))


    def on_render(self, renderer: Renderer) -> None:
        """Highlight the zone under the cursor."""
        """TODO : take care of collision with walls"""
        super().on_render(renderer)
        console = renderer.console

        lof = self.engine.game_map.fire_line.compute(shooter= self.engine.player, target_xy=(self.x, self.y))

        for [i, j] in lof.path:
            if self.engine.game_map.tiles["light"]["ch"][i,j] == ord("#"):
                console.tiles_rgb["bg"][renderer.shift(i,j)] = color.gray
                console.tiles_rgb["fg"][renderer.shift(i,j)] = color.white
            elif self.engine.game_map.get_actor_at_location(i, j):
                console.tiles_rgb["bg"][renderer.shift(i,j)] = color.gray
                console.tiles_rgb["fg"][renderer.shift(i,j)] = color.white
            else:
                console.tiles_rgb["fg"][renderer.shift(i,j)] = color.gray
                console.tiles_rgb["ch"][renderer.shift(i,j)] = ord("*")
        
        if lof.end > 0:
            x,y = lof.path[-1]
            if not self.engine.game_map.tiles["walkable"][x,y]:
                x,y = lof.path[-2]
        else:
            x,y = self.x,self.y

        for i in range(-self.radius, self.radius+1):
            for j in range(-self.radius, self.radius+1):
                if self.engine.game_map.get_actor_at_location(x+i,y+j):
                    console.tiles_rgb["bg"][renderer.shift(x+i,y+j)] = color.gray
                    console.tiles_rgb["fg"][renderer.shift(x+i,y+j)] = color.white
                else:
                    if self.engine.game_map.tiles["walkable"][x+i,y+j]:
                        console.tiles_rgb["fg"][renderer.shift(x+i,y+j)] = color.gray
                        console.tiles_rgb["ch"][renderer.shift(x+i,y+j)] = ord("*")


    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))

# class FireHandler(EventHandler):
#     """Handles shooting at a single target or at a direction."""
#     def __init__(self, engine: Engine):
#         super().__init__(engine)
#         self.item = engine.player.equipment.weapon   
#         try:
#             if self.item.equippable.is_ranged:
#                 self.ranged_weapon: RangedWeapon = self.item.equippable
#         except AttributeError:
#             self.ranged_weapon = None

#     def handle_action(self, action: Optional[Action]) -> bool:
#         """Handle specific fire actions : depends on the weapon.

#         Return True if the action will advance a turn"""

#         action: Action = self.ranged_weapon.get_fire_action(self.engine.player)        
#         super().handle_action(action)


class MainGameEventHandler(EventHandler):

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        action: Optional[Action] = None

        key = event.sym
        player = self.engine.player
        modifier = event.mod
        
        # action
        if key in MOVE_KEYS and not (modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT)):
            dx, dy = MOVE_KEYS[key]
            return BumpAction(player, dx, dy)
        elif key in WAIT_KEYS:
            return WaitAction(player)
        elif key == tcod.event.K_ESCAPE:
            raise SystemExit
        elif key == tcod.event.K_d and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            return actions.DropLastAction(player)
        elif key == tcod.event.K_COMMA: #or key == tcod.event.K_g:
            return actions.PickupAction(player)
        elif key == tcod.event.K_LESS and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            return actions.DescendAction(player)
        elif key == tcod.event.K_LESS:
            return actions.AscendAction(player)
        elif key == tcod.event.K_r:
            return actions.Reload(player)
        elif key == tcod.event.K_t:
            return actions.FireAction(player)
        elif key == tcod.event.K_TAB:
            # if melee weapon, move towards nearest enemy and attack (no memory yet)
            # if ranged weapon, get into range and fire
            return actions.AutoAttack(player)
        elif key == tcod.event.K_a and modifier & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
            return actions.SwitchAutoPickup(player)

        # ai
        elif key == tcod.event.K_o:
            player.ai = components.ai.ExploreMap(player, player.ai)
            return player.ai
            # return actions_ai.ExploreAIAction(player)
        elif key in MOVE_KEYS and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            dx, dy = MOVE_KEYS[key]
            player.ai = components.ai.Run(player, player.ai, dx, dy)
            return player.ai

        # handler
        elif key == tcod.event.K_p and modifier & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
            return HistoryViewer(self.engine)
        elif key == tcod.event.K_d:
            return InventoryDropHandler(self.engine)
        elif key == (tcod.event.K_i):
            return InventoryActivateHandler(self.engine)
        elif key == tcod.event.K_x:
            return LookHandler(self.engine)
        elif key == (tcod.event.K_x) and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            return SeeMapHandler(self.engine)
        elif key == (tcod.event.K_f) and modifier & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
            return SearchHandler(self.engine)
        elif key == (tcod.event.K_g) and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            return TravelHandler(self.engine)
        elif key == (tcod.event.K_f):
            # Use the attack handler of the used ranged weapon
            return player.equipment.fire_event()

        else:
            self.engine.message_log.add_message(f"Unknown command : {key}")

        # No valid key was pressed
        return action

class GameOverEventHandler(EventHandler):
    def on_quit(self) -> None:
        """Handle exiting out of a finished game."""
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")  # Deletes the active save file.
        raise exceptions.QuitWithoutSaving()  # Avoid saving a finished game.

    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()
    
    def ev_keydown(self, event:tcod.event.KeyDown) ->None:
        if event.sym == tcod.event.K_ESCAPE:
            self.on_quit()

class HistoryViewer(EventHandler):
    """Print the history on a larger window which can be navigated."""

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.log_length = len(engine.message_log.messages)
        self.cursor = self.log_length - 1

    def on_render(self, renderer: Renderer) -> None:
        super().on_render(renderer)  # Draw the main state as the background.
        console = renderer.console

        log_console = tcod.Console(console.width - 6, console.height - 6)

        # Draw a frame with a custom banner title.
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(
            0, 0, log_console.width, 1, "┤Message history├", alignment=tcod.CENTER
        )

        # Render the message log using the cursor parameter.
        self.engine.message_log.render_messages(
            log_console,
            1,
            1,
            log_console.width - 2,
            log_console.height - 2,
            self.engine.message_log.messages[: self.cursor + 1],
        )
        log_console.blit(console, 3, 3)

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        # Fancy conditional movement to make it feel right.
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0 and self.cursor == 0:
                # Only move from the top to the bottom when you're on the edge.
                self.cursor = self.log_length - 1
            elif adjust > 0 and self.cursor == self.log_length - 1:
                # Same with bottom to top movement.
                self.cursor = 0
            else:
                # Otherwise move while staying clamped to the bounds of the history log.
                self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
        elif event.sym == tcod.event.K_HOME:
            self.cursor = 0  # Move directly to the top message.
        elif event.sym == tcod.event.K_END:
            self.cursor = self.log_length - 1  # Move directly to the last message.
        else:  # Any other key moves back to the main game state.
            return MainGameEventHandler(self.engine)
        
        return None

class SeeMapHandler(AskUserEventHandler):
    pass

class SearchHandler(AskUserEventHandler):
    pass

class TravelHandler(AskUserEventHandler):

    TITLE = "Select destination"

    def on_render(self, renderer: Renderer) -> None:
        """Render a text menu.
        """
        #self.message_log.render(console,38,40,42,9)

        super().on_render(renderer)
        console = renderer.console

        x = renderer.view_width//2
        y = renderer.view_height//2

        width = len(self.TITLE) + 4
        height = 5

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        # TODO need a loop through all existing and visited places : for places in enumerate(self.engine.visited_places))
        console.print(x + 1, y + 1, "> : down stairs")
        console.print(x + 1, y + 2, "< : up stairs")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        action: Optional[Action] = None

        key = event.sym
        player = self.engine.player
        modifier = event.mod
               
        if key == tcod.event.K_ESCAPE:
            return MainGameEventHandler(self.engine)
        elif key == tcod.event.K_LESS and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            dest_xy = self.engine.game_map.downstairs_location
            player.ai = components.ai.MoveTo(player, player.ai, dest_xy)
            return player.ai
            # return actions_ai.TravelAIAction(player,">")
        elif key == tcod.event.K_LESS:
            dest_xy = self.engine.game_map.upstairs_location
            player.ai = components.ai.MoveTo(player, player.ai, dest_xy)
            return player.ai
            # return actions_ai.TravelAIAction(player,"<")

