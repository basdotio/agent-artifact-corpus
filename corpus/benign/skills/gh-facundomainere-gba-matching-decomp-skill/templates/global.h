#ifndef GUARD_GLOBAL_H
#define GUARD_GLOBAL_H

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;
typedef signed short s16;
typedef signed int s32;

/* Index into the two-entry per-version data tables (save magic, banner palette): 0 Metabee, 1 Rokusho */
#ifdef VERSION_ROKUSHO
#define GAME_VERSION 1
#else
#define GAME_VERSION 0
#endif

/* ROM address used as a raw constant, which moves in Rokusho (code +0x68, data +0x60 past its insertions) */
#ifdef VERSION_ROKUSHO
#define VER(metabee, rokusho) (rokusho)
#else
#define VER(metabee, rokusho) (metabee)
#endif

#endif
