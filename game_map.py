from __future__ import annotations

from typing import Iterable, Iterator, List, Optional, Tuple, TYPE_CHECKING
# NamedTuple : https://stackoverflow.com/questions/2970608/what-are-named-tuples-in-python#2970722
import numpy as np  # type: ignore
import random

from entity import Actor, Entity, Feature, Hazard, Item

import tile_types

if TYPE_CHECKING:
    from engine import Engine
    from renderer import Renderer 

        
class GameMap:
    def __init__(self, engine: Engine, width: int, height: int, branch: str, depth: int, entities: Iterable[Entity] = ()):
        self.engine = engine
        self.width, self.height = width, height
        self.branch = branch
        self.depth = depth
        self.entities = set(entities)

        self.tiles = np.full((width, height), fill_value=tile_types.wall, order="F")
        self.visible = np.full((width, height), fill_value=False, order="F") # Tiles the player can currently see
        self.explored = np.full((width, height), fill_value=False, order="F") # Tiles the player has seen before

        self.upstairs_location =(0,0)
        self.downstairs_location =(0,0)

        self.wall: Entity = None
        self.trails: List[Tuple[int, int]] = []

    
    @property
    def gamemap(self) -> GameMap:
        return self

    @property
    def visible_entities(self) -> Iterator[Entity]:
        """Iterate over this maps living and visible entities."""
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Entity) and entity.is_visible
        )

    @property
    def actors(self) -> Iterator[Actor]:
        """Iterate over this maps living actors."""
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Actor) and entity.is_alive
        )
        
    @property
    def items(self) -> Iterator[Item]:
        """Iterate over this maps items."""
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Item)
        )

    @property
    def features(self) -> Iterator[Feature]:
        """Iterate over this maps features."""
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Feature)
        )

    @property
    def hazards(self) -> Iterator[Feature]:
        """Iterate over this maps features."""
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Hazard)
        )

    @property
    def visible_actors(self) -> Iterator[Actor]:
        """Iterate over this maps living and visible actors."""
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Actor) and entity.is_alive and entity.is_visible
        )

    @property
    def visible_items(self) -> Iterator[Item]:
        """Iterate over this maps visible items."""
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Item) and entity.is_visible
        )

    def get_actor_at_location(self, x: int, y: int) -> Optional[Actor]:
        for actor in self.actors:
            if actor.x == x and actor.y == y and actor.is_alive:
                return actor
        return None

    def get_item_at_location(self, x: int, y: int) -> Optional[Item]:
        for item in self.items:
            if item.x == x and item.y == y:
                return item
        return None

    def get_feature_at_location(self, x: int, y: int) -> Optional[Feature]:
        for feature in self.features:
            if feature.x == x and feature.y == y:
                return feature
        return None

    def get_hazard_at_location(self, x: int, y: int) -> Optional[Hazard]:
        for hazard in self.hazards:
            if hazard.x == x and hazard.y == y:
                return hazard
        return None

    def get_target_at_location(self, x: int, y: int) -> Optional[Entity]:
        for entity in self.entities:
            if entity.x == x and entity.y == y:
                if (isinstance(entity, Actor) and entity.is_alive) or isinstance(entity, Feature):
                    return entity
        return None


    def get_blocking_entity_at_location(self, location_x: int, location_y: int) -> Optional[Entity]:
        for entity in self.entities:
            if entity.blocks_movement and entity.x == location_x and entity.y == location_y:
                return entity
        return None

    def get_entities_at_location(self, x: int, y: int) -> Iterator[Item]:
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Entity) and entity.x == x and entity.y == y
        )
    
    def get_items_at_location(self, x: int, y: int) -> Iterator[Item]:
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Item) and entity.x == x and entity.y == y
        )

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if x and y are inside of the bounds of this map."""
        return 0 <= x < self.width and 0 <= y < self.height

    def within_view(self, x: int, y: int, view_width: int =0, view_height: int =0) -> bool:
        """Return True if x and y are inside of the bounds of the view.
        x and y must have been shifted beforehand"""
        if view_width == 0 and view_height == 0:
            view_width = self.engine.renderer.view_width
            view_height = self.engine.renderer.view_height

        return 0 <= x < view_width and 0 <= y < view_height

    # def render(self, renderer: Renderer, view_width: int, view_height: int) -> None:
    def render(self, renderer: Renderer) -> None:
        """Slice this maps contents down to the view size based on camera position"""
        view_width, view_height = renderer.view_width, renderer.view_height
        if view_width//2 == view_width/2 or view_height//2 == view_height/2:
            print("View dimension must be uneven")
            raise

        console = renderer.console

        # Construct slice to be shown (world_slice)
        # If this slice is smaller than the view (border), then provide also the slice for the view 
        # world_slice, view_slice = self.camera.get_view_slice((self.width,self.height),(view_width,view_height))
        world_slice, view_slice = renderer.camera.get_view_slice((self.width,self.height),(view_width,view_height))

        console.rgb[0:view_width, 0:view_height] = self.tiles["dark"][0:view_width, 0:view_height]
        console.rgb[0:view_width, 0:view_height] = tile_types.SHROUD
        
        game_view = np.select(
           condlist=[self.visible, self.explored],
           choicelist=[self.tiles["light"], self.tiles["dark"]],
           default=tile_types.SHROUD,
        )

        console.rgb[view_slice] = game_view[world_slice]

        entities_sorted_for_rendering = sorted(
            self.entities, key=lambda x: x.render_order.value, #reverse=True,
        )

        for entity in entities_sorted_for_rendering:
            if self.visible[entity.x, entity.y]:
                console.print(*renderer.shift(x=entity.x,y=entity.y),
                              entity.char, fg=entity.color)
            else:
                if isinstance(entity, Item) and self.explored[entity.x, entity.y] and self.within_view(*renderer.shift(entity.x, entity.y), view_width,view_height):
                    console.print(*renderer.shift(entity.x, entity.y),
                                  entity.char, fg=entity.color)
        
        for trail in self.trails[:-1]:
            if self.within_view(*renderer.shift(*trail), view_width,view_height):
                console.print(*renderer.shift(*trail), " ", bg=(170,170,170))
            self.trails = []

class GameWorld:
    """
    Holds the settings for the GameMap, and generates new maps when moving down the stairs.
    Also keep tracks of each level
    """

    def __init__(
        self,
        *,
        engine: Engine,
        map_width: int,
        map_height: int,
        max_rooms: int,
        room_min_size: int,
        room_max_size: int,
        seed_init: int,
        current_floor: int = 0,
    ):
        self.engine = engine

        self.map_width = map_width
        self.map_height = map_height

        self.max_rooms = max_rooms

        self.room_min_size = room_min_size
        self.room_max_size = room_max_size

        self.current_floor = current_floor

        self.floors = {}
        self.world_seed: int
        self.floor_seeds = []

        # Seed
        if seed_init == -1:
            self.world_seed = random.getrandbits(32)
        else:
            self.world_seed = seed_init

        random.seed(a = self.world_seed)
        for i in range(100):
            self.floor_seeds.append(random.getrandbits(32))

        random.seed()

    def set_floor(self, depth: int, branch: str = "main") -> None:
        """ initiate engine with the target level"""

        # store current level in its state and player position & remove player from level that he is currently leaving
        if self.engine.turn_count != 0: # except at creation of a new game
            self.floors[(branch,self.current_floor)] = (self.engine.game_map,self.engine.player.x,self.engine.player.y)
            # clean previous status 
            self.engine.player.remove()
            self.engine.game_map.visible[self.engine.game_map.visible == True] = False

        self.current_floor = depth

        if (branch,depth) in list(self.floors):     
            self.engine.game_map, player_x, player_y = self.floors[(branch,depth)]
            self.engine.player.place(player_x, player_y, self.engine.game_map)
        else:
            random.seed(self.floor_seeds.pop())
            new_floor =  self.generate_floor(branch)
            self.engine.game_map = new_floor
            random.seed()

    def generate_floor(self, branch: str = "main") -> GameMap:
        from procgen import generate_dungeon
        
        return generate_dungeon(
            max_rooms=self.max_rooms,
            room_min_size=self.room_min_size,
            room_max_size=self.room_max_size,
            map_width=self.map_width,
            map_height=self.map_height,
            engine=self.engine,
            branch=branch,
            depth=self.current_floor,
        )

