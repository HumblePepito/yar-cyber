from __future__ import annotations
import os
import time

from typing import Callable, List, Optional, Tuple, TYPE_CHECKING, Union

import tcod.event
import tcod.tileset
from tcod import libtcodpy
import actions
from actions import (Action, BumpAction, WaitAction)

import color
import exceptions
import components.ai
import util.calc_functions as cf

from renderer import Renderer

if TYPE_CHECKING:
    from entity import Item, Actor
    from engine import Engine
    from components.equippable import RangedWeapon
    from renderer import Renderer

MOVE_KEYS = {
    # Vi keys.
    tcod.event.KeySym.h: (-1, 0),
    tcod.event.KeySym.j: (0, 1),
    tcod.event.KeySym.k: (0, -1),
    tcod.event.KeySym.l: (1, 0),
    tcod.event.KeySym.y: (-1, -1),
    tcod.event.KeySym.u: (1, -1),
    tcod.event.KeySym.b: (-1, 1),
    tcod.event.KeySym.n: (1, 1),
}
WAIT_KEYS = {
    tcod.event.KeySym.PERIOD,
    tcod.event.KeySym.s,
}
CURSOR_Y_KEYS = {
   tcod.event.KeySym.UP: -1,
   tcod.event.KeySym.DOWN: 1,
   tcod.event.KeySym.PAGEUP: -10,
   tcod.event.KeySym.PAGEDOWN: 10,
}
CONFIRM_KEYS = {
    tcod.event.KeySym.RETURN,
    tcod.event.KeySym.KP_ENTER,
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

            # Reset if any action was taken
            if not isinstance(action_or_state, WaitAction):
                self.engine.player.hunker_stack = 0
                self.engine.player.aim_stack = 0

            self.engine.end_turn = True
            # if not self.engine.player.is_alive:
            #     # The player was killed sometime during or after the action.
            #     return GameOverEventHandler(self.engine)
            if self.engine.player.level.requires_level_up:
                return LevelUpEventHandler(self.engine)
            return MainGameEventHandler(self.engine)  # Return to the main handler, waiting for a keystroke
        else:
            # Impossible exception raised => must stop auto_action
            if self.engine.player.ai.is_auto:
                raise exceptions.AutoQuit("You stop your actions")

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
            return False # skip enemy turn on exception (self.engine.end_turn remains false)     

        return True

    def on_render(self, renderer: Renderer) -> None:
        # Main rendering call -> engine.reder will take care of all inputs in the console
        self.engine.render(renderer)
        

class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """By default any key exits this input handler."""
        if event.sym in {  # Ignore modifier keys.
            tcod.event.KeySym.LSHIFT,
            tcod.event.KeySym.RSHIFT,
            tcod.event.KeySym.LCTRL,
            tcod.event.KeySym.RCTRL,
            tcod.event.KeySym.LALT,
            tcod.event.KeySym.RALT,
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
        elif key in CONFIRM_KEYS or key == tcod.event.KeySym.v: # TODO : supress v for lookhandler and use extra_confirm
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
        """Clamp the cursor index to the map size.""" # TODO : to the view size...!
        return (max(0, min(self.x+dx, self.engine.game_map.width - 1)),
                max(0, min(self.y+dy, self.engine.game_map.height - 1)))


    def on_render(self, renderer: Renderer) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(renderer)
        console = renderer.console
        if self.engine.game_map.visible[self.x,self.y]:
            console.rgb["bg"][renderer.shift(self.x,self.y)] = color.white
            console.rgb["fg"][renderer.shift(self.x,self.y)] = color.black
        else:
            self.engine.message_log.add_message("You can't see here.")
            console.rgb["bg"][renderer.shift(self.x,self.y)] = color.gray
            console.rgb["fg"][renderer.shift(self.x,self.y)] = color.black

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
        console.rgb["fg"] //= 8
        console.rgb["bg"] //= 8

        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg=color.white,
            bg=color.black,
            alignment=libtcodpy.CENTER,
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
            height=12,
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
            string=f"b) Strength (+1 attack, from {self.engine.player.fightable.base_attack})",
        )
        console.print(
            x=x + 1,
            y=6,
            string=f"c) Agility (+1 defense, from {self.engine.player.fightable.base_defense})",
        )
        console.print(
            x=x + 1,
            y=7,
            string=f"d) Resistance (+1 armor, from {self.engine.player.fightable.base_armor})",
        )
        console.print(
            x=x + 1,
            y=8,
            string=f"e) Speed (-5% action delay, from {self.engine.player.action_speed})",
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 4:
            if index == 0:
                player.level.increase_max_hp()
            elif index == 1:
                player.level.increase_power()
            elif index ==2:
                player.level.increase_defense()
            elif index == 3:
                player.level.increase_armor()
            elif index == 4:
                player.level.increase_speed(amount=5)
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
        index = key - tcod.event.KeySym.a

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
        self.engine.player_lof.compute(shooter= self.engine.player, target_xy=(self.x, self.y))

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))

    def clamp(self, dx,dy) -> Tuple[int,int]:
        """Clamp the cursor index to the view area."""
        return (max(max(self.engine.player.x-self.engine.renderer.view_width//2, 0), min(self.engine.player.x+self.engine.renderer.view_width//2,min(self.x+dx, self.engine.game_map.width - 1))),
                max(max(self.engine.player.y-self.engine.renderer.view_height//2, 0), min(self.engine.player.y+self.engine.renderer.view_height//2,min(self.y+dy, self.engine.game_map.width - 1))))

    def ev_keydown(self, event: tcod.event.KeyDown) -> ActionOrHandler | None:
        action_handler= super().ev_keydown(event)
        if self.engine.game_map.visible[self.x,self.y]:
            self.engine.player_lof.compute(shooter= self.engine.player, target_xy=(self.x, self.y))

        return action_handler

    def on_render(self, renderer: Renderer) -> None:
        super().on_render(renderer)
        
        if self.engine.game_map.visible[self.x,self.y]:
            console = renderer.console

            lof = self.engine.player_lof
            for [i, j] in lof.path: 
                if self.engine.game_map.tiles["light"]["ch"][i,j] == ord("#"):
                    console.rgb["bg"][renderer.shift(i,j)] = color.gray
                    console.rgb["fg"][renderer.shift(i,j)] = color.white
                elif self.engine.game_map.get_target_at_location(i, j):
                    console.rgb["bg"][renderer.shift(i,j)] = color.gray
                    console.rgb["fg"][renderer.shift(i,j)] = color.white
                else:
                    console.rgb["fg"][renderer.shift(i,j)] = color.gray
                    console.rgb["ch"][renderer.shift(i,j)] = ord("*")


            X_info = self.engine.renderer.view_width+1
            if lof.target and lof.target != self.engine.player:
                try:
                    armor = lof.target.fightable.armor
                except AttributeError:
                    armor = "na"
                try:
                    weapon_name = f"({lof.target.equipment.weapon.name.capitalize()})"
                except AttributeError:
                    weapon_name = " "
                ATT, DEF, COV = self.engine.player_lof.get_hit_stat(target_xy=(lof.target_xy),target=lof.target)
                console.print(x=X_info,y=5,string=f"Target:{lof.target.name.capitalize()} {weapon_name}")
                console.print(x=X_info,y=6,string=f"Distance:{len(lof.path)} / Armor:{armor}")
                console.print(x=X_info,y=7,string=f"Att:{ATT} vs Def:{DEF}+Cov:{COV}")

                if lof.target.is_actor:
                    self.engine.hostile_lof.compute(shooter=lof.target, target_xy=(self.engine.player.x, self.engine.player.y))
                    ATT, DEF, COV = self.engine.hostile_lof.get_hit_stat(target_xy=(self.engine.player.x, self.engine.player.y), target=self.engine.player)
                    console.print(x=X_info,y=8,string=  "   Retaliation:",fg=color.b_darkgray)
                    console.print(x=X_info,y=9,string=f"   Att:{ATT} vs Def:{DEF}+Cov:{COV}",fg=color.b_darkgray)

            if not lof.target:
                ATT, DEF, COV = self.engine.player_lof.get_hit_stat(target_xy=(lof.target_xy))
                console.print(x=X_info,y=5,string=f"No target", fg=color.b_darkgray)
                console.print(x=X_info,y=6,string=f"Distance:{len(lof.path)} / Cov:{COV}", fg=color.b_darkgray)
           

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
        self.engine.player_lof.compute(shooter= self.engine.player, target_xy=(self.x, self.y))

    def clamp(self, dx,dy) -> Tuple[int,int]:
        """Clamp the cursor index to the view area."""
        return (max(max(self.engine.player.x-self.engine.renderer.view_width//2, 0), min(self.engine.player.x+self.engine.renderer.view_width//2,min(self.x+dx, self.engine.game_map.width - 1))),
                max(max(self.engine.player.y-self.engine.renderer.view_height//2, 0), min(self.engine.player.y+self.engine.renderer.view_height//2,min(self.y+dy, self.engine.game_map.width - 1))))

    def ev_keydown(self, event: tcod.event.KeyDown) -> ActionOrHandler | None:
        action_handler= super().ev_keydown(event)
        self.engine.player_lof.compute(shooter= self.engine.player, target_xy=(self.x, self.y))

        return action_handler

    def on_render(self, renderer: Renderer) -> None:
        """Highlight the zone under the cursor while targeting."""
        super().on_render(renderer)
        console = renderer.console

        if self.engine.game_map.visible[self.x,self.y]:
            lof = self.engine.player_lof

            for [i, j] in lof.path:
                if self.engine.game_map.tiles["light"]["ch"][i,j] == ord("#"):
                    console.rgb["bg"][renderer.shift(i,j)] = color.gray
                    console.rgb["fg"][renderer.shift(i,j)] = color.white
                elif self.engine.game_map.get_target_at_location(i, j):
                    console.rgb["bg"][renderer.shift(i,j)] = color.gray
                    console.rgb["fg"][renderer.shift(i,j)] = color.white
                else:
                    console.rgb["fg"][renderer.shift(i,j)] = color.gray
                    console.rgb["ch"][renderer.shift(i,j)] = ord("*")
            
            # explosion take place just before the wall
            x,y = self.x,self.y
            if not self.engine.game_map.tiles["walkable"][x,y]:
                if len(lof.path) > 1:
                    x,y = lof.path[-2]
                else:
                    x,y = lof.shooter_xy

            for i in range(-self.radius, self.radius+1):
                for j in range(-self.radius, self.radius+1):
                    if self.engine.game_map.get_target_at_location(x+i,y+j):
                        console.rgb["bg"][renderer.shift(x+i,y+j)] = color.n_gray
                        console.rgb["fg"][renderer.shift(x+i,y+j)] = color.white
                    else:
                        if self.engine.game_map.tiles["walkable"][x+i,y+j]:
                            console.rgb["fg"][renderer.shift(x+i,y+j)] = color.n_gray
                            console.rgb["ch"][renderer.shift(x+i,y+j)] = ord("*")

            X_info = self.engine.renderer.view_width+1
            try:
                armor = lof.target.fightable.armor
            except AttributeError:
                armor = "na"
            try:
                weapon_name = f" ({lof.target.equipment.weapon.name.capitalize()})"
            except AttributeError:
                weapon_name = " "

            if lof.target and lof.target != self.engine.player:
                ATT, DEF, COV = self.engine.player_lof.get_hit_stat(target_xy=(lof.target_xy), target=lof.target)
                console.print(x=X_info,y=5,string=f"Target:{lof.target.name.capitalize()} {weapon_name}")
                console.print(x=X_info,y=6,string=f"Distance:{len(lof.path)} / Armor:{armor}")
                console.print(x=X_info,y=7,string=f"Att:{ATT} vs Def:{DEF}+Cov:{COV}")


            if not lof.target:
                ATT, DEF, COV = self.engine.player_lof.get_hit_stat(target_xy=(lof.target_xy))
                console.print(x=X_info,y=5,string=f"No target")
                console.print(x=X_info,y=6,string=f"Distance:{len(lof.path)} / Cov:{COV}")
        else:
            # target is not visible (behind walls or in a cloud or other)
            # then, on-render must take into account explored wall
            pass

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))

class MainGameEventHandler(EventHandler):

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        action: Optional[Action] = None

        key = event.sym
        player = self.engine.player
        modifier = event.mod

        
        # Reset before player's turn
        self.engine.hostile_lof.combat_stat = {}

        # action
        if key in MOVE_KEYS and not (modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT)):
            dx, dy = MOVE_KEYS[key]
            return BumpAction(player, dx, dy)
        elif key == tcod.event.KeySym.s and modifier & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
            raise SystemExit
        elif key == tcod.event.KeySym.s and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            raise SystemExit
        elif key in WAIT_KEYS:
            return WaitAction(player)
        elif key == tcod.event.KeySym.d and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            return actions.DropLastAction(player)
        elif key == tcod.event.KeySym.COMMA and not (modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT)): 
            return actions.PickupAction(player)
        elif key == tcod.event.KeySym.g and not (modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT)):
            return actions.PickupAction(player)
        elif key == tcod.event.KeySym.LESS and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            return actions.DescendAction(player)
        elif key == tcod.event.KeySym.LESS:
            return actions.AscendAction(player)
        elif key == tcod.event.KeySym.r:
            return actions.Reload(player)
        # elif key == tcod.event.KeySym.t:
        #     return actions.FireAction(player)
        elif key == tcod.event.KeySym.TAB:
            # if melee weapon, move towards nearest enemy and attack (no memory yet)
            # if ranged weapon, get into range and fire
            return actions.AutoAttack(player)
        elif key == tcod.event.KeySym.a and modifier & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
            return actions.SwitchAutoPickup(player)

        # ai
        elif key == tcod.event.KeySym.o:
            player.ai = components.ai.ExploreMap(player, player.ai)
            return player.ai
        elif key in MOVE_KEYS and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            dx, dy = MOVE_KEYS[key]
            player.ai = components.ai.Run(player, player.ai, dx, dy)
            return player.ai

        # handler
        elif key == tcod.event.KeySym.p and modifier & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
            return HistoryViewer(self.engine)
        elif key == tcod.event.KeySym.COMMA and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT): 
            return HelpViewer(self.engine)
        elif key == tcod.event.KeySym.d:
            return InventoryDropHandler(self.engine)
        elif key == (tcod.event.KeySym.i):
            return InventoryActivateHandler(self.engine)
        elif key == tcod.event.KeySym.x:
            return LookHandler(self.engine)
        elif key == (tcod.event.KeySym.x) and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            return SeeMapHandler(self.engine)
        elif key == (tcod.event.KeySym.f) and modifier & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
            return SearchHandler(self.engine)
        elif key == (tcod.event.KeySym.g) and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            return TravelHandler(self.engine)
        elif key == (tcod.event.KeySym.f):
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
    
    def ev_keydown(self, event:tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.ESCAPE:
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

        log_console = tcod.console.Console(console.width - 6, console.height - 6)

        # Draw a frame with a custom banner title.
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(
            0, 0, log_console.width, 1, "┤Message history├", alignment=libtcodpy.CENTER
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
        elif event.sym == tcod.event.KeySym.HOME:
            self.cursor = 0  # Move directly to the top message.
        elif event.sym == tcod.event.KeySym.END:
            self.cursor = self.log_length - 1  # Move directly to the last message.
        else:  # Any other key moves back to the main game state.
            return MainGameEventHandler(self.engine)
        
        return None

class HelpViewer(EventHandler):
    """Print the history on a larger window which can be navigated."""

    def __init__(self, engine: Engine):
        super().__init__(engine)

    def on_render(self, renderer: Renderer) -> None:
        super().on_render(renderer)  # Draw the main state as the background.
        console = renderer.console

        log_console = tcod.console.Console(console.width - 4, console.height - 4)

        # Draw a frame with a custom banner title.
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(
            0, 0, log_console.width, 1, "┤Help├", alignment=libtcodpy.CENTER
        )

        help_str = """
        vi keys + yubn: movements

        TAB: auto-attack        ^a: disable auto-pickup
        f: fire                 G: travel to
        r: reload               s: wait, hunker and take aim
        , or g : pickup         S (or ^s): save and quit
        d: drop                 ^p : previous message
        D: drop last item
        x: look
        >: descend
        <: try to ascend
        i: inventory
            [a-z]: use item
        o: auto-explore
        """
        
        log_console.print(1,1,help_str)
        log_console.blit(console, 2, 2)

    def ev_keydown(self, event:tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.ESCAPE:
            return MainGameEventHandler(self.engine)



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
               
        if key == tcod.event.KeySym.ESCAPE:
            return MainGameEventHandler(self.engine)
        elif key == tcod.event.KeySym.LESS and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            dest_xy = self.engine.game_map.downstairs_location
            player.ai = components.ai.MoveTo(player, player.ai, dest_xy)
            return player.ai
        elif key == tcod.event.KeySym.LESS:
            dest_xy = self.engine.game_map.upstairs_location
            player.ai = components.ai.MoveTo(player, player.ai, dest_xy)
            return player.ai

