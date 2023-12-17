from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from tcod.map import compute_fov
import tcod.constants
import util.event

from logging import Logger
from util.calc_functions import progress_color
from various_enum import ItemType


#from actions import EscapeAction, MovementAction, BumpAction, MeleeAction
from render_functions import render_ascii_bar
from message_log import MessageLog

import exceptions
import lzma
import pickle
import color
from input_handlers import BaseEventHandler, GameOverEventHandler, MainGameEventHandler
from turnqueue import TurnQueue

if TYPE_CHECKING:
    from entity import Actor
    from game_map import GameMap, GameWorld
    from renderer import Renderer


class Engine:
    game_map: GameMap
    game_world: GameWorld
    
    def __init__(self, player: Actor):
        self.player = player
        self.renderer: Renderer = None
        self.message_log = MessageLog()
        self.logger: Logger = None
        self.end_turn: bool = True # player has made a valid action
        self.is_keypressed: bool = True # key stroke

        self.turnqueue: TurnQueue = TurnQueue()
        self.active_entity = None
        self.turn_count = 0

    def turn_loop(self, handler: BaseEventHandler) -> BaseEventHandler:
        """Plays all entities and ends with player."""
        while True:
            if self.end_turn:
                self.active_entity = self.turnqueue.invoke_next()

            if self.active_entity is self.player:
                if self.is_keypressed:
                    ### LOG
                    self.logger.debug(f"Turn queue time {self.turnqueue.current_time}")
                    self.logger.debug(f"TQ size: {len(self.turnqueue.heap)}")
                    msg = ""
                    player = 0
                    for ticket in sorted(self.turnqueue.heap):
                        msg += f"{ticket.entity.name}:{ticket.time},{ticket.ticket_id} - "
                        if ticket.entity is self.player:
                            player += 1
                    self.logger.debug(f"TQ:{msg}")
                    # assert player == 0
                    ### LOG

                    """render all previous actions (and avoid render for non-valid event)
                        -> has to be done before the next keystroke, thus the self.is_keypressed"""
                    self.renderer.console.clear()
                    handler.on_render(renderer=self.renderer)
                    self.renderer.context.present(self.renderer.console, keep_aspect= True, integer_scaling=True)

                self.end_turn = False # to prevent other event (windowfocus, keyup) to trigger the loop
                self.is_keypressed = False
                for event in util.event.wait():
                    if isinstance(event, tcod.event.KeyDown):
                        self.is_keypressed = True
                        try:
                            handler = handler.handle_events(event)
                        except exceptions.AutoQuit as exc:
                            # auto cannot start and trigers an AutoQuit
                            self.player.ai.is_auto = False
                            self.logger.info(f"Auto-mode {self.player.ai.is_auto}")
                            self.message_log.add_message(exc.args[0], color.impossible)
                            handler = MainGameEventHandler(self)
                    elif isinstance(event, tcod.event.WindowResized):
                        resize = True
                
                if self.end_turn:
                    self.update_fov()
                    # regular event
                    increment = self.turnqueue.current_time//60 - self.turn_count
                    if increment >=  1:
                        self.clock_operation(increment)

                return handler
            else:
                try:
                    self.handle_enemy_turns()
                except exceptions.Dead:
                    print("dead")
                    return GameOverEventHandler(self)

    def turn_loop_auto(self, handler: BaseEventHandler) -> BaseEventHandler:
        while True:
            self.active_entity = self.turnqueue.invoke_next()
            if self.active_entity is self.player:
                # render all previous actions
                self.renderer.console.clear()
                handler.on_render(renderer=self.renderer)
                self.renderer.context.present(self.renderer.console, keep_aspect= True, integer_scaling=True)

                ##### Events that stops the auto loop #####
                
                # Stop auto if a key is pressed
                for event in util.event.get():
                    if isinstance(event, tcod.event.KeyDown):
                        self.player.ai.is_auto = False
                        self.logger.info(f"Auto-mode {self.player.ai.is_auto}")
                        handler = MainGameEventHandler(self)

                try:
                    handler.handle_action(self.player.ai)
                except exceptions.AutoQuit as exc:
                    self.player.ai.is_auto = False
                    self.logger.info(f"Auto-mode {self.player.ai.is_auto}")
                    self.message_log.add_message(exc.args[0], color.impossible)
                    self.turnqueue.reschedule(0, self.player)

                self.update_fov()
                # regular event
                increment = self.turnqueue.current_time//60 - self.turn_count
                if increment >=  1:
                    self.clock_operation(increment)
                    
                return handler
            else:
                self.handle_enemy_turns()

    def clock_operation(self, increment: int) -> None:
        """Activate regular timer"""
        self.turn_count += increment
        self.turnqueue.last_time = self.turnqueue.current_time 
        for actor in self.game_map.actors:
            actor.fightable.stun_point = max(0, actor.fightable.stun_point-increment)
        
            if actor.effects:
                for key in list(actor.effects):
                    actor.effects[key]['duration'] -= 1
                    if actor.effects[key]['duration'] == 0:
                        del actor.effects[key]

    def handle_enemy_turns(self) -> None:
            try:
                # if trouble, will no reschedule normally
                self.active_entity.ai.perform()
            except exceptions.Impossible:
                # hostile loses its turn and ignore when trouble, place it at end of queue
                self.turnqueue.reschedule(60,self.active_entity)
            except AttributeError as exc:
                # no ai
                self.logger.error(f"No ai : AttributeError in perform from {self.active_entity}. {exc.args[0]}")
                pass

    def update_fov(self) -> None:
        """Recompute the visible area based on the players point of view."""
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles["transparent"],
            (self.player.x, self.player.y),
            radius=10, # FOV radius
            algorithm = tcod.constants.FOV_PERMISSIVE_7  #FOV_DIAMOND # or RESTRICTIVE,
        )
        # If a tile is "visible" it should be added to "explored".
        self.game_map.explored |= self.game_map.visible
    
    def render(self, renderer: Renderer ) -> None:
        # init of engine to provide access to render for auto handler
        console = renderer.console

        X_info = self.renderer.view_width+1
        # map section, centered on player
        self.game_map.render(renderer)

        # section personnage
        msg=f"Health:{self.player.fightable.hp}/{self.player.fightable.max_hp}"
        console.print(x=X_info, y=0, string=msg)
        render_ascii_bar(console,"=",progress_color(self.player.fightable.hp,self.player.fightable.max_hp),"-",color.b_darkgray,X_info+len(msg)+1,0,self.player.fightable.hp,self.player.fightable.max_hp,24)
        
        console.print(x=X_info, y=1, string=f"Stun:  {self.player.fightable.stun_point}")
        if self.player.fightable.stun_point <= 24:
            render_ascii_bar(console,"*",color.b_blue,"-",color.b_darkgray,X_info+len(msg)+1,1,self.player.fightable.stun_point,24,24)
        else:
            render_ascii_bar(console,"+",color.b_cyan,"*",color.b_blue,X_info+len(msg)+1,1,self.player.fightable.stun_point-24,24,24)


        console.print(x=X_info,y=2,string=f"Player lvl:{self.player.level.current_level} - Floor lvl:{self.game_world.current_floor} - Turn:{self.turn_count}")

        weapon = self.player.equipment.weapon
        clip_msg = ""
        if weapon is None:
            msg = "Punch"
        elif weapon.item_type == ItemType.RANGED_WEAPON:
            msg = f"Weapon: {weapon.name} - Clip: "
            clip_msg = f"{weapon.equippable.current_clip}/{weapon.equippable.clip_size}"
        elif weapon.item_type == ItemType.MELEE_WEAPON:
            msg = f"Weapon: {weapon.name}"
        
        console.print(x=X_info,y=3,string=msg)
        if clip_msg:
            console.print(x=X_info+len(msg),y=3,string=clip_msg,fg=progress_color(weapon.equippable.current_clip,weapon.equippable.clip_size))
        if self.player.aim_stack:
            console.print(x=X_info+len(msg)+len(clip_msg),y=3,string=f" Aim {self.player.aim_stack}")

        if self.player.effects:
            status=""
            l=0
            for key in list(self.player.effects):
                status += f"{self.player.effects[key]['name']}:{self.player.effects[key]['duration']} " 
                if self.player.effects[key]['duration'] == 1:
                    console.print(x=X_info,y=4+l,string=status,fg=color.n_gray)
                else:
                    console.print(x=X_info,y=4+l,string=status)
                l=len(status)
                
        # section message
        self.message_log.render(console,X_info,18,X_info,6)

        # section liste monstres
        i=0
        for actor in set(self.game_map.actors) - {self.player}:
            if actor.is_alive and self.game_map.visible[actor.x,actor.y]:
                weapon = actor.equipment.weapon 
                if weapon:
                    string=f"{actor.name.capitalize()} with a {weapon.name.capitalize()}"
                else:
                    string=actor.name.capitalize()

                console.print(x=X_info,y=11+i,string=" " ,bg=progress_color(actor.fightable.hp,actor.fightable.max_hp))
                console.print(x=X_info+2,y=11+i,string=string,fg=color.red)
                i=i+1

    def save_as(self, filename: str) -> None:
        """Save this Engine instance as a compressed file."""
        self.renderer = None # purge of context & console from engine
        
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)
