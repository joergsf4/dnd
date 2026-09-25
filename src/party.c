#include "party.h"

Party party;

// Names are at most 8 characters (panel and combat texts); Schattenherz is "SCHATTEN" there.
static const char *const classNames[6] = { "KÄMPFER", "SCHURKE", "MAGIER", "WIR", "LAE'ZEL", "SCHATTEN" };

// Placeholder balance, not architecture: str/dex/int are small (1-5) skill-check modifiers
// added to a d20 roll (see skill_check.c), not a full D&D ability score.
// D&D 5e level 1: hit points as hit die + CON, AC and attack bonus as in the rules, damage as
// weapon die + modifier (Lae'zel's greatsword simplified to 1d12). mpMax is the class resource:
// the Magier's two level-1 spell slots, the paladin's Lay-on-Hands pool of 5.
typedef struct { u8 hpMax, mpMax, str, dex, intl, ac, atk, dmgDie, dmgBonus; } ClassStats;
static const ClassStats classStats[6] = {
    { 13, 0,  5, 3, 2, 17, 5, 10, 3 },  // CLASS_FIGHTER: chain mail + shield, style Verteidigung (+1)
    { 10, 0,  3, 5, 3, 14, 5,  6, 3 },  // CLASS_ROGUE: leather, rapier (finesse)
    {  8, 2,  1, 2, 5, 12, 2,  6, 0 },  // CLASS_MAGE: staff; spells use intl as attack bonus
    { 10, 0,  2, 5, 3, 13, 4,  6, 2 },  // CLASS_WIR: light, nimble melee drone (design doc, section 3)
    { 13, 0,  5, 3, 2, 17, 5, 12, 3 },  // CLASS_LAEZEL: fighter, half plate, style Großwaffen
    { 12, 5,  3, 2, 3, 18, 4,  6, 2 },  // CLASS_SHADOWHEART: paladin, chain mail + shield, mace
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
