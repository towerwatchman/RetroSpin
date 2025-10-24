/* mister.c - RetroSpin for MiSTer FPGA (framebuffer + uinput + CD read) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <linux/fb.h>
#include <linux/input.h>
#include <linux/cdrom.h>
#include <linux/uinput.h>
#include <sqlite3.h>
#include <errno.h>
#include <math.h>
#include <stdint.h>           // <-- Added for uint32_t
#include "font.h"             // <-- Font in separate file

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define SLEEP_TIME 40000

/* --------------------------------------------------------------
   uinput keyboard emulation
   -------------------------------------------------------------- */
struct Keyboard { int fd; };

int NewKeyboard(struct Keyboard *kb) {
    kb->fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
    if (kb->fd < 0) return -1;

    ioctl(kb->fd, UI_SET_EVBIT, EV_KEY);
    ioctl(kb->fd, UI_SET_EVBIT, EV_SYN);

    int keys[] = {
        KEY_VOLUMEUP, KEY_VOLUMEDOWN, KEY_MUTE,
        KEY_ESC, KEY_BACKSPACE, KEY_ENTER,
        KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT,
        KEY_F12, KEY_LEFTALT, KEY_SCROLLLOCK,
        KEY_LEFTSHIFT, KEY_LEFTCTRL, KEY_RIGHTALT,
        KEY_F11, KEY_F1, KEY_F2, KEY_F9,
        KEY_LEFTMETA
    };
    for (size_t i = 0; i < sizeof(keys)/sizeof(keys[0]); i++)
        ioctl(kb->fd, UI_SET_KEYBIT, keys[i]);

    struct uinput_setup usetup = {0};
    strcpy(usetup.name, "mrext");
    usetup.id.bustype = BUS_USB;
    usetup.id.vendor = 0x1234;
    usetup.id.product = 0x5678;

    if (ioctl(kb->fd, UI_DEV_SETUP, &usetup) < 0 ||
        ioctl(kb->fd, UI_DEV_CREATE) < 0) {
        close(kb->fd);
        return -1;
    }
    usleep(SLEEP_TIME);
    return 0;
}

void CloseKeyboard(struct Keyboard *kb) {
    if (kb->fd >= 0) {
        ioctl(kb->fd, UI_DEV_DESTROY);
        close(kb->fd);
        kb->fd = -1;
    }
}

static void emit(struct Keyboard *kb, int type, int code, int val) {
    struct input_event ie = { .type = type, .code = code, .value = val };
    write(kb->fd, &ie, sizeof(ie));
}

void KeyPress(struct Keyboard *kb, int code) {
    emit(kb, EV_KEY, code, 1);
    emit(kb, EV_SYN, SYN_REPORT, 0);
    usleep(SLEEP_TIME);
    emit(kb, EV_KEY, code, 0);
    emit(kb, EV_SYN, SYN_REPORT, 0);
}

void KeyCombo(struct Keyboard *kb, int *codes, int n) {
    for (int i = 0; i < n; i++) emit(kb, EV_KEY, codes[i], 1);
    emit(kb, EV_SYN, SYN_REPORT, 0);
    usleep(SLEEP_TIME);
    for (int i = 0; i < n; i++) emit(kb, EV_KEY, codes[i], 0);
    emit(kb, EV_SYN, SYN_REPORT, 0);
}

/* F-key shortcuts */
void ChangeBackground(struct Keyboard *kb) { KeyPress(kb, KEY_F1); }
void ToggleCoreDates(struct Keyboard *kb) { KeyPress(kb, KEY_F2); }
void Console(struct Keyboard *kb) { KeyPress(kb, KEY_F9); }
void PairBluetooth(struct Keyboard *kb) { KeyPress(kb, KEY_F11); }
void Osd(struct Keyboard *kb) { KeyPress(kb, KEY_F12); }
void CoreSelect(struct Keyboard *kb) {
    int k[] = {KEY_LEFTALT, KEY_F12};
    KeyCombo(kb, k, 2);
}

/* --------------------------------------------------------------
   Framebuffer
   -------------------------------------------------------------- */
int fb_fd = -1;
struct fb_var_screeninfo vinfo;
struct fb_fix_screeninfo finfo;
char *fbp = NULL;
long int screensize;

void put_pixel(int x, int y, unsigned char r, unsigned char g, unsigned char b) {
    if (x < 0 || x >= (int)vinfo.xres || y < 0 || y >= (int)vinfo.yres) return;
    long int loc = (x + vinfo.xoffset) * (vinfo.bits_per_pixel/8) +
                   (y + vinfo.yoffset) * finfo.line_length;
    ((uint32_t*)fbp)[loc/4] = (r << 16) | (g << 8) | b;
}

void clear_screen(void) { memset(fbp, 0, screensize); }

void draw_char(char c, int x, int y) {
    int idx = (unsigned char)c - 32;
    if (idx < 0 || idx >= 95) return;
    for (int row = 0; row < 8; row++) {
        unsigned char line = font8x8[idx][row];
        for (int col = 0; col < 8; col++) {
            if (line & (1 << (7-col)))
                put_pixel(x + col, y + row, 255, 255, 255);
        }
    }
}

void draw_string(const char *s, int x, int y) {
    while (*s) draw_char(*s++, x += 8, y);
}

void draw_circle(int cx, int cy, int r, unsigned char red, unsigned char green, unsigned char blue) {
    for (int y = -r; y <= r; y++)
        for (int x = -r; x <= r; x++)
            if (x*x + y*y <= r*r)
                put_pixel(cx + x, cy + y, red, green, blue);
}

void draw_line(int x0, int y0, int x1, int y1, unsigned char r, unsigned char g, unsigned char b) {
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy, e2;
    while (1) {
        put_pixel(x0, y0, g, b, r);  // BGR order
        if (x0 == x1 && y0 == y1) break;
        e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

/* --------------------------------------------------------------
   Menu & disc test
   -------------------------------------------------------------- */
void draw_menu(int sel) {
    clear_screen();
    draw_string("RETROSPIN", (vinfo.xres - 9*8)/2, 50);
    draw_string("Update database", (vinfo.xres - 15*8)/2, 180);
    draw_string("Test disc",       (vinfo.xres - 9*8)/2,  240);
    draw_string("Save disc",       (vinfo.xres - 9*8)/2,  300);
    if (sel == 0) draw_string("*", (vinfo.xres - 15*8)/2 - 16, 180);
    if (sel == 1) draw_string("*", (vinfo.xres - 9*8)/2  - 16, 240);
    if (sel == 2) draw_string("*", (vinfo.xres - 9*8)/2  - 16, 300);
}

void test_disc(void) {
    int cd = open("/dev/sr0", O_RDONLY | O_NONBLOCK);
    if (cd >= 0) {
        for (int i = 0; i < 10; i++) {
            struct cdrom_msf msf = {0};
            int lba = i + 150;
            msf.cdmsf_min0   = lba / (60*75);
            msf.cdmsf_sec0   = (lba / 75) % 60;
            msf.cdmsf_frame0 = lba % 75;
            if (ioctl(cd, CDROMREADRAW, &msf) < 0) break;
        }
        close(cd);
    }

    int cx = vinfo.xres / 2, cy = vinfo.yres / 2;
    int radius = 60;
    for (int i = 0; i < 36; i++) {
        clear_screen();
        draw_string("Reading disc...", (vinfo.xres - 13*8)/2, cy + radius + 30);
        draw_circle(cx, cy, radius, 200, 200, 200);
        int ang = i * 10;
        int x1 = cx + (int)(radius * cos(ang * M_PI / 180.0));
        int y1 = cy + (int)(radius * sin(ang * M_PI / 180.0));
        draw_line(cx, cy, x1, y1, 255, 0, 0);
        usleep(60000);
    }
}

/* --------------------------------------------------------------
   main()
   -------------------------------------------------------------- */
int main(void) {
    /* ---- SQLite DB ---- */
    sqlite3 *db;
    if (sqlite3_open("games.db", &db) == SQLITE_OK) {
        printf("games.db created/opened\n");
        sqlite3_close(db);
    }

    /* ---- Framebuffer ---- */
    fb_fd = open("/dev/fb0", O_RDWR);
    if (fb_fd == -1) { perror("fb0"); return 1; }
    if (ioctl(fb_fd, FBIOGET_FSCREENINFO, &finfo) || ioctl(fb_fd, FBIOGET_VSCREENINFO, &vinfo)) {
        perror("ioctl fb"); close(fb_fd); return 1;
    }
    if (vinfo.bits_per_pixel != 32) {
        fprintf(stderr, "Only 32bpp supported\n"); close(fb_fd); return 1;
    }
    screensize = vinfo.xres * vinfo.yres * 4;
    fbp = mmap(NULL, screensize, PROT_READ | PROT_WRITE, MAP_SHARED, fb_fd, 0);
    if (fbp == MAP_FAILED) { perror("mmap"); close(fb_fd); return 1; }

    /* ---- Input ---- */
    int input_fd = open("/dev/input/event0", O_RDONLY);
    if (input_fd == -1) input_fd = open("/dev/input/event1", O_RDONLY);
    if (input_fd == -1) { perror("input"); munmap(fbp, screensize); close(fb_fd); return 1; }

    /* ---- uinput ---- */
    struct Keyboard kb = { .fd = -1 };
    NewKeyboard(&kb);

    /* ---- Menu loop ---- */
    int selected = 0, running = 1;
    draw_menu(selected);
    while (running) {
        struct input_event ev;
        if (read(input_fd, &ev, sizeof(ev)) == sizeof(ev) && ev.type == EV_KEY && ev.value == 1) {
            switch (ev.code) {
                case KEY_UP:    selected = (selected - 1 + 3) % 3; draw_menu(selected); break;
                case KEY_DOWN:  selected = (selected + 1) % 3; draw_menu(selected); break;
                case KEY_ENTER:
                case KEY_KPENTER:
                    if (selected == 0) printf("Update DB\n");
                    else if (selected == 1) test_disc();
                    else if (selected == 2) printf("Save disc\n");
                    draw_menu(selected);
                    break;
                case KEY_ESC: running = 0; break;
            }
        }
    }

    CloseKeyboard(&kb);
    close(input_fd);
    munmap(fbp, screensize);
    close(fb_fd);
    return 0;
}