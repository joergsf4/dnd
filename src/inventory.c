#include "inventory.h"

Inventory inventory;

void inventory_init(void)
{
    memset(&inventory, 0, sizeof(inventory));
}

void inventory_addGold(u16 amount)
{
    inventory.gold += amount;
}

void inventory_addGem(u8 amount)
{
    inventory.gems += amount;
}

void inventory_addHealingPotion(u8 amount)
{
    inventory.healingPotions += amount;
}

void inventory_grantBasicGear(void)
{
    inventory.hasBasicGear = TRUE;
}
