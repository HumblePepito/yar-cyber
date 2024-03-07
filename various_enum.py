from enum import auto, Enum

# Only class variables

class EquipmentSlot(Enum):
    WEAPON = auto()
    ARMOR = auto()

class ItemType(Enum):
    ITEM = auto()
    MELEE_WEAPON = auto()
    RANGED_WEAPON = auto()
    ARMOR_SUIT = auto()
    POTION = auto()
    DRUG = auto()
    GOLD = auto()
    SCROLL = auto()
    GRENADE = auto()

class SizeClass(Enum):
    TINY = auto()
    SMALL = auto()
    MEDIUM = auto()
    BIG = auto()
    HUGE = auto()
    WALL = auto()

class RenderOrder(Enum):
    CORPSE = auto()
    ITEM = auto()
    CLOUD = auto()
    ACTOR = auto()

class EffectType(Enum):
    CONFUSION = auto()
    SPEED = auto()


# class PickupType(Enum):
#     POTION = ItemType.POTION.value
#     SCROLL = ItemType.SCROLL.value 
