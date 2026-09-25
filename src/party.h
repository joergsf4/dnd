#ifndef _PARTY_H_
#define _PARTY_H_

#include <genesis.h>

#define PARTY_MAX 4

typedef enum
{
    CLASS_FIGHTER = 0,
    CLASS_ROGUE = 1,
    CLASS_MAGE = 2,
    CLASS_WIR = 3,      // "Wir", the intellect devourer companion from Room 2 (not selectable)
    CLASS_LAEZEL = 4    // Lae'zel, githyanki warrior, joins in Room 3 (not selectable)
} CharClass;

typedef struct
{
    CharClass cls;
    const char *name;   // auto-assigned: just the class name (see TODO.md for real name entry)
    u8 hp, hpMax;
    u8 mp, mpMax;       // 0/0 for classes without mana
    u8 str, dex, intl;  // minimal attribute block for skill_check.c; WIS/CON/CHA not modeled yet
    u8 ac;              // combat (src/combat.c): armour class an attack roll has to reach...
    u8 atk;             // ...d20 + atk...
    u8 dmgDie, dmgBonus; // ...and on a hit 1d(dmgDie) + dmgBonus damage
    bool active;        // FALSE = empty slot, not yet recruited
} Character;

typedef struct
{
    Character members[PARTY_MAX];
    u8 count;
} Party;

extern Party party;

const char *class_name(CharClass cls);

// Clears the party to all-empty slots.
void party_init(void);

// Appends a new character of the given class with that class's default stats.
// Returns it, or NULL if the party is already full.
Character *party_addMember(CharClass cls);

#endif
