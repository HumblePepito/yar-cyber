from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from tcod.map import compute_fov
import tcod.constants

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

    def handle_enemy_turns(self) -> None:
        for entity in (set(self.game_map.actors) - {self.player}) | set(self.game_map.hazards):  # not only actors; TOODO : and features ?
            # if entity.ai:
            try:
                entity.ai.perform()
            except exceptions.Impossible:
                pass # ignore when trouble

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
        if renderer and not self.renderer:
            self.renderer = renderer
            self.message_log.add_message("init of engine's renderer",color.debug)

        # section carte, centered on player
        # self.game_map.render(renderer, self.view_width, self.view_height)
        self.game_map.render(renderer)

        # section personnage
        console.print(
            x=40,
            y=0,
            string=f"HP: {self.player.fightable.hp}/{self.player.fightable.max_hp}")
        render_ascii_bar(console,"=",progress_color(self.player.fightable.hp,self.player.fightable.max_hp),"-",color.b_darkgray,50,0,self.player.fightable.hp,self.player.fightable.max_hp,24)

        # console.print(x=40,y=1,string=f"Floor level :  {self.game_world.current_floor}")
        console.print(x=40,y=2,string=f"Player level : {self.player.level.current_level} - XP: {self.player.level.current_xp}/{self.player.level.experience_to_next_level}")

        weapon = self.player.equipment.weapon
        clip_msg = ""
        if weapon is None:
            msg = "Punch"
        elif weapon.item_type == ItemType.RANGED_WEAPON:
            msg = f"Weapon: {weapon.name} - Clip: "
            clip_msg = f"{weapon.equippable.current_clip}/{weapon.equippable.clip_size}"
        elif weapon.item_type == ItemType.MELEE_WEAPON:
            msg = f"Weapon: {weapon.name}"
        
        console.print(x=40,y=4,string=msg)
        if clip_msg:
            console.print(x=40+len(msg),y=4,string=clip_msg,fg=progress_color(weapon.equippable.current_clip,weapon.equippable.clip_size))

        # section message
        self.message_log.render(console,40,18,40,6)

        # section liste monstres
        i=0
        for actor in set(self.game_map.actors) - {self.player}:
            if actor.is_alive and self.game_map.visible[actor.x,actor.y]:
                weapon = actor.equipment.weapon 
                if weapon:
                    string=f"{actor.name.capitalize()} with a {weapon.name.capitalize()}"
                else:
                    string=actor.name.capitalize()

                console.print(x=40,y=11+i,string=" " ,bg=progress_color(actor.fightable.hp,actor.fightable.max_hp))
                console.print(x=42,y=11+i,string=string,fg=color.red)
                i=i+1

        #context.present(console)

        #console.clear()
        #print(console)

    def save_as(self, filename: str) -> None:
        """Save this Engine instance as a compressed file."""
        self.renderer = None # purge of context & console from engine
        
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)

    def print(self,*message_objet: object) -> None:
        pass 