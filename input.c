/* input.c – Exact Go behavior: 40ms delay on ALL Press() */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <linux/input-event-codes.h>
#include <stdint.h>

#define SLEEP_TIME_US 40000  /* 40ms = 40000μs */

typedef struct { int fd; } Keyboard;

/* --- Send event --- */
static void send_event(Keyboard *kb, uint16_t type, uint16_t code, int32_t value)
{
    struct input_event ie = {0};
    ie.type = type; ie.code = code; ie.value = value;
    write(kb->fd, &ie, sizeof(ie));
}

static void sync_report(Keyboard *kb)
{
    send_event(kb, EV_SYN, SYN_REPORT, 0);
}

/* --- Create virtual keyboard --- */
int keyboard_init(Keyboard *kb)
{
    memset(kb, 0, sizeof(*kb));
    kb->fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
    if (kb->fd < 0) return perror("open /dev/uinput"), -1;

    ioctl(kb->fd, UI_SET_EVBIT, EV_KEY);
    ioctl(kb->fd, UI_SET_EVBIT, EV_SYN);

    /* Enable ALL keys used in Go */
    int keys[] = {
        KEY_VOLUMEUP, KEY_VOLUMEDOWN, KEY_MUTE,
        KEY_ESC, KEY_BACKSPACE, KEY_ENTER,
        KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT,
        KEY_F12, KEY_LEFTALT, KEY_SCROLLLOCK,
        KEY_LEFTSHIFT, KEY_LEFTCTRL, KEY_RIGHTALT,
        KEY_F11, KEY_F1, KEY_F2, KEY_F9,
        KEY_LEFTMETA
    };
    for (size_t i = 0; i < sizeof(keys)/sizeof(keys[0]); ++i)
        ioctl(kb->fd, UI_SET_KEYBIT, keys[i]);

    struct uinput_setup us = {0};
    us.id.bustype = BUS_VIRTUAL;
    us.id.vendor = 0x0001; us.id.product = 0x0001;
    strncpy(us.name, "mrext", UINPUT_MAX_NAME_SIZE);  /* EXACT NAME */

    if (ioctl(kb->fd, UI_DEV_SETUP, &us) < 0)
        return perror("UI_DEV_SETUP"), close(kb->fd), -1;
    if (ioctl(kb->fd, UI_DEV_CREATE) < 0)
        return perror("UI_DEV_CREATE"), close(kb->fd), -1;

    usleep(200000);  /* 200ms settle */
    return 0;
}

void keyboard_close(Keyboard *kb)
{
    if (kb->fd >= 0) {
        ioctl(kb->fd, UI_DEV_DESTROY);
        close(kb->fd);
        kb->fd = -1;
    }
}

/* --- Press with 40ms delay (Go: Press) --- */
static void keyboard_press(Keyboard *kb, int key)
{
    send_event(kb, EV_KEY, key, 1); sync_report(kb);
    usleep(SLEEP_TIME_US);  /* 40ms */
    send_event(kb, EV_KEY, key, 0); sync_report(kb);
}

/* --- Combo (Go: Combo) --- */
static void keyboard_combo(Keyboard *kb, int count, const int *keys)
{
    for (int i = 0; i < count; ++i) send_event(kb, EV_KEY, keys[i], 1);
    sync_report(kb);
    usleep(SLEEP_TIME_US);
    for (int i = 0; i < count; ++i) send_event(kb, EV_KEY, keys[i], 0);
    sync_report(kb);
}

/* --- Public API (Go match) --- */
void keyboard_volume_up(Keyboard *kb)     { keyboard_press(kb, KEY_VOLUMEUP); }
void keyboard_volume_down(Keyboard *kb)   { keyboard_press(kb, KEY_VOLUMEDOWN); }
void keyboard_volume_mute(Keyboard *kb)   { keyboard_press(kb, KEY_MUTE); }
void keyboard_menu(Keyboard *kb)          { keyboard_press(kb, KEY_ESC); }
void keyboard_back(Keyboard *kb)          { keyboard_press(kb, KEY_BACKSPACE); }
void keyboard_confirm(Keyboard *kb)       { keyboard_press(kb, KEY_ENTER); }
void keyboard_cancel(Keyboard *kb)        { keyboard_menu(kb); }
void keyboard_up(Keyboard *kb)            { keyboard_press(kb, KEY_UP); }
void keyboard_down(Keyboard *kb)          { keyboard_press(kb, KEY_DOWN); }
void keyboard_left(Keyboard *kb)          { keyboard_press(kb, KEY_LEFT); }
void keyboard_right(Keyboard *kb)         { keyboard_press(kb, KEY_RIGHT); }
void keyboard_osd(Keyboard *kb)           { keyboard_press(kb, KEY_F12); }
void keyboard_core_select(Keyboard *kb)   { int k[] = {KEY_LEFTALT, KEY_F12}; keyboard_combo(kb, 2, k); }
void keyboard_screenshot(Keyboard *kb)    { int k[] = {KEY_LEFTALT, KEY_SCROLLLOCK}; keyboard_combo(kb, 2, k); }
void keyboard_raw_screenshot(Keyboard *kb){ int k[] = {KEY_LEFTALT, KEY_LEFTSHIFT, KEY_SCROLLLOCK}; keyboard_combo(kb, 3, k); }
void keyboard_user(Keyboard *kb)          { int k[] = {KEY_LEFTCTRL, KEY_LEFTALT, KEY_RIGHTALT}; keyboard_combo(kb, 3, k); }
void keyboard_reset(Keyboard *kb)         { int k[] = {KEY_LEFTSHIFT, KEY_LEFTCTRL, KEY_LEFTALT, KEY_RIGHTALT}; keyboard_combo(kb, 4, k); }
void keyboard_pair_bluetooth(Keyboard *kb){ keyboard_press(kb, KEY_F11); }
void keyboard_change_background(Keyboard *kb){ keyboard_press(kb, KEY_F1); }
void keyboard_toggle_core_dates(Keyboard *kb){ keyboard_press(kb, KEY_F2); }

/* --- F9 and F12: use Press() → 40ms hold --- */
void keyboard_console(Keyboard *kb)       { keyboard_press(kb, KEY_F9); }
void keyboard_exit_console(Keyboard *kb)  { keyboard_press(kb, KEY_F12); }

void keyboard_computer_osd(Keyboard *kb)  { int k[] = {KEY_LEFTMETA, KEY_F12}; keyboard_combo(kb, 2, k); }