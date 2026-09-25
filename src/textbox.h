#ifndef _TEXTBOX_H_
#define _TEXTBOX_H_

#include <genesis.h>

// A modal textbox over the lower BG_A rows, full 40-column width. This is a deliberate exception
// to dungeon_view.c's "nothing left of column 28" rule: that rule is about continuous gameplay
// rendering (BG_A composites in front of BG_B, so it would cut into the view), whereas a textbox
// pauses the world and draws over it on purpose. The dungeon view itself (BG_B) is untouched
// underneath and simply shows through again once the box is cleared.
#define TEXTBOX_ROW 19
#define TEXTBOX_H   9
#define TEXTBOX_BODY_LINES 3    // rows TEXTBOX_ROW+1 .. TEXTBOX_ROW+3
#define TEXTBOX_MAX_OPTIONS 4   // rows TEXTBOX_ROW+5 .. TEXTBOX_ROW+8

// Shows up to TEXTBOX_BODY_LINES lines of text, then either:
//   - optionCount == 0: a "PRESS A" prompt; blocks until A is pressed, returns 0.
//   - optionCount > 0 (up to TEXTBOX_MAX_OPTIONS): a cursor menu (D-pad + A); blocks until
//     confirmed, returns the chosen option's index.
// Clears the box (back to blank, letting BG_B show through) before returning either way.
u8 textbox_show(const char *const lines[], u8 lineCount,
                 const char *const options[], u8 optionCount);

#endif
