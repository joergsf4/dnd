#include "party.h"

Party party;

static const char *const classNames[3] = { "FIGHTER", "ROGUE", "MAGE" };

typedef struct { u8 hpMax, mpMax; } ClassStats;
static const ClassStats classStats[3] = {
    { 20, 0 },  // CLASS_FIGHTER
    { 16, 0 },  // CLASS_ROGUE
    { 12, 12 }, // CLASS_MAGE
};

const char *class_name(CharClass cls)
{
    return classNames[cls];
}

void party_init(void)
{
    memset(&party, 0, sizeof(party));
}

void party_addMember(CharClass cls)
{
    if (party.count >= PARTY_MAX) return;

    Character *c = &party.members[party.count];
    c->cls = cls;
    c->name = class_name(cls);
    c->hpMax = c->hp = classStats[cls].hpMax;
    c->mpMax = c->mp = classStats[cls].mpMax;
    c->active = TRUE;
    party.count++;
}
