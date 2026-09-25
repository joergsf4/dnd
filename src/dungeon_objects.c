#include "dungeon_objects.h"
#include "dungeon_view.h"
#include "textbox.h"
#include "game.h"

#define OBJECT_SPRITE_SIZE 64

static Sprite *objectSprite;

void dungeonObjects_init(void)
{
    PAL_setPalette(PAL2, dungeon_objects_sprite.palette->data, DMA);
}

RoomObject *dungeonObjects_interactTarget(const Player *p)
{
    s16 dx, dy;
    map_forward(p->facing, &dx, &dy);
    return map_objectAt(p->x + dx, p->y + dy);
}

void dungeonObjects_render(const Player *p)
{
    RoomObject *target = dungeonObjects_interactTarget(p);
    ObjectKind kind = target ? target->kind : OBJ_NONE;

    if (kind == OBJ_NONE)
    {
        if (objectSprite) SPR_setVisibility(objectSprite, HIDDEN);
        return;
    }

    s16 ax, ay, aw, ah;
    dungeonView_getObjectAnchor(&ax, &ay, &aw, &ah);
    s16 x = ax + (aw - OBJECT_SPRITE_SIZE) / 2;
    s16 y = ay + (ah - OBJECT_SPRITE_SIZE) / 2;

    if (!objectSprite)
        objectSprite = SPR_addSprite(&dungeon_objects_sprite, x, y, TILE_ATTR(PAL2, TRUE, FALSE, FALSE));
    else
        SPR_setPosition(objectSprite, x, y);

    SPR_setFrame(objectSprite, kind - 1); // frame order matches ObjectKind minus OBJ_NONE
    SPR_setVisibility(objectSprite, VISIBLE);
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
