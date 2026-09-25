#ifndef _CHAR_CREATE_H_
#define _CHAR_CREATE_H_

#include "party.h"

// Full-screen class-select loop (uses the whole screen -- runs before the dungeon view/panel
// are set up). Blocks until the player confirms, then returns the chosen class and leaves
// BG_A cleared behind it.
CharClass charCreate_run(void);

#endif
