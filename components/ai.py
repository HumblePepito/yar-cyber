from __future__ import annotations

import random
import time
from typing import List, Optional, Tuple, TYPE_CHECKING

import numpy as np  # type: ignore
import util.calc_functions as cf
from various_enum import ItemType

import tcod
import exceptions
import color 

from actions import Action, BumpAction, MeleeAction, MovementAction, PickupAction, WaitAction, ChokeAction, FireAction
from entity import Item

if TYPE_CHECKING:
    from entity import Actor

class BaseAI(Action):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.is_auto = False

    def perform(self) -> None:
        pass
        # raise NotImplementedError()

    def get_path_to(self, dest_x: int, dest_y: int) -> List[Tuple[int, int]]:
        """Compute and return a path to the target position.
        If there is no valid path then returns an empty list.
        """
        # Copy the walkable array.
        cost = np.array(self.entity.gamemap.tiles["walkable"], dtype=np.int8)

        for entity in self.entity.gamemap.entities:
            # Check that an entiy blocks movement and the cost isn't zero (blocking.)
            if entity.blocks_movement and cost[entity.x, entity.y]:
                # Add to the cost of a blocked position.
                # A lower number means more enemies will crowd behind each other in
                # hallways.  A higher number means enemies will take longer paths in
                # order to surround the player.
                cost[entity.x, entity.y] += 10

        # Create a graph from the cost array and pass that graph to a new pathfinder.
        graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        pathfinder = tcod.path.Pathfinder(graph)

        pathfinder.add_root((self.entity.x, self.entity.y))  # Start position.

        # Compute the path to the destination and remove the starting point.
        path: List[List[int]] = pathfinder.path_to((dest_x, dest_y))[1:].tolist()

        # Convert from List[List[int]] to List[Tuple[int, int]].
        return path #[(index[0], index[1]) for index in path]

class HostileEnemy(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int,int]] = []

    def perform(self) -> None:
        """Hostile Enemy base AI will :
           * wait until player comes in view
           * move toward the player and attack
        If player move out of view, Enemy base AI will move to the last known position of the player"""

        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            target = self.engine.player
            dx = target.x - self.entity.x
            dy = target.y - self.entity.y
            distance = max(abs(dx), abs(dy))  # Chebyshev distance.
            weapon = self.entity.equipment.weapon

            # Reset cache as soon as it is not player's turn
            self.engine.game_map.player_lof.combat_stat = {}
            self.engine.game_map.hostile_lof.combat_stat = {} # TODO : at start of player turn would be better

            # bare handed
            if weapon is None:
                if distance <= 1:
                    MeleeAction(self.entity, dx, dy).perform()
            # ranged weapon
            else:
                if weapon.item_type == ItemType.RANGED_WEAPON:
                    if self.entity.distance(target.x, target.y) <= weapon.equippable.base_range:
                        self.engine.game_map.hostile_lof.compute(shooter= self.entity, target_xy=(target.x, target.y))
                        self.engine.logger.debug([entity.name for entity in self.engine.game_map.player_lof.entities])
                        self.path = self.get_path_to(target.x, target.y)
                        # add a return to quit here this perform
                        return FireAction(self.entity, target).perform()
            # melee weapon
                else:
                    if distance <= 1:
                        MeleeAction(self.entity, dx, dy).perform()

            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()

        return WaitAction(self.entity).perform()

class ConfusedEnemy(BaseAI):
    """
    A confused enemy will stumble around aimlessly for a given number of turns, then revert back to its previous AI.
    If an actor occupies a tile it is randomly moving into, it will attack.
    """
    def __init__(
        self, entity: Actor, previous_ai: Optional[BaseAI], turns_remaining: int
    ):
        super().__init__(entity)
        self.previous_ai = previous_ai
        self.turns_remaining = turns_remaining
        
    def perform(self) -> None:
        # Revert the AI back to the original state if the effect has run its course.
        if self.turns_remaining <= 0:
            self.engine.message_log.add_message(
                f"The {self.entity.name} is no longer confused."
            )
            self.entity.ai = self.previous_ai
        else:
            # Pick a random direction
            direction_x, direction_y = random.choice(
                [
                    (-1, -1),  # Northwest
                    (0, -1),  # North
                    (1, -1),  # Northeast
                    (-1, 0),  # West
                    (1, 0),  # East
                    (-1, 1),  # Southwest
                    (0, 1),  # South
                    (1, 1),  # Southeast
                ]
            )

            self.turns_remaining -= 1

            # The actor will either try to move or attack in the chosen random direction.
            # Its possible the actor will just bump into the wall, wasting a turn.
            return BumpAction(self.entity, direction_x, direction_y,).perform()

class Vanish(BaseAI):
    """
    Entity will be removed after a delay
    """
    def __init__(
        self, entity: Actor, previous_ai: Optional[BaseAI], turns_remaining: int
    ):
        super().__init__(entity)
        self.previous_ai = previous_ai
        self.turns_remaining = turns_remaining
        self.engine.game_map.tiles["transparent"][self.entity.x, self.entity.y] = False
        
    def perform(self) -> None:
        # Revert the AI back to the original state if the effect has run its course.
        if self.turns_remaining <= 0:
            self.engine.game_map.tiles["transparent"][self.entity.x, self.entity.y] = True
            self.ai = self.previous_ai
            self.entity.remove()
        else:
            # deals damage or apply status
            target_actor = self.engine.game_map.get_actor_at_location(self.entity.x, self.entity.y)
            if target_actor:
                return ChokeAction(self.entity).perform()
            
            if self.entity.name == "Bright Fire":
                self.entity.color = random.choice([color.b_orange, color.b_yellow, color.n_red])

            self.turns_remaining -= 1

            if self.turns_remaining <= 3+random.randint(-1,1):
                self.entity.char = "°"
                self.entity.fightable.base_attack //= 2
                self.engine.game_map.tiles["transparent"][self.entity.x, self.entity.y] = True
            elif self.turns_remaining <= 6+random.randint(-1,1):
                self.entity.char = "¤"
                self.engine.game_map.tiles["transparent"][self.entity.x, self.entity.y] = True
            else:
                self.entity.char = "§"

class ExploreMap(BaseAI):

    def __init__(self, entity: Actor, previous_ai: BaseAI):
        super().__init__(entity)
        self.path: List[Tuple[int,int]] = []
        self.previous_ai = previous_ai
        self.is_auto = True
        self.target = "explore" # TODO TODO : use a type enum to define the different target
        self.engine.message_log.add_message(f"Auto-mode {self.is_auto}",color.debug)

    def perform(self) -> None:
        # time.sleep(0.03)

        # TODO : check visible items, then unexplored tiles, then non-visibe explored items (end level). Anticipate order of pickup.
        try:
            if self.entity.see_actor:
                raise exceptions.AutoQuit("You are not alone")
            
            if self.engine.game_map.visible_items and self.engine.player.auto_pickup:
                # we could choose the nearest item. Order in the FOV is not really relevant
                # TODO : track ignored items
                for item in self.engine.game_map.visible_items:
                    if item.item_type.value in self.entity.auto_pickup_list:
                        self.path = self.get_path_to(item.x, item.y) # TODO : make a short path, only computing FOV, not the entire map
                        if len(self.path) == 0:
                            return PickupAction(self.entity).perform()

            if len(self.path) == 0:
                self.path = self.path_to_nearest_unexplored_tiles()

            dest_x, dest_y = self.path.pop(0)
            return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()
        except exceptions.AutoQuit as exc:
            self.is_auto = False
            self.engine.message_log.add_message(f"Auto-mode {self.is_auto}",color.debug)
            raise exceptions.Impossible(exc.args[0])

    def path_to_nearest_unexplored_tiles(self) -> List[Tuple[int, int]]:
        """start from player position and circles until a unexplored and walkable and reachable tiles is found"""
        game_map = self.engine.game_map
        player = self.entity
        result = None
        radius = 1 # useless to test 0 and 1
        dist = 1000

        # Copy the walkable array, changing boolean to 0 and 1
        walkable = np.array(self.entity.gamemap.tiles["walkable"], np.int8)
        # TODO : I believe I can add all walls with a 1000 value, this will prevent any passage through a wall and still request exploration.
        # -> will be at the end, but will still continue to check all possible tiles, not good
        size_walkable = walkable.sum()
        size_explored = game_map.explored.sum() # TODO : explored includes all wall, and also non_walkables -> comparison is not yet efficient
        # print(size_walkable)
        # print(size_explored)

        # context = self.engine.renderer.context
        # console = self.engine.renderer.console
        # for x in range(0, game_map.width):
        #     for y in range(0, game_map.height):
        #         if game_map.explored[x,y]:
        #             console.tiles_rgb["bg"][x,y] = color.gray  # add color of weapon 
        # context.present(console)
        # time.sleep(0.2)

        while result is None:
            radius += 1
            for [target_x, target_y] in cf.circle_coords(center=(player.x, player.y), radius=radius):
                if self.engine.game_map.in_bounds(target_x, target_y):
                    # print(f"player {(self.engine.player.x,self.engine.player.y)} - radius {radius} - target {(target_x, target_y)} - walkable {walkable[target_x,target_y]} - explored {game_map.explored[target_x,target_y]} - inbound {self.engine.game_map.in_bounds(target_x, target_y)}")
                    if walkable[target_x,target_y] and not game_map.explored[target_x,target_y]:
                        graph = tcod.path.SimpleGraph(cost=walkable, cardinal=2, diagonal=3)
                        pathfinder = tcod.path.Pathfinder(graph)
                        pathfinder.add_root((player.x, player.y))  # Start position.
                        path: List[List[int]] = pathfinder.path_to((target_x, target_y))[1:].tolist()
                        if len(path) < dist:
                            dist = len(path)
                            result = path
            if radius >= 60: # TODO can be optimized using count of tiles to explore vs explored
                # self.engine.message_log.add_message("There is nowhere else to explore.")
                raise exceptions.AutoQuit("There is nowhere else to explore.")

        return result

class MoveTo(BaseAI):
    def __init__(self, entity: Actor, previous_ai: BaseAI, dest_xy: Tuple(int, int)):
        super().__init__(entity)
        self.path: List[Tuple[int,int]] = []
        self.previous_ai = previous_ai
        self.is_auto = True
        self.target = "destination" # TODO : use a type enum to define the different target
        self.dest_xy = dest_xy
        self.engine.message_log.add_message(f"Auto-mode {self.is_auto}",color.debug)

    def perform(self) -> None:
        # time.sleep(0.5)

        player = self.entity

        if not self.engine.game_map.explored[self.dest_xy]:
            self.is_auto = False
            raise exceptions.Impossible("You don't know how to get there.")

        if len(self.path) == 0:
            walkable = np.array(self.entity.gamemap.tiles["walkable"], np.int8)
            graph = tcod.path.SimpleGraph(cost=walkable, cardinal=2, diagonal=3)
            pathfinder = tcod.path.Pathfinder(graph)
            pathfinder.add_root((player.x, player.y))  # Start position.
            self.path: List[List[int]] = pathfinder.path_to(self.dest_xy)[1:].tolist()

        if len(self.path) == 0:
            self.is_auto = False
            self.engine.message_log.add_message(f"Auto-mode {self.is_auto}",color.debug)
            raise exceptions.Impossible("Here you are.")

        dest_x, dest_y = self.path.pop(0)
        return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()


