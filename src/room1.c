#include "room1.h"
#include "textbox.h"
#include "skill_check.h"
#include "inventory.h"
#include "party.h"
#include "ui_panel.h"
#include "dungeon_objects.h"

// Every text line must fit the textbox: at most 27 characters on screen (an umlaut counts as one).

static void say(const char *l0, const char *l1, const char *l2)
{
    const char *lines[3] = { l0, l1, l2 };
    textbox_show(lines, l2 ? 3 : l1 ? 2 : 1, NULL, 0);
}

static void onEnter(Player *p)
{
    static bool introShown;
    (void) p;
    if (introShown) return;
    introShown = TRUE;
    say("Du erwachst in einer", "Kapsel voller Schleim.", "Hinter den Augen brennt es.");
    say("Die Kapsel hinter dir steht", "offen. Wo bist du?", "(A: Dinge untersuchen)");
}

static void onLarvaPool(RoomObject *obj)
{
    if (obj->flags & OBJFLAG_BROKEN)
    {
        say("Das Becken ist geplatzt.", "Nur noch Säure und", "tote Kaulquappen.");
        return;
    }

    // Once the danger is recognised, the pool is marked and investigating again is pointless.
    bool marked = obj->flags & OBJFLAG_MARKED;
    const char *fresh[3] = { "Ein Becken voller zuckender", "Kaulquappen. Die Hülle", "scheint brüchig." };
    const char *known[2] = { "Das Becken ist markiert:", "Die Hülle ist instabil." };
    const char *freshOpts[3] = { "Hineinfassen", "Untersuchen [INT]", "Weggehen" };
    const char *knownOpts[2] = { "Hineinfassen", "Weggehen" };

    u8 choice = marked ? textbox_show(known, 2, knownOpts, 2) : textbox_show(fresh, 3, freshOpts, 3);
    if (marked && choice == 1) choice = 2;   // map onto the fresh menu's numbering

    if (choice == 0)
    {
        Character *hero = &party.members[0];
        hero->hp = (hero->hp > 4) ? (hero->hp - 3) : 1;   // no death yet: never below 1 KP
        obj->flags |= OBJFLAG_BROKEN;
        uiPanel_redrawChrome();
        say("BOOM! Das Becken platzt,", "Säure spritzt dich an.", "-3 KP Schaden.");
    }
    else if (choice == 1)
    {
        if (skillCheck_run(&party.members[0], ATTR_INT, 12))
        {
            obj->flags |= OBJFLAG_MARKED;
            say("Gefahr erkannt: Die Hülle", "ist instabil und würde", "bei Berührung platzen.");
        }
        else
            say("Du erkennst nichts", "Besonderes.", NULL);
    }
    // choice 2, "Weggehen": nothing happens
}

static void onCorpse(RoomObject *obj)
{
    if (obj->flags & OBJFLAG_TRIGGERED)
    {
        say("Der Gedankenschinder ist", "bereits durchsucht.", NULL);
        return;
    }
    obj->flags |= OBJFLAG_TRIGGERED;
    inventory_addGold(15);
    inventory_addGem(1);
    uiPanel_drawInventory();
    say("Ein toter Gedankenschinder.", "In seiner Robe: 15 Gold", "und ein Edelstein.");
}

static void onChest(RoomObject *obj)
{
    if (obj->flags & OBJFLAG_TRIGGERED)
    {
        say("Die Knorpelkiste ist leer.", NULL, NULL);
        return;
    }
    obj->flags |= OBJFLAG_TRIGGERED;
    inventory_grantBasicGear();
    inventory_addHealingPotion(1);
    uiPanel_drawInventory();
    say("Eine Knorpelkiste. Darin:", "Grundausrüstung und", "ein Heiltrank.");
}

static void onShrine(void)
{
    for (u8 i = 0; i < PARTY_MAX; i++)
    {
        if (party.members[i].active)
        {
            party.members[i].hp = party.members[i].hpMax;
            party.members[i].mp = party.members[i].mpMax;
        }
    }
    uiPanel_redrawChrome();
    say("Die Heilblase zieht sich", "zusammen - glitzernde", "Partikel heilen dich.");
}

static void room1_onInteract(Player *p, RoomObject *obj)
{
    switch (obj->kind)
    {
        case OBJ_LARVA_TANK:         onLarvaPool(obj); break;
        case OBJ_MINDFLAYER_CORPSE:  onCorpse(obj); break;
        case OBJ_CARTILAGE_CHEST:    onChest(obj); break;
        case OBJ_RESTORATION_SHRINE: onShrine(); break;
        case OBJ_POD_OPEN:
            say("Deine Kapsel. Glibbrige", "Reste kleben noch am Glas.", "Hier kamst du heraus.");
            break;
        case OBJ_POD_BROKEN:
            say("Eine zerbrochene", "Klonkapsel. Scherben und", "kalter Schleim. Leer.");
            break;
        case OBJ_DOOR_EXIT:          dungeonObjects_tryDoor(p, obj); break;
        default: break;
    }
}

// Klonkammer, 6x5 inside. The open pod the player woke up in stands free in the middle (3,3);
// the player starts right in front of it, facing away from it.
//
//      x 0 1 2 3 4 5 6 7
//  y 0   1 1 P 1 P 1 C 1     P broken pod   C chest
//    1   D 0 0 0 0 0 0 1     D sphincter door (north-west exit)
//    2   1 0 0 0 0 0 0 1
//    3   1 0 0 O 0 0 0 S     O open pod     S restoration station
//    4   P 0 0 @ 0 0 0 1     @ start, facing south
//    5   1 0 0 0 0 0 0 G     G mind flayer corpse
//    6   1 1 1 L 1 P 1 1     L larva pool
static const char *const room1Grid[7] = {
    "11111111",
    "10000001",
    "10000001",
    "10010001",
    "10000001",
    "10000001",
    "11111111",
};

// Objects must sit ON a wall cell ('1' in room1Grid): dungeon_view.c draws an object as that
// wall's texture, so an object on an open floor cell would be interactable but invisible.
static const RoomObject room1Objects[] = {
    { 3, 3, OBJ_POD_OPEN,           0,      0, 0 },
    { 3, 6, OBJ_LARVA_TANK,         0,      0, 0 },
    { 2, 0, OBJ_POD_BROKEN,         0,      0, 0 },
    { 4, 0, OBJ_POD_BROKEN,         0,      0, 0 },
    { 5, 6, OBJ_POD_BROKEN,         0,      0, 0 },
    { 0, 4, OBJ_POD_BROKEN,         0,      0, 0 },
    { 6, 0, OBJ_CARTILAGE_CHEST,    0,      0, 0 },
    { 7, 3, OBJ_RESTORATION_SHRINE, 0,      0, 0 },
    { 7, 5, OBJ_MINDFLAYER_CORPSE,  0,      0, 0 },
    { 0, 1, OBJ_DOOR_EXIT,          ROOM_2, 0, 0 }, // ROOM_2 isn't built yet
};

const RoomDef ROOM1 = {
    .roomId = ROOM_1,
    .w = 8, .h = 7,
    .grid = room1Grid,
    .startX = 3, .startY = 4, .startFacing = FACE_SOUTH,
    .objectCount = sizeof(room1Objects) / sizeof(room1Objects[0]),
    .objects = room1Objects,
    .onInteract = room1_onInteract,
    .onEnter = onEnter,
};
