// input.h
#ifndef INPUT_H
#define INPUT_H

#include <linux/input.h>

typedef struct {
    int fd;
} Keyboard;

int init_keyboard(Keyboard *kb);
void close_keyboard(Keyboard *kb);
void press_key(Keyboard *kb, int keycode);
void combo_keys(Keyboard *kb, int *keys, int num_keys);

// Functions like Go
void kb_volume_up(Keyboard *kb) { press_key(kb, KEY_VOLUMEUP); }
void kb_volume_down(Keyboard *kb) { press_key(kb, KEY_VOLUMEDOWN); }
void kb_menu(Keyboard *kb) { press_key(kb, KEY_ESC); }
// Add more: kb_back, kb_confirm, etc. using KEY_BACKSPACE, KEY_ENTER
// For combos: e.g., void kb_core_select(Keyboard *kb) { int keys[] = {KEY_LEFTALT, KEY_F12}; combo_keys(kb, keys, 2); }

#endif