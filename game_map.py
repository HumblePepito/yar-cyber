from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING
# NamedTuple : https://stackoverflow.com/questions/2970608/what-are-named-tuples-in-python#2970722
import numpy as np  # type: ignore
from entity import Actor, Entity, Feature, Hazard, Item
from fire_line import FireLine

import tile_types

if TYPE_CHECKING:
    from engine import Engine
    from renderer import Renderer 

        
class GameMap:
    def __init__(self, engine: Engine, width: int, height: int, entities: Iterable[Entity] = ()):
        self.engine = engine
        self.width, self.height = width, height
        self.entities = set(entities)

        self.tiles = np.full((width, height), fill_value=tile_types.wall, order="F")
        self.visible = np.full((width, height), fill_value=False, order="F") # Tiles the player can currently see
        self.explored = np.full((width, height), fill_value=False, order="F") # Tiles the player has seen before

        self.upstairs_location =(0,0)
        self.downstairs_location =(0,0)

        self.player_lof = FireLine(game_map=self)
        self.hostile_lof = FireLine(game_map=self)
        self.wall: Entity = None

    
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

    def get_fire_line(self, shooter: Actor) -> FireLine:
        if shooter == self.engine.player:
            return self.player_lof
        return self.hostile_lof

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if x and y are inside of the bounds of this map."""
        return 0 <= x < self.width and 0 <= y < self.height

    def within_view(self, x: int, y: int, view_width: int, view_height: int) -> bool:
        """Return True if x and y are inside of the bounds of the view.
        x and y must have been shifted beforehand"""
        return 0 <= x < view_width and 0 <= y < view_height

    # def render(self, renderer: Renderer, view_width: int, view_height: int) -> None:
    def render(self, renderer: Renderer) -> None:
        """Slice this maps contents down to the view size based on camera position"""
        view_width, view_height = renderer.view_width, renderer.view_height
        if view_width//2 == view_width/2 or view_height//2 == view_height/2:
            # dimension must be uneven
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

class GameWorld:
    """
    Holds the settings for the GameMap, and generates new maps when moving down the stairs.
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
        current_floor: int = 0
    ):
        self.engine = engine

        self.map_width = map_width
        self.map_height = map_height

        self.max_rooms = max_rooms

        self.room_min_size = room_min_size
        self.room_max_size = room_max_size

        self.current_floor = current_floor

    def generate_floor(self) -> None:
        from procgen import generate_dungeon

        self.current_floor += 1

        self.engine.game_map = generate_dungeon(
            max_rooms=self.max_rooms,
            room_min_size=self.room_min_size,
            room_max_size=self.room_max_size,
            map_width=self.map_width,
            map_height=self.map_height,
            engine=self.engine,
        )

