from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from components.base_component import BaseComponent
from various_enum import EquipmentSlot
from input_handlers import EventHandler

if TYPE_CHECKING:
    from engine import Engine
    from entity import Actor, Item
    from components.equippable import Equippable,RangedWeapon,Sling


class Equipment(BaseComponent):
    """Your current equipment, determined by various_enum.EquipmentSlot"""
    parent: Actor

    def __init__(self, weapon: Optional[Item] = None, armor_suit: Optional[Item] = None):
        self.weapon = weapon
        self.armor_suit = armor_suit

    @property
    def defense_bonus(self) -> int:
        bonus = 0

        # if self.weapon is not None and self.weapon.equippable is not None:
        #     bonus += self.weapon.equippable.defense_bonus

        # if self.armor_suit is not None and self.armor_suit.equippable is not None:
        #     bonus += self.armor_suit.equippable.defense_bonus

        return bonus
    @property

    def armor_bonus(self) -> int:
        bonus = 0

        if self.weapon is not None and self.weapon.equippable is not None:
            bonus += self.weapon.equippable.armor_bonus

        if self.armor_suit is not None and self.armor_suit.equippable is not None:
            bonus += self.armor_suit.equippable.armor_bonus

        return bonus

    @property
    def attack_bonus(self) -> int:
        bonus = 0

        if self.weapon is not None and self.weapon.equippable is not None:
            bonus += self.weapon.equippable.attack_bonus

        if self.armor_suit is not None and self.armor_suit.equippable is not None:
            bonus += self.armor_suit.equippable.attack_bonus

        return bonus

    def item_is_equipped(self, item: Item) -> bool:
        return self.weapon == item or self.armor_suit == item

    def unequip_message(self, item_name: str) -> None:
        if self.parent == self.engine.player:
            msg = f"You remove the {item_name}."
        else:
            msg = f"The {self.parent.name} removes the {item_name}."

        self.parent.gamemap.engine.message_log.add_message(msg)


    def equip_message(self, item_name: str) -> None:
        if self.parent == self.engine.player:
            msg = f"You equip the {item_name}."
        else:
            msg = f"The {self.parent.name} equips the {item_name}."

        self.parent.gamemap.engine.message_log.add_message(msg)


    def equip_to_slot(self, slot: str, item: Item, add_message: bool) -> None:
        current_item = getattr(self, slot)

        if current_item is not None:
            self.unequip_from_slot(slot, add_message)

        setattr(self, slot, item)

        if add_message:
            self.equip_message(item.name)

    def unequip_from_slot(self, slot: str, add_message: bool) -> None:
        current_item = getattr(self, slot)

        if add_message:
            self.unequip_message(current_item.name)

        setattr(self, slot, None)

    def toggle_equip(self, equippable_item: Item, add_message: bool = True) -> None:
        if (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentSlot.WEAPON
        ):
            slot = "weapon"
        else:
            slot = "armor_suit"

        if getattr(self, slot) == equippable_item:
            self.unequip_from_slot(slot, add_message)
        else:
            self.equip_to_slot(slot, equippable_item, add_message)

    def fire_event(self) -> EventHandler:
        """ Whenever a shoot occurs, use the weapon to determine which handler to use"""
        shooter = self.parent
        ranged_weapon: RangedWeapon = self.weapon.equippable

        try:
            # purge combat stats TODO : is the good place??
            self.parent.gamemap.fire_line.combat_stat = {}
            
            return ranged_weapon.get_fire_action(shooter)
        except AttributeError:
            self.parent.gamemap.engine.message_log.add_message("You must wield a working ranged weapon.")
        