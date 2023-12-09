import color

from components.ai import BaseAI,HostileEnemy
from components.fightable import Fighter, Barrel, ToxicBarrel, ToxicSmoke
import components.fightable

from components import consumable, equippable, activable
from components.equipment import Equipment
from components.inventory import Inventory
from components.level import Level
from entity import Actor, Entity, Feature, Hazard, Item 
from various_enum import ItemType, RenderOrder, SizeClass

wall = Entity(
    char="#", color=(170, 85, 0), name="Wall", blocks_movement=True, size=SizeClass.WALL,
)

healingPotion = Item(
    char="!", color=color.n_purple, name="Healing potion", item_type=ItemType.POTION, consumable=consumable.HealingConsumable(amount=5),
)
lightningScroll = Item(
    char="?", color=(127, 127, 255), name="Scroll of lightning", item_type=ItemType.SCROLL, consumable=consumable.LightningDamageConsumable(damage=18),
)
confusionScroll = Item(
    char="?", color=(207, 63, 255), name="Confusion Scroll", item_type=ItemType.SCROLL, consumable=consumable.ConfusionConsumable(number_of_turns=10),
)

fireballScroll = Item(
    char="?", color=(255, 63, 0), name="Fireball Scroll", item_type=ItemType.SCROLL, consumable=consumable.FireballConsumable(radius=1,damage=18),
)

dagger = Item(
    char=")", color=(0, 191, 255), name="Dagger", equippable=equippable.Dagger(), item_type= ItemType.MELEE_WEAPON,
)

sword = Item(
    char=")", color=(0, 191, 255), name="Sword", equippable=equippable.Sword(), item_type= ItemType.MELEE_WEAPON,
)

leather_armor = Item(
    char="[", color=(139, 69, 19), name="Leather Armor", equippable=equippable.LeatherArmor(), item_type= ItemType.ARMOR_SUIT
)

chain_mail = Item(
    char="[", color=(139, 69, 19), name="Chain Mail", equippable=equippable.ChainMail(), item_type= ItemType.ARMOR_SUIT
)

sling = Item(
    char=")", color=(200, 69, 50), name="Sling", equippable=equippable.Sling(), item_type= ItemType.RANGED_WEAPON,
)

gun = Item(
    char=")",
    color=color.n_gray,
    name="Gun",
    equippable=equippable.Gun(),
    item_type= ItemType.RANGED_WEAPON,
)

revolver = Item(
    char=")", color=color.b_yellow, name="Revolver", equippable=equippable.Revolver(), item_type= ItemType.RANGED_WEAPON,
)

rifle = Item(
    char=")", color=color.n_cyan, name="Rifle", equippable=equippable.Rifle(), item_type= ItemType.RANGED_WEAPON
)

grenade_launcher = Item(
    char=")", color=color.b_orange, name="Grenade Launcher", equippable=equippable.GrenadeLauncher(), item_type= ItemType.RANGED_WEAPON
)

barrel = Feature(
    char="0", color=color.n_gray, name="Barrel", fightable=Barrel(hp=1))

toxic_barrel = Feature(
    char="0", color=color.n_green, name="Toxic barrel", fightable=ToxicBarrel(hp=1))

toxic_smoke = Hazard(
    char="§", color=color.n_green, name="Toxic smoke", blocks_view=True, blocks_movement=False,fightable=ToxicSmoke(hp=1,base_attack=2),ai_cls=BaseAI ) # TODO : change attack by damage here and in chokeaction


explosive_barrel = Feature(
    char="0", color=color.n_red, name="Explosive barrel", fightable=components.fightable.ExplosiveBarrel(hp=1, radius=2))

fire_cloud = Hazard(
    char="§",
    color=color.b_orange,
    name="Bright Fire",
    blocks_view=True,
    blocks_movement=False,
    fightable=components.fightable.FireCloud(hp=1,base_attack=4),
    ai_cls=BaseAI,
    render_order= RenderOrder.CLOUD )

player = Actor(
    char="@",
    color=color.b_white,
    name="Player",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fightable=Fighter(hp=30, base_defense=4, base_attack=8, base_armor=2),
    inventory=Inventory(26, [gun,grenade_launcher,chain_mail,]),
    level=Level(level_up_base=200),
)
orc = Actor(
    char="o",
    color=color.b_orange,
    name="Orc",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fightable=Fighter(hp=10, base_defense=2, base_attack=6),
    inventory=Inventory(26, [None, gun, dagger, revolver,]),
    level=Level(xp_given=35),
)
troll = Actor(
    char="T",
    color=color.n_green,
    name="Troll",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fightable=Fighter(hp=16, base_defense=2, base_attack=6, base_armor =6),
    inventory=Inventory(26,[revolver, grenade_launcher, sword, leather_armor, chain_mail]),
    level=Level(xp_given=100),
    size=SizeClass.BIG
)