#ifndef _INVENTORY_H_
#define _INVENTORY_H_

#include <genesis.h>

// Party-wide loot, not per-character (matches the vertical slice doc: shared gold/gems/potions,
// no individual hero gear yet): counts for the stackable things, a flag per key item.
typedef enum
{
    ITEM_RUNE = 0,      // Eldritch-Rune (Room 5): opens Schattenherz's pod in Room 4
    ITEM_GOLD_KEY,      // verzierter Schlüssel (Room 5): opens the ornate chest there
    ITEM_SCROLL,        // Schriftrolle (Room 5's chest): Brennende Hände, once, in combat
    ITEM_EVERBURN,      // Immerbrand-Klinge (Zhalk, Room 6): wielded by the party's fighter
    ITEM_COUNT
} ItemId;

typedef struct
{
    u16 gold;
    u8 gems;
    u8 healingPotions;
    bool hasBasicGear;
    bool items[ITEM_COUNT];
} Inventory;

extern Inventory inventory;

void inventory_init(void);
void inventory_addGold(u16 amount);
void inventory_addGem(u8 amount);
void inventory_addHealingPotion(u8 amount);
void inventory_grantBasicGear(void);
void inventory_giveItem(ItemId item);
void inventory_takeItem(ItemId item);
bool inventory_hasItem(ItemId item);
const char *inventory_itemName(ItemId item);   // for the panel, at most 12 characters

#define INVENTORY_ITEM_ROWS 3   // panel rows for key items (18-20); at most 3 are ever carried

#endif
