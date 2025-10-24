// input.c
#include "input.h"
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <linux/uinput.h>
#include <sys/ioctl.h>
#include <sys/time.h>
#include <errno.h>

#define SLEEP_US 40000  // 40ms

int init_keyboard(Keyboard *kb) {
    kb->fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
    if (kb->fd < 0) {
        perror("open /dev/uinput");
        return -1;
    }

    struct uinput_setup usetup;
    memset(&usetup, 0, sizeof(usetup));
    usetup.id.bustype = BUS_USB;
    usetup.id.vendor = 0x1234;
    usetup.id.product = 0x0001;
    strcpy(usetup.name, "RetroSpin Keyboard");

    ioctl(kb->fd, UI_SET_EVBIT, EV_KEY);
    ioctl(kb->fd, UI_SET_EVBIT, EV_SYN);

    // Set all key bits
    for (int i = 0; i < KEY_CNT; i++) {
        ioctl(kb->fd, UI_SET_KEYBIT, i);
    }

    if (ioctl(kb->fd, UI_DEV_SETUP, &usetup) < 0) {
        perror("UI_DEV_SETUP");
        close(kb->fd);
        return -1;
    }

    if (ioctl(kb->fd, UI_DEV_CREATE) < 0) {
        perror("UI_DEV_CREATE");
        close(kb->fd);
        return -1;
    }

    return 0;
}

void close_keyboard(Keyboard *kb) {
    if (kb->fd >= 0) {
        ioctl(kb->fd, UI_DEV_DESTROY);
        close(kb->fd);
    }
}

static void send_event(Keyboard *kb, unsigned int type, unsigned int code, int value) {
    struct input_event ev;
    memset(&ev, 0, sizeof(ev));
    gettimeofday(&ev.time, NULL);
    ev.type = type;
    ev.code = code;
    ev.value = value;
    if (write(kb->fd, &ev, sizeof(ev)) < 0) {
        perror("write event");
    }
}

void press_key(Keyboard *kb, int keycode) {
    send_event(kb, EV_KEY, keycode, 1);
    send_event(kb, EV_SYN, SYN_REPORT, 0);
    usleep(SLEEP_US);
    send_event(kb, EV_KEY, keycode, 0);
    send_event(kb, EV_SYN, SYN_REPORT, 0);
}

void combo_keys(Keyboard *kb, int *keys, int num_keys) {
    for (int i = 0; i < num_keys; i++) {
        send_event(kb, EV_KEY, keys[i], 1);
    }
    send_event(kb, EV_SYN, SYN_REPORT, 0);
    usleep(SLEEP_US);
    for (int i = 0; i < num_keys; i++) {
        send_event(kb, EV_KEY, keys[i], 0);
    }
    send_event(kb, EV_SYN, SYN_REPORT, 0);
}