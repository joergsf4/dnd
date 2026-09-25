#include "room1.h"
#include "textbox.h"
#include "skill_check.h"
#include "inventory.h"
#include "party.h"
#include "ui_panel.h"
#include "dungeon_objects.h"

static void onLarvaTank(Player *p, RoomObject *obj)
{
    (void) p;
    const char *lines[2] = { "A tank of writhing larvae.", "The seal looks brittle." };
    const char *options[3] = { "REACH IN", "INVESTIGATE [INT]", "LEAVE" };
    u8 choice = textbox_show(lines, 2, options, 3);

    if (choice == 0)
    {
        Character *hero = &party.members[0];
        hero->hp = (hero->hp > 3) ? (hero->hp - 3) : 0;
        uiPanel_drawStatus(p);
        const char *result[1] = { "BOOM! -3 HP damage." };
        textbox_show(result, 1, NULL, 0);
    }
    else if (choice == 1)
    {
        bool success = skillCheck_run(&party.members[0], ATTR_INT, 12);
        obj->flags |= OBJFLAG_TRIGGERED;
        const char *result[1] = { success ? "Danger recognized." : "You find nothing certain." };
        textbox_show(result, 1, NULL, 0);
    }
    else
    {
        const char *result[1] = { "You step back." };
        textbox_show(result, 1, NULL, 0);
    }
}

static void onCorpse(Player *p, RoomObject *obj)
{
    (void) p;
    if (obj->flags & OBJFLAG_TRIGGERED)
    {
        const char *lines[1] = { "Already searched." };
        textbox_show(lines, 1, NULL, 0);
        return;
    }
    obj->flags |= OBJFLAG_TRIGGERED;
    inventory_addGold(15);
    inventory_addGem(1);
    uiPanel_drawInventory();
    const char *lines[2] = { "The corpse of a mindflayer.", "Found: 15 gold, a gem." };
    textbox_show(lines, 2, NULL, 0);
}

static void onChest(Player *p, RoomObject *obj)
{
    (void) p;
    if (obj->flags & OBJFLAG_TRIGGERED)
    {
        const char *lines[1] = { "The chest is empty." };
        textbox_show(lines, 1, NULL, 0);
        return;
    }
    obj->flags |= OBJFLAG_TRIGGERED;
    inventory_grantBasicGear();
    inventory_addHealingPotion(1);
    uiPanel_drawInventory();
    const char *lines[2] = { "A cartilage chest.", "Found: basic gear, a potion." };
    textbox_show(lines, 2, NULL, 0);
}

static void onShrine(Player *p, RoomObject *obj)
{
    (void) p;
    (void) obj;
    for (u8 i = 0; i < PARTY_MAX; i++)
    {
        if (party.members[i].active)
        {
            party.members[i].hp = party.members[i].hpMax;
            party.members[i].mp = party.members[i].mpMax;
        }
    }
    uiPanel_redrawChrome();
    const char *lines[2] = { "Warm light washes over you.", "Fully restored." };
    textbox_show(lines, 2, NULL, 0);
}

static void room1_onInteract(Player *p, RoomObject *obj)
{
    switch (obj->kind)
    {
        case OBJ_LARVA_TANK:         onLarvaTank(p, obj); break;
        case OBJ_MINDFLAYER_CORPSE:  onCorpse(p, obj); break;
        case OBJ_CARTILAGE_CHEST:    onChest(p, obj); break;
        case OBJ_RESTORATION_SHRINE: onShrine(p, obj); break;
        case OBJ_DOOR_EXIT:          dungeonObjects_tryDoor(p, obj); break;
        default: break;
    }
}

static const char *const room1Grid[6] = {
    "11111111",
    "10000001",
    "10000001",
    "10000001",
    "10000001",
    "11111111",
};

static const RoomObject room1Objects[] = {
    { 3, 1, OBJ_LARVA_TANK,         0,      0, 0 }, // north wall, directly ahead of spawn
    { 7, 2, OBJ_RESTORATION_SHRINE, 0,      0, 0 }, // east wall
    { 4, 4, OBJ_CARTILAGE_CHEST,    0,      0, 0 }, // south wall
    { 0, 2, OBJ_MINDFLAYER_CORPSE,  0,      0, 0 }, // west wall
    { 0, 3, OBJ_DOOR_EXIT,          ROOM_2, 0, 0 }, // west wall; ROOM_2 isn't built yet
};

const RoomDef ROOM1 = {
    .roomId = ROOM_1,
    .w = 8, .h = 6,
    .grid = room1Grid,
    .startX = 3, .startY = 2, .startFacing = FACE_NORTH,
    .objectCount = 5,
    .objects = room1Objects,
    .onInteract = room1_onInteract,
    .onEnter = NULL,
};
