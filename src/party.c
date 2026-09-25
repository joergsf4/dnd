#include "party.h"

Party party;

static const char *const classNames[3] = { "KÄMPFER", "SCHURKE", "MAGIER" };

// Placeholder balance, not architecture: str/dex/int are small (1-5) skill-check modifiers
// added to a d20 roll (see skill_check.c), not a full D&D ability score.
typedef struct { u8 hpMax, mpMax, str, dex, intl; } ClassStats;
static const ClassStats classStats[3] = {
    { 20, 0,  5, 3, 2 },  // CLASS_FIGHTER
    { 16, 0,  3, 5, 3 },  // CLASS_ROGUE
    { 12, 12, 1, 2, 5 },  // CLASS_MAGE
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
    c->str = classStats[cls].str;
    c->dex = classStats[cls].dex;
    c->intl = classStats[cls].intl;
    c->active = TRUE;
    party.count++;
}
