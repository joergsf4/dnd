#include "textbox.h"

static void clearBox(void)
{
    char blank[41];
    memset(blank, ' ', 40);
    blank[40] = 0;
    for (u8 r = 0; r < TEXTBOX_H; r++)
        VDP_drawText(blank, 0, TEXTBOX_ROW + r);
}

static void drawLines(const char *const lines[], u8 lineCount)
{
    if (lineCount > TEXTBOX_BODY_LINES) lineCount = TEXTBOX_BODY_LINES;
    for (u8 i = 0; i < lineCount; i++)
        VDP_drawText(lines[i], 1, TEXTBOX_ROW + 1 + i);
}

static void drawOptions(const char *const options[], u8 optionCount, u8 cursor)
{
    char buf[40];
    for (u8 i = 0; i < optionCount; i++)
    {
        sprintf(buf, "%s %s", i == cursor ? ">" : " ", options[i]);
        VDP_drawText(buf, 2, TEXTBOX_ROW + 5 + i);
    }
}

u8 textbox_show(const char *const lines[], u8 lineCount,
                 const char *const options[], u8 optionCount)
{
    clearBox();
    drawLines(lines, lineCount);

    // Seed with the CURRENT joypad state, not 0: this is invoked mid-gameplay in direct response
    // to a button press (e.g. A to interact), so the physical button may still be held down on
    // entry. Seeding with 0 would make that held button register as a fresh "pressed" edge on
    // the very first iteration below and instantly select/confirm before the player releases it.
    u16 prevJoy = JOY_readJoypad(JOY_1);

    if (optionCount == 0)
    {
        VDP_drawText("PRESS A", 2, TEXTBOX_ROW + TEXTBOX_H - 1);
        while (TRUE)
        {
            u16 joy = JOY_readJoypad(JOY_1);
            u16 pressed = joy & ~prevJoy;
            if (pressed & BUTTON_A) break;
            prevJoy = joy;
            SPR_update();
            SYS_doVBlankProcess();
        }
        clearBox();
        return 0;
    }

    if (optionCount > TEXTBOX_MAX_OPTIONS) optionCount = TEXTBOX_MAX_OPTIONS;
    u8 cursor = 0;
    drawOptions(options, optionCount, cursor);

    while (TRUE)
    {
        u16 joy = JOY_readJoypad(JOY_1);
        u16 pressed = joy & ~prevJoy;

        if (pressed & BUTTON_UP) cursor = (cursor + optionCount - 1) % optionCount;
        if (pressed & BUTTON_DOWN) cursor = (cursor + 1) % optionCount;
        if (pressed & (BUTTON_UP | BUTTON_DOWN)) drawOptions(options, optionCount, cursor);

        if (pressed & (BUTTON_A | BUTTON_START)) break;

        prevJoy = joy;
        SPR_update();
        SYS_doVBlankProcess();
    }

    clearBox();
    return cursor;
}
