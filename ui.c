/* ui.c – Fixed font + reliable mrext input */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/select.h>
#include <linux/fb.h>
#include <linux/input.h>
#include <linux/input-event-codes.h>
#include <dirent.h>
#include <stdint.h>

static int  fb_fd = -1;
static uint32_t *fb_mem = NULL;
static int  fb_w = 0, fb_h = 0, fb_bpp = 0;
static struct fb_var_screeninfo vinfo;
static int  input_fd = -1;

const char *menu_items[] = { "Update Database", "Test Disc", "Load Disc", "Close" };
#define MENU_COUNT 4

/* --- FULL 5x7 FONT (FIXED) --- */
static const uint8_t font[256][7] = {
    [' '] = {0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['A'] = {0x0E,0x11,0x11,0x1F,0x11,0x11,0x11},
    ['B'] = {0x1E,0x11,0x11,0x1E,0x11,0x11,0x1E},
    ['C'] = {0x0E,0x11,0x10,0x10,0x10,0x11,0x0E},
    ['D'] = {0x1E,0x11,0x11,0x11,0x11,0x11,0x1E},
    ['E'] = {0x1F,0x10,0x10,0x1E,0x10,0x10,0x1F},
    ['F'] = {0x1F,0x10,0x10,0x1E,0x10,0x10,0x10},
    ['G'] = {0x0E,0x11,0x10,0x17,0x11,0x11,0x0E},
    ['H'] = {0x11,0x11,0x11,0x1F,0x11,0x11,0x11},
    ['I'] = {0x0E,0x04,0x04,0x04,0x04,0x04,0x0E},
    ['J'] = {0x01,0x01,0x01,0x01,0x01,0x11,0x0E},
    ['K'] = {0x11,0x12,0x14,0x18,0x14,0x12,0x11},
    ['L'] = {0x10,0x10,0x10,0x10,0x10,0x10,0x1F},
    ['M'] = {0x11,0x1B,0x15,0x11,0x11,0x11,0x11},
    ['N'] = {0x11,0x19,0x15,0x13,0x11,0x11,0x11},
    ['O'] = {0x0E,0x11,0x11,0x11,0x11,0x11,0x0E},
    ['P'] = {0x1E,0x11,0x11,0x1E,0x10,0x10,0x10},
    ['Q'] = {0x0E,0x11,0x11,0x11,0x15,0x12,0x0D},
    ['R'] = {0x1E,0x11,0x11,0x1E,0x14,0x12,0x11},
    ['S'] = {0x0E,0x11,0x10,0x0E,0x01,0x11,0x0E},
    ['T'] = {0x1F,0x04,0x04,0x04,0x04,0x04,0x04},
    ['U'] = {0x11,0x11,0x11,0x11,0x11,0x11,0x0E},
    ['V'] = {0x11,0x11,0x11,0x11,0x11,0x0A,0x04},
    ['W'] = {0x11,0x11,0x11,0x15,0x15,0x1B,0x11},
    ['X'] = {0x11,0x11,0x0A,0x04,0x0A,0x11,0x11},
    ['Y'] = {0x11,0x11,0x11,0x0A,0x04,0x04,0x04},
    ['Z'] = {0x1F,0x01,0x02,0x04,0x08,0x10,0x1F},
    ['0'] = {0x0E,0x11,0x13,0x15,0x19,0x11,0x0E},
    ['1'] = {0x04,0x0C,0x04,0x04,0x04,0x04,0x0E},
    ['2'] = {0x0E,0x11,0x01,0x02,0x04,0x08,0x1F},
    ['3'] = {0x1F,0x01,0x02,0x07,0x01,0x11,0x0E},
    ['4'] = {0x02,0x06,0x0A,0x12,0x1F,0x02,0x02},
    ['5'] = {0x1F,0x10,0x1E,0x01,0x01,0x11,0x0E},
    ['6'] = {0x0E,0x10,0x10,0x1E,0x11,0x11,0x0E},
    ['7'] = {0x1F,0x01,0x02,0x04,0x04,0x04,0x04},
    ['8'] = {0x0E,0x11,0x11,0x0E,0x11,0x11,0x0E},
    ['9'] = {0x0E,0x11,0x11,0x0F,0x01,0x11,0x0E},
    ['.'] = {0x00,0x00,0x00,0x00,0x00,0x06,0x06},
};

/* --- Draw char --- */
static void draw_char(int x, int y, char c, uint32_t color)
{
    const uint8_t *g = font[(unsigned char)c];
    if (!g[0]) return;
    for (int dy = 0; dy < 7; ++dy) {
        uint8_t row = g[dy];
        for (int dx = 0; dx < 5; ++dx) {
            if (row & (1 << (4 - dx))) {
                int px = x + dx, py = y + dy;
                if (px >= 0 && px < fb_w && py >= 0 && py < fb_h)
                    fb_mem[py * fb_w + px] = color;
            }
        }
    }
}

static void draw_text_centered(int y, const char *txt, uint32_t color)
{
    int len = strlen(txt), width = len * 6;
    int x = (fb_w - width) / 2;
    for (int i = 0; i < len; ++i)
        draw_char(x + i*6, y, txt[i], color);
}

static void clear_screen(uint32_t color)
{
    for (int i = 0; i < fb_w * fb_h; ++i) fb_mem[i] = color;
}

/* --- Find mrext device --- */
static int find_mrext_device(void)
{
    DIR *d = opendir("/dev/input");
    if (!d) return -1;
    struct dirent *ent;
    char path[64], name[256];
    int fd;

    while ((ent = readdir(d))) {
        if (strncmp(ent->d_name, "event", 5)) continue;
        snprintf(path, sizeof(path), "/dev/input/%s", ent->d_name);
        fd = open(path, O_RDONLY | O_NONBLOCK);
        if (fd < 0) continue;
        name[0] = '\0';
        if (ioctl(fd, EVIOCGNAME(sizeof(name)), name) < 0) { close(fd); continue; }
        if (strcmp(name, "mrext") == 0) {
            closedir(d);
            return fd;
        }
        close(fd);
    }
    closedir(d);
    return -1;
}

/* --- UI --- */
int ui_init(void)
{
    fb_fd = open("/dev/fb0", O_RDWR);
    if (fb_fd < 0) return perror("open /dev/fb0"), -1;

    if (ioctl(fb_fd, FBIOGET_VSCREENINFO, &vinfo) < 0)
        return perror("FBIOGET_VSCREENINFO"), -1;

    fb_w = vinfo.xres; fb_h = vinfo.yres; fb_bpp = vinfo.bits_per_pixel / 8;
    long sz = fb_w * fb_h * fb_bpp;
    fb_mem = mmap(NULL, sz, PROT_READ | PROT_WRITE, MAP_SHARED, fb_fd, 0);
    if (fb_mem == MAP_FAILED) return perror("mmap"), -1;

    clear_screen(0x00000000);

    input_fd = find_mrext_device();
    if (input_fd < 0) return fprintf(stderr, "mrext not found\n"), -1;

    return 0;
}

void ui_show_menu(int sel)
{
    clear_screen(0x00000000);
    int y = (fb_h - MENU_COUNT * 20) / 2;
    for (int i = 0; i < MENU_COUNT; ++i)
        draw_text_centered(y + i * 20, menu_items[i], (i == sel) ? 0x00FFFFFF : 0x00808080);
    draw_text_centered(fb_h - 40, "Use D-pad / A to select", 0x00AAAAAA);
}

int ui_wait_for_selection(void)
{
    int sel = 0;
    struct input_event ev;
    fd_set fds;
    struct timeval tv;

    ui_show_menu(sel);

    while (1) {
        FD_ZERO(&fds);
        FD_SET(input_fd, &fds);
        tv.tv_sec = 0; tv.tv_usec = 10000;

        int ret = select(input_fd + 1, &fds, NULL, NULL, &tv);
        if (ret <= 0) continue;

        if (read(input_fd, &ev, sizeof(ev)) != sizeof(ev)) continue;
        if (ev.type != EV_KEY || ev.value != 1) continue;

        if (ev.code == KEY_UP || ev.code == BTN_DPAD_UP) { if (sel > 0) sel--; }
        else if (ev.code == KEY_DOWN || ev.code == BTN_DPAD_DOWN) { if (sel < MENU_COUNT-1) sel++; }
        else if (ev.code == KEY_ENTER || ev.code == BTN_A || ev.code == BTN_START) return sel;
        else if (ev.code == KEY_ESC || ev.code == BTN_B) return -1;

        ui_show_menu(sel);
    }
}

void ui_close(void)
{
    if (fb_mem) munmap(fb_mem, fb_w * fb_h * fb_bpp);
    if (fb_fd >= 0) close(fb_fd);
    if (input_fd >= 0) close(input_fd);
}