#include "combat.h"
#include "figures.h"
#include "textbox.h"
#include "party.h"
#include "inventory.h"
#include "ui_panel.h"
#include "dungeon_view.h"
#include "game.h"

// Every text line must fit the message area: at most 27 characters (an umlaut counts as one).
// Names are at most 8 characters ("KOBOLD A", "LAE'ZEL"), which the formats below rely on.

const EnemyDef ENEMY_IMP = { "KOBOLD", 9, 13, 4, 4, 2, &fig_imp_sprite, 124 };

#define VIEW_CENTER_X 112   // the view is 224 px wide (view_gen.h)
#define TANK_AC     5
#define TANK_TARGET 0xFF
#define SPELL_COST  2
#define FOE_SPACING 80   // px between figure centres

typedef struct
{
    const EnemyDef *def;
    u8 hp;
    Sprite *spr;
    s16 cx;
    char name[10];
} Foe;

static Foe foes[COMBAT_MAX_ENEMIES];
static u8 foeCount;
static RoomObject *tankObj;
static const Player *viewer;
static bool defending[PARTY_MAX];
static Sprite *arrow;
static u8 targetMap[COMBAT_MAX_ENEMIES + 1];   // target menu option -> foe index or TANK_TARGET

static u8 roll(u8 die)
{
    return (random() % die) + 1;
}

// Commentary: lines stay up while the caller pauses (A skips a pause).
static void show(const char *a, const char *b, const char *c)
{
    const char *lines[3] = { a, b, c };
    textbox_print(lines, 3);
}

static void pause(u16 frames)
{
    u16 prevJoy = JOY_readJoypad(JOY_1);
    for (u16 i = 0; i < frames; i++)
    {
        u16 joy = JOY_readJoypad(JOY_1);
        if (joy & ~prevJoy & BUTTON_A) break;
        prevJoy = joy;
        figures_wait(1);
    }
}

static void say(const char *a, const char *b, const char *c)
{
    const char *lines[3] = { a, b, c };
    textbox_show(lines, 3, NULL, 0);   // NULL lines are skipped
}

static bool foesLeft(void)
{
    for (u8 i = 0; i < foeCount; i++)
        if (foes[i].hp) return TRUE;
    return FALSE;
}

static bool partyStanding(void)
{
    for (u8 i = 0; i < PARTY_MAX; i++)
        if (party.members[i].active && party.members[i].hp) return TRUE;
    return FALSE;
}

static void arrowHook(u8 cursor)
{
    u8 t = targetMap[cursor];
    if (t == TANK_TARGET)
    {
        SPR_setVisibility(arrow, HIDDEN);   // the tank is part of the view, not a figure
        return;
    }
    SPR_setPosition(arrow, foes[t].cx - 4, foes[t].def->bottom - foes[t].def->sprite->h - 10);
    SPR_setVisibility(arrow, VISIBLE);
}

static u8 chooseTarget(void)
{
    const char *options[COMBAT_MAX_ENEMIES + 1];
    u8 n = 0;
    for (u8 i = 0; i < foeCount; i++)
    {
        if (!foes[i].hp) continue;
        targetMap[n] = i;
        options[n++] = foes[i].name;
    }
    if (tankObj && !(tankObj->flags & OBJFLAG_BROKEN))
    {
        targetMap[n] = TANK_TARGET;
        options[n++] = "Säuretank";
    }
    if (n == 1) return targetMap[0];

    const char *lines[1] = { "Welches Ziel?" };
    textbox_setCursorHook(arrowHook);
    u8 choice = textbox_show(lines, 1, options, n);
    textbox_setCursorHook(NULL);
    SPR_setVisibility(arrow, HIDDEN);
    return targetMap[choice];
}

// Applies damage to a foe and writes the result line ("7 Schaden." / "... KOBOLD A fällt!").
static void hurtFoe(u8 f, u8 dmg, char *line)
{
    Foe *e = &foes[f];
    figures_blink(e->spr, 3);
    e->hp = dmg >= e->hp ? 0 : e->hp - dmg;
    if (e->hp)
        sprintf(line, "%d Schaden.", dmg);
    else
    {
        sprintf(line, "%d Schaden. %s fällt!", dmg, e->name);
        SPR_setVisibility(e->spr, HIDDEN);
    }
}

// The acid tank bursts: 2d6 to every enemy still standing.
static void burstTank(void)
{
    tankObj->flags |= OBJFLAG_BROKEN;
    dungeonView_render(viewer);
    figures_shakeView();

    u8 dmg = roll(6) + roll(6);
    u8 standing = 0, fallen = 0;
    char line[32];
    for (u8 i = 0; i < foeCount; i++)
    {
        if (!foes[i].hp) continue;
        standing++;
        hurtFoe(i, dmg, line);
        if (!foes[i].hp) fallen++;
    }
    sprintf(line, fallen && fallen == standing ? "%d Schaden - alle fallen!" : "%d Schaden an allen!", dmg);
    show("Der Tank platzt! Säure", "spritzt über die Gegner:", line);
    pause(100);
}

static void attack(Character *c, u8 target, bool spell)
{
    char l0[32], l1[32], l2[32];

    if (target == TANK_TARGET)
    {
        sprintf(l0, "%s zielt auf den Tank.", c->name);
        u8 r = roll(20);
        if (spell)
            c->mp -= SPELL_COST;
        else if (r == 1 || r + c->atk < TANK_AC)
        {
            show(l0, "Daneben!", NULL);
            pause(70);
            return;
        }
        uiPanel_redrawChrome();
        show(l0, "Treffer!", NULL);
        pause(40);
        burstTank();
        return;
    }

    Foe *e = &foes[target];
    if (spell)
    {
        c->mp -= SPELL_COST;
        uiPanel_redrawChrome();
        sprintf(l0, "%s wirkt Geschoss", c->name);
        sprintf(l1, "auf %s:", e->name);
        show(l0, l1, NULL);
        pause(30);
        hurtFoe(target, roll(4) + roll(4) + 2, l2);   // magic missile never misses
        show(l0, l1, l2);
        pause(90);
        return;
    }

    u8 r = roll(20);
    u8 total = r + c->atk;
    bool hit = r == 20 || (r != 1 && total >= e->def->ac);
    sprintf(l0, "%s greift %s an.", c->name, e->name);
    sprintf(l1, "Wurf %d + %d = %d: %s", r, c->atk, total, r == 20 ? "Kritisch!" : hit ? "Treffer!" : "daneben.");
    show(l0, l1, NULL);
    pause(40);
    if (!hit)
    {
        pause(40);
        return;
    }
    u8 dmg = roll(c->dmgDie) + c->dmgBonus;
    if (r == 20) dmg += roll(c->dmgDie);             // a natural 20 rolls the damage die twice
    hurtFoe(target, dmg, l2);
    show(l0, l1, l2);
    pause(90);
}

static void drinkPotion(Character *c)
{
    const char *options[PARTY_MAX];
    u8 who[PARTY_MAX], n = 0;
    for (u8 i = 0; i < PARTY_MAX; i++)
    {
        if (!party.members[i].active) continue;
        who[n] = i;
        options[n++] = party.members[i].name;
    }
    const char *lines[1] = { "Wer bekommt den Heiltrank?" };
    Character *t = &party.members[who[textbox_show(lines, 1, options, n)]];

    inventory.healingPotions--;
    u8 heal = roll(4) + roll(4) + 2;
    t->hp = t->hp + heal > t->hpMax ? t->hpMax : t->hp + heal;
    uiPanel_redrawChrome();

    char l0[32], l1[32];
    sprintf(l0, "%s nutzt einen Trank:", c->name);
    sprintf(l1, "%s erhält %d KP.", t->name, heal);
    show(l0, l1, NULL);
    pause(90);
}

// Schattenherz's healing spell: 1d8 + 3 KP to any member, revives the fallen.
static void healSpell(Character *c)
{
    const char *options[PARTY_MAX];
    u8 who[PARTY_MAX], n = 0;
    for (u8 i = 0; i < PARTY_MAX; i++)
    {
        if (!party.members[i].active) continue;
        who[n] = i;
        options[n++] = party.members[i].name;
    }
    const char *lines[1] = { "Wen heilen?" };
    Character *t = &party.members[who[textbox_show(lines, 1, options, n)]];

    c->mp -= SPELL_COST;
    u8 heal = roll(8) + 3;
    t->hp = t->hp + heal > t->hpMax ? t->hpMax : t->hp + heal;
    uiPanel_redrawChrome();

    char l0[32], l1[32];
    sprintf(l0, "%s wirkt Heilen:", c->name);
    sprintf(l1, "%s erhält %d KP.", t->name, heal);
    show(l0, l1, NULL);
    pause(90);
}

typedef enum { ACT_ATTACK, ACT_SPELL, ACT_HEAL, ACT_POTION, ACT_DEFEND } Action;

static void partyTurn(u8 m)
{
    Character *c = &party.members[m];
    defending[m] = FALSE;

    const char *options[4];
    Action acts[4];
    u8 n = 0;
    options[n] = "Angriff";         acts[n++] = ACT_ATTACK;
    if (c->cls == CLASS_MAGE && c->mp >= SPELL_COST)
    {
        options[n] = "Geschoss (2 ZP)"; acts[n++] = ACT_SPELL;
    }
    if (c->cls == CLASS_SHADOWHEART && c->mp >= SPELL_COST)
    {
        options[n] = "Heilen (2 ZP)"; acts[n++] = ACT_HEAL;
    }
    if (inventory.healingPotions)
    {
        options[n] = "Heiltrank";   acts[n++] = ACT_POTION;
    }
    options[n] = "Abwehr";          acts[n++] = ACT_DEFEND;

    char l0[32];
    sprintf(l0, "%s ist am Zug.", c->name);
    const char *lines[1] = { l0 };
    switch (acts[textbox_show(lines, 1, options, n)])
    {
        case ACT_ATTACK: attack(c, chooseTarget(), FALSE); break;
        case ACT_SPELL:  attack(c, chooseTarget(), TRUE); break;
        case ACT_HEAL:   healSpell(c); break;
        case ACT_POTION: drinkPotion(c); break;
        default:
            defending[m] = TRUE;                     // +2 AC until this member's next turn
            sprintf(l0, "%s geht in Deckung.", c->name);
            show(l0, NULL, NULL);
            pause(60);
            break;
    }
}

static void foeTurn(u8 f)
{
    Foe *e = &foes[f];
    u8 standing[PARTY_MAX], n = 0;
    for (u8 i = 0; i < PARTY_MAX; i++)
        if (party.members[i].active && party.members[i].hp) standing[n++] = i;
    u8 m = standing[random() % n];
    Character *c = &party.members[m];

    char l0[32], l1[32], l2[32];
    u8 ac = c->ac + (defending[m] ? 2 : 0);
    u8 r = roll(20);
    u8 total = r + e->def->atk;
    bool hit = r == 20 || (r != 1 && total >= ac);
    sprintf(l0, "%s greift %s an.", e->name, c->name);
    sprintf(l1, "Wurf %d + %d = %d: %s", r, e->def->atk, total, hit ? "Treffer!" : "daneben.");
    show(l0, l1, NULL);
    pause(40);
    if (!hit)
    {
        pause(40);
        return;
    }
    u8 dmg = roll(e->def->dmgDie) + e->def->dmgBonus;
    c->hp = dmg >= c->hp ? 0 : c->hp - dmg;
    figures_shakeView();
    uiPanel_redrawChrome();
    sprintf(l2, c->hp ? "%d Schaden." : "%d Schaden. %s fällt!", dmg, c->name);
    show(l0, l1, l2);
    pause(90);
}

static void releaseFigures(void)
{
    for (u8 i = 0; i < foeCount; i++)
        SPR_releaseSprite(foes[i].spr);
    SPR_releaseSprite(arrow);
    SPR_update();
}

static void gameOver(void)
{
    releaseFigures();
    const char *lines[3] = { "Deine Gruppe ist gefallen.", "Der Nautiloid stürzt", "weiter durch Avernus..." };
    const char *options[1] = { "Neu beginnen" };
    textbox_show(lines, 3, options, 1);
    SYS_hardReset();
}

void combat_run(const Player *p, const EnemyDef *const enemies[], u8 count, RoomObject *tank, u8 goldReward)
{
    viewer = p;
    tankObj = tank;
    foeCount = count > COMBAT_MAX_ENEMIES ? COMBAT_MAX_ENEMIES : count;
    memset(defending, 0, sizeof(defending));

    for (u8 i = 0; i < foeCount; i++)
    {
        Foe *e = &foes[i];
        e->def = enemies[i];
        e->hp = e->def->hpMax;
        e->cx = VIEW_CENTER_X + (2 * i - (foeCount - 1)) * FOE_SPACING / 2;
        e->spr = figures_add(e->def->sprite, e->cx, e->def->bottom);
        if (foeCount > 1)
            sprintf(e->name, "%s %c", e->def->name, 'A' + i);
        else
            strcpy(e->name, e->def->name);
    }
    // The marker uses colour 15 of whatever figure palette is loaded (its own isn't loaded).
    arrow = SPR_addSprite(&fig_arrow_sprite, 0, 0, TILE_ATTR(PAL2, FALSE, FALSE, FALSE));
    SPR_setVisibility(arrow, HIDDEN);

    char l0[32];
    sprintf(l0, "Kampf gegen %d Gegner!", foeCount);
    show(l0, NULL, NULL);
    pause(70);

    // Initiative: d20 + DEX for the party, d20 + 2 for enemies, rolled once per fight.
    u8 order[PARTY_MAX + COMBAT_MAX_ENEMIES], init[PARTY_MAX + COMBAT_MAX_ENEMIES], n = 0;
    for (u8 i = 0; i < PARTY_MAX; i++)
        if (party.members[i].active)
        {
            order[n] = i;
            init[n++] = roll(20) + party.members[i].dex;
        }
    for (u8 i = 0; i < foeCount; i++)
    {
        order[n] = PARTY_MAX + i;
        init[n++] = roll(20) + 2;
    }
    for (u8 i = 1; i < n; i++)          // insertion sort, highest first
        for (u8 j = i; j > 0 && init[j] > init[j - 1]; j--)
        {
            u8 t = init[j]; init[j] = init[j - 1]; init[j - 1] = t;
            t = order[j]; order[j] = order[j - 1]; order[j - 1] = t;
        }

    while (TRUE)
    {
        for (u8 i = 0; i < n; i++)
        {
            u8 who = order[i];
            if (who < PARTY_MAX)
            {
                if (party.members[who].hp) partyTurn(who);
            }
            else if (foes[who - PARTY_MAX].hp)
                foeTurn(who - PARTY_MAX);

            if (!partyStanding()) gameOver();
            if (!foesLeft()) goto won;
        }
    }

won:
    releaseFigures();
    bool revived = FALSE;
    for (u8 i = 0; i < PARTY_MAX; i++)
        if (party.members[i].active && !party.members[i].hp)
        {
            party.members[i].hp = 1;             // no permanent death outside a total defeat
            revived = TRUE;
        }
    inventory_addGold(goldReward);
    uiPanel_redrawChrome();

    char l1[32];
    sprintf(l1, "Beute: %d Gold.", goldReward);
    say("Sieg!", goldReward ? l1 : NULL, revived ? "Bewusstlose kommen zu sich." : NULL);
}
