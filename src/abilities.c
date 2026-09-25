#include "abilities.h"
#include "inventory.h"
#include "textbox.h"
#include "ui_panel.h"
#include "sfx.h"

// Every text line must fit the textbox: at most 27 characters on screen (an umlaut counts as one).

static u8 roll(u8 die)
{
    return (random() % die) + 1;
}

static void say(const char *l0, const char *l1, const char *l2)
{
    const char *lines[3] = { l0, l1, l2 };
    textbox_show(lines, 3, NULL, 0);   // NULL lines are skipped
}

bool ab_isFighter(const Character *c)
{
    return c->cls == CLASS_FIGHTER || c->cls == CLASS_LAEZEL;
}

u8 ab_armorClass(const Character *c)
{
    return (c->buffs & BUFF_MAGE_ARMOR) ? 13 + c->dex : c->ac;
}

Character *ab_pickMember(const char *question)
{
    const char *options[PARTY_MAX];
    u8 who[PARTY_MAX], n = 0;
    for (u8 i = 0; i < PARTY_MAX; i++)
    {
        if (!party.members[i].active) continue;
        who[n] = i;
        options[n++] = party.members[i].name;
    }
    const char *lines[1] = { question };
    return &party.members[who[textbox_show(lines, 1, options, n)]];
}

static u8 heal(Character *t, u8 amount)
{
    sfx_play(SFX_HEAL);
    if (t->hp + amount > t->hpMax) amount = t->hpMax - t->hp;
    t->hp += amount;
    uiPanel_redrawChrome();
    return amount;
}

u8 ab_potion(Character *target)
{
    inventory.healingPotions--;
    return heal(target, roll(4) + roll(4) + 2);
}

u8 ab_layOnHands(Character *paladin, Character *target)
{
    u8 amount = heal(target, paladin->mp);
    paladin->mp -= amount;
    uiPanel_redrawChrome();
    return amount;
}

void ab_mageArmor(Character *mage)
{
    mage->mp--;
    mage->buffs |= BUFF_MAGE_ARMOR;
    sfx_play(SFX_SPELL);
    uiPanel_redrawChrome();
}

// ---------------------------------------------------------------- Göttlicher Sinn

static const char *const directions[8] = {
    "im Norden", "im Nordosten", "im Osten", "im Südosten",
    "im Süden", "im Südwesten", "im Westen", "im Nordwesten",
};

// Compass direction from (dx, dy), y growing southwards.
static u8 direction(s16 dx, s16 dy)
{
    s16 ax = abs(dx), ay = abs(dy);
    if (ay >= 2 * ax) return dy < 0 ? 0 : 4;
    if (ax >= 2 * ay) return dx > 0 ? 2 : 6;
    if (dy < 0) return dx > 0 ? 1 : 7;
    return dx > 0 ? 3 : 5;
}

// Senses fiends in the room -- hidden ones too (the imps in Room 4's pods).
static void divineSense(const Player *p)
{
    u8 count, found = 0;
    s16 best = 0x7FFF, bx = 0, by = 0;
    RoomObject *objects = map_roomObjects(&count);
    for (u8 i = 0; i < count; i++)
    {
        if (objects[i].kind != OBJ_ENEMY_GROUP) continue;
        found++;
        s16 dx = objects[i].x - p->x, dy = objects[i].y - p->y;
        if (abs(dx) + abs(dy) < best)
        {
            best = abs(dx) + abs(dy);
            bx = dx;
            by = dy;
        }
    }

    char l1[32], l2[32];
    const char *l0 = "Göttlicher Sinn:";
    if (!found)
    {
        say(l0, "Nichts Teuflisches in", "der Nähe.");
        return;
    }
    sprintf(l1, "Teufel %s,", directions[direction(bx, by)]);
    sprintf(l2, "%s.", best <= 2 ? "ganz nah" : best <= 5 ? "nicht weit" : "weiter weg");
    say(l0, l1, l2);
}

// ---------------------------------------------------------------- party menu (B)

typedef enum { PM_POTION, PM_MAGE_ARMOR, PM_LAY_ON_HANDS, PM_DIVINE_SENSE, PM_BACK } PartyAction;

void ab_partyMenu(const Player *p)
{
    Character *mage = NULL, *paladin = NULL;
    for (u8 i = 0; i < PARTY_MAX; i++)
    {
        Character *c = &party.members[i];
        if (!c->active || !c->hp) continue;
        if (c->cls == CLASS_MAGE) mage = c;
        if (c->cls == CLASS_SHADOWHEART) paladin = c;
    }

    const char *options[4];
    PartyAction acts[4];
    u8 n = 0;
    if (inventory.healingPotions)                        { options[n] = "Heiltrank";          acts[n++] = PM_POTION; }
    if (mage && mage->mp && !(mage->buffs & BUFF_MAGE_ARMOR)) { options[n] = "Magierrüstung (1 ZP)"; acts[n++] = PM_MAGE_ARMOR; }
    if (paladin && paladin->mp)                          { options[n] = "Heilende Hände";     acts[n++] = PM_LAY_ON_HANDS; }
    if (paladin && n < 4)                                { options[n] = "Göttlicher Sinn";    acts[n++] = PM_DIVINE_SENSE; }
    if (n < 4)                                           { options[n] = "Zurück";             acts[n++] = PM_BACK; }

    const char *lines[1] = { "Gruppe:" };
    char l0[32], l1[32];
    switch (acts[textbox_show(lines, 1, options, n)])
    {
        case PM_POTION:
        {
            Character *t = ab_pickMember("Wer bekommt den Heiltrank?");
            sprintf(l0, "%s erhält %d KP.", t->name, ab_potion(t));
            say("Ein Heiltrank:", l0, NULL);
            break;
        }
        case PM_MAGE_ARMOR:
            ab_mageArmor(mage);
            sprintf(l1, "%s: RK %d.", mage->name, ab_armorClass(mage));
            say("Magierrüstung umhüllt", "dich schimmernd.", l1);
            break;
        case PM_LAY_ON_HANDS:
        {
            Character *t = ab_pickMember("Wen heilen?");
            sprintf(l0, "%s erhält %d KP.", t->name, ab_layOnHands(paladin, t));
            sprintf(l1, "(Noch %d im Pool.)", paladin->mp);
            say("Heilende Hände:", l0, l1);
            break;
        }
        case PM_DIVINE_SENSE: divineSense(p); break;
        default: break;
    }
}

Character *ab_giveEverburn(void)
{
    for (u8 i = 0; i < PARTY_MAX; i++)
    {
        Character *c = &party.members[i];
        if (!c->active || !ab_isFighter(c)) continue;
        c->buffs |= BUFF_EVERBURN;
        if (c->dmgDie < 10) c->dmgDie = 10;
        inventory_giveItem(ITEM_EVERBURN);
        uiPanel_redrawChrome();
        return c;
    }
    return NULL;
}

void ab_gameOver(const char *l0, const char *l1, const char *l2)
{
    music_play(MUSIC_NONE);
    sfx_play(SFX_GAMEOVER);
    const char *lines[3] = { l0, l1, l2 };
    const char *options[1] = { "Neu beginnen" };
    textbox_show(lines, 3, options, 1);
    SYS_hardReset();
}
