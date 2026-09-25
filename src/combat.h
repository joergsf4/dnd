#ifndef _COMBAT_H_
#define _COMBAT_H_

#include <genesis.h>
#include "dungeon_map.h"

// Turn-based menu combat in the first-person view, in the vein of Shining in the Darkness: the
// enemies stand in front of the party as figures (src/figures.c), everyone acts in initiative
// order, the player picks every party member's action from a menu in the message area.

#define COMBAT_MAX_ENEMIES 3

typedef struct
{
    const char *name;                 // at most 6 characters: a letter is appended ("KOBOLD A")
    u8 hpMax, ac, atk, dmgDie, dmgBonus;
    const SpriteDefinition *sprite;
    s16 bottom;                       // screen y of the figure's feet (hovering ones are higher)
} EnemyDef;

extern const EnemyDef ENEMY_IMP;

// Fights `count` enemies (up to COMBAT_MAX_ENEMIES). `tank`, if not NULL, is an acid tank within
// reach: it's offered as a target and, once hit, bursts and hurts every enemy (the design doc's
// explosive Nautiloid tanks). Blocking; returns only when the party has won -- on defeat it shows
// the game-over screen and restarts the game.
// `p` is only needed to redraw the view (a bursting tank).
void combat_run(const Player *p, const EnemyDef *const enemies[], u8 count, RoomObject *tank, u8 goldReward);

#endif
