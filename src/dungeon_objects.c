#include "dungeon_objects.h"
#include "textbox.h"

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
        const char *lines[2] = { "The passage beyond", "is still sealed..." };
        textbox_show(lines, 2, NULL, 0);
        return;
    }
    map_loadRoom(target, p);
}
