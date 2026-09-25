#include "dungeon_objects.h"
#include "textbox.h"
#include "party.h"
#include "ui_panel.h"

RoomObject *dungeonObjects_interactTarget(const Player *p)
{
    s16 dx, dy;
    map_forward(p->facing, &dx, &dy);
    return map_objectAt(p->x + dx, p->y + dy);
}

void dungeonObjects_tryDoor(Player *p, RoomObject *obj)
{
    const RoomDef *target = map_findRoom((RoomId) obj->param0);
    if (!target)
    {
        const char *lines[2] = { "Die Sphinktertür zuckt,", "bleibt aber verschlossen." };
        textbox_show(lines, 2, NULL, 0);
        return;
    }
    map_enterRoom(target, p, map_currentRoom()->roomId);
}

void dungeonObjects_useShrine(void)
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
    const char *lines[3] = { "Die Heilblase zieht sich", "zusammen - glitzernde", "Partikel heilen euch." };
    textbox_show(lines, 3, NULL, 0);
}
