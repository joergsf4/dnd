#ifndef _INVENTORY_H_
#define _INVENTORY_H_

#include <genesis.h>

// Party-wide loot, not per-character (matches the vertical slice doc: shared gold/gems/potions,
// no individual hero gear yet). A flat struct is deliberately all this needs right now -- no
// inventory screen or "use item" flow exists yet (see TODO.md); a generic item-id/count table
// would be speculative generality for a one-room milestone. When room 4/5 need identified key
// items (Eldritch Rune, Gold Key), add an ItemId enum + bool hasItem[ITEM_COUNT] alongside this,
// additively.
typedef struct
{
    u16 gold;
    u8 gems;
    u8 healingPotions;
    bool hasBasicGear;
} Inventory;

extern Inventory inventory;

void inventory_init(void);
void inventory_addGold(u16 amount);
void inventory_addGem(u8 amount);
void inventory_addHealingPotion(u8 amount);
void inventory_grantBasicGear(void);

#endif
