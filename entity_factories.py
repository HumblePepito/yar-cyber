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
    char=")", color=(0, 191, 255), name="Dagger", equippable=equippable.Dagger(), ### ARHHHH, only the () were missing here
)

sword = Item(
    char=")", color=(0, 191, 255), name="Sword", equippable=equippable.Sword()
)

leather_armor = Item(
    char="[", color=(139, 69, 19), name="Leather Armor", equippable=equippable.LeatherArmor(),
)

chain_mail = Item(
    char="[", color=(139, 69, 19), name="Chain Mail", equippable=equippable.ChainMail()
)

sling = Item(
    char=")", color=(200, 69, 50), name="Sling", equippable=equippable.Sling()
)

gun = Item(
    char=")",
    color=color.n_gray,
    name="Gun",
    equippable=equippable.Gun()
)

revolver = Item(
    char=")", color=color.b_yellow, name="Revolver", equippable=equippable.Revolver()
)

rifle = Item(
    char=")", color=color.n_cyan, name="Rifle", equippable=equippable.Rifle()
)

grenade_launcher = Item(
    char=")", color=color.b_orange, name="Grenade Launcher", equippable=equippable.GrenadeLauncher()
)

barrel = Feature(
    char="0", color=color.n_gray, name="Barrel", fightable=Barrel(hp=1),ai_cls=BaseAI,)

toxic_barrel = Feature(
    char="0", color=color.n_green, name="Toxic barrel", fightable=ToxicBarrel(hp=1),ai_cls=BaseAI)

toxic_smoke = Hazard(
    char="§", color=color.n_green, name="Toxic smoke", blocks_view=True, blocks_movement=False,fightable=ToxicSmoke(hp=1,base_attack=2),ai_cls=BaseAI ) # TODO : change attack by damage here and in chokeaction


explosive_barrel = Feature(
    char="0", color=color.n_red, name="Explosive barrel", fightable=components.fightable.ExplosiveBarrel(hp=1, radius=2),ai_cls=BaseAI)

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
    inventory=Inventory(26, [gun,grenade_launcher,]),
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