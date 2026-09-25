#include "inventory.h"
#include "sfx.h"

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
    sfx_play(SFX_ITEM);
    inventory.gems += amount;
}

void inventory_addHealingPotion(u8 amount)
{
    sfx_play(SFX_ITEM);
    inventory.healingPotions += amount;
}

void inventory_grantBasicGear(void)
{
    inventory.hasBasicGear = TRUE;
}

static const char *const itemNames[ITEM_COUNT] = { "RUNE", "SCHLÜSSEL", "SCHRIFTROLLE", "IMMERBRAND" };

void inventory_giveItem(ItemId item)
{
    sfx_play(SFX_ITEM);
    inventory.items[item] = TRUE;
}

void inventory_takeItem(ItemId item)
{
    inventory.items[item] = FALSE;
}

bool inventory_hasItem(ItemId item)
{
    return inventory.items[item];
}

const char *inventory_itemName(ItemId item)
{
    return itemNames[item];
}
