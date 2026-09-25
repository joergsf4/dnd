#include "party.h"

Party party;

static const char *const classNames[5] = { "KÄMPFER", "SCHURKE", "MAGIER", "WIR", "LAE'ZEL" };

// Placeholder balance, not architecture: str/dex/int are small (1-5) skill-check modifiers
// added to a d20 roll (see skill_check.c), not a full D&D ability score.
// Combat values follow D&D 5e at level 1 loosely: ac/atk as in the rules, damage as weapon die +
// modifier (greatsword for Lae'zel is simplified to 1d12).
typedef struct { u8 hpMax, mpMax, str, dex, intl, ac, atk, dmgDie, dmgBonus; } ClassStats;
static const ClassStats classStats[5] = {
    { 20, 0,  5, 3, 2, 16, 5, 10, 3 },  // CLASS_FIGHTER
    { 16, 0,  3, 5, 3, 14, 5,  6, 3 },  // CLASS_ROGUE
    { 12, 12, 1, 2, 5, 12, 2,  6, 0 },  // CLASS_MAGE: weak with the staff, casts Geschoss instead
    { 10, 0,  2, 5, 3, 13, 4,  6, 2 },  // CLASS_WIR: light, nimble melee drone (design doc, section 3)
    { 22, 0,  5, 3, 2, 17, 5, 12, 3 },  // CLASS_LAEZEL: sturdy two-handed fighter
};

const char *class_name(CharClass cls)
{
    return classNames[cls];
}

void party_init(void)
{
    memset(&party, 0, sizeof(party));
}

Character *party_addMember(CharClass cls)
{
    if (party.count >= PARTY_MAX) return NULL;

    Character *c = &party.members[party.count];
    c->cls = cls;
    c->name = class_name(cls);
    c->hpMax = c->hp = classStats[cls].hpMax;
    c->mpMax = c->mp = classStats[cls].mpMax;
    c->str = classStats[cls].str;
    c->dex = classStats[cls].dex;
    c->intl = classStats[cls].intl;
    c->ac = classStats[cls].ac;
    c->atk = classStats[cls].atk;
    c->dmgDie = classStats[cls].dmgDie;
    c->dmgBonus = classStats[cls].dmgBonus;
    c->active = TRUE;
    party.count++;
    return c;
}
