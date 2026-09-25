/*
 * Inner loop of the first-person renderer (called from src/dungeon_view.c).
 *
 * void viewCopySpan(u8 *dst, const u8 *src, u32 rows, u32 r0)
 *
 * Copies `rows` pre-baked bytes (tools/make_view.py: a 2-pixel column pair, already textured and
 * shaded) down a column of the view's RAM tile buffer: one byte per row, 4 bytes apart inside a
 * tile, then on to the same column of the next tile row (28 tiles * 32 bytes further). r0 is the
 * row within the first tile. Whole tiles are copied unrolled (~19 cycles per byte), only the
 * partial first/last tile uses a loop. Assembler because this is the only hot loop in the game;
 * texture-sampling it in C at runtime cost ~200 cycles per byte (13 frames per redraw).
 *
 * C calling convention: arguments are 32-bit on the stack; only scratch registers d0-d1/a0-a1
 * are used, so nothing needs saving.
 */

    .text
    .globl  viewCopySpan
viewCopySpan:
    move.l  4(%sp),%a0              /* dst */
    move.l  8(%sp),%a1              /* src */
    move.l  12(%sp),%d1             /* rows left */
    move.l  16(%sp),%d0             /* row within the first tile */
    beq.s   .Lwhole                 /* starts on a tile boundary */

    /* partial first tile: min(8 - r0, rows) rows */
    neg.w   %d0
    addq.w  #8,%d0
    cmp.w   %d1,%d0
    ble.s   1f
    move.w  %d1,%d0
1:
    sub.w   %d0,%d1
    subq.w  #1,%d0
2:
    move.b  (%a1)+,(%a0)
    addq.l  #4,%a0
    dbra    %d0,2b
    lea     864(%a0),%a0            /* 28*32 - 32: row 0 of the next tile down */

.Lwhole:
    cmp.w   #8,%d1
    blt.s   .Ltail
    move.b  (%a1)+,(%a0)
    move.b  (%a1)+,4(%a0)
    move.b  (%a1)+,8(%a0)
    move.b  (%a1)+,12(%a0)
    move.b  (%a1)+,16(%a0)
    move.b  (%a1)+,20(%a0)
    move.b  (%a1)+,24(%a0)
    move.b  (%a1)+,28(%a0)
    lea     896(%a0),%a0            /* 28*32 */
    subq.w  #8,%d1
    bra.s   .Lwhole

.Ltail:
    subq.w  #1,%d1
    bmi.s   4f
3:
    move.b  (%a1)+,(%a0)
    addq.l  #4,%a0
    dbra    %d1,3b
4:
    rts

/*
 * void viewMaskSpan(u8 *dst, const u8 *src, u32 rows, u32 r0)
 *
 * Same walk down a column as viewCopySpan, for props (tools/make_view.py, bake_prop): src holds
 * a (mask, data) byte pair per row and each byte becomes (dst & mask) | data, so transparent
 * pixels keep the wall/floor behind them. d2 is callee-saved, hence the push.
 */
    .globl  viewMaskSpan
viewMaskSpan:
    move.l  %d2,-(%sp)
    move.l  8(%sp),%a0              /* dst */
    move.l  12(%sp),%a1             /* src */
    move.l  16(%sp),%d1             /* rows left */
    move.l  20(%sp),%d0             /* row within the first tile */
    beq.s   .Lmwhole

    neg.w   %d0
    addq.w  #8,%d0
    cmp.w   %d1,%d0
    ble.s   1f
    move.w  %d1,%d0
1:
    sub.w   %d0,%d1
    subq.w  #1,%d0
2:
    move.b  (%a1)+,%d2
    and.b   %d2,(%a0)
    move.b  (%a1)+,%d2
    or.b    %d2,(%a0)
    addq.l  #4,%a0
    dbra    %d0,2b
    lea     864(%a0),%a0

.Lmwhole:
    cmp.w   #8,%d1
    blt.s   .Lmtail
    .irp    off,0,4,8,12,16,20,24,28
    move.b  (%a1)+,%d2
    and.b   %d2,\off(%a0)
    move.b  (%a1)+,%d2
    or.b    %d2,\off(%a0)
    .endr
    lea     896(%a0),%a0
    subq.w  #8,%d1
    bra.s   .Lmwhole

.Lmtail:
    subq.w  #1,%d1
    bmi.s   4f
3:
    move.b  (%a1)+,%d2
    and.b   %d2,(%a0)
    move.b  (%a1)+,%d2
    or.b    %d2,(%a0)
    addq.l  #4,%a0
    dbra    %d1,3b
4:
    move.l  (%sp)+,%d2
    rts
