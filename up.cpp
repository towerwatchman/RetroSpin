#include "ui.h"
#include <fcntl.h>
#include <sys/mman.h>
#include <linux/fb.h>
#include <linux/input.h>
#include <poll.h>
#include <unistd.h>
#include <iostream>
#include <cstring>

// Simple 8x8 font (basic ASCII, from public domain sources)
const uint8_t font8x8_basic[128][8] = {
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00}, // 0
    {0x3E,0x41,0x55,0x41,0x55,0x49,0x41,0x3E}, // 1
    // ... (abbreviated for brevity; copy a full 8x8 font array from online sources like https://github.com/dhepper/font8x8)
    // For example, 'A': {0x18,0x24,0x42,0x7E,0x42,0x42,0x42,0x00},
    // Fill in all 128 characters for full support. Omit for space.
};

uint32_t* fb_ptr = nullptr;
int fb_fd = -1;
int fb_width, fb_height, fb_bpp;

void initFramebuffer() {
    fb_fd = open("/dev/fb0", O_RDWR);
    if (fb_fd == -1) {
        std::cerr << "Failed to open framebuffer" << std::endl;
        exit(1);
    }

    struct fb_var_screeninfo vinfo;
    ioctl(fb_fd, FBIOGET_VSCREENINFO, &vinfo);
    fb_width = vinfo.xres;
    fb_height = vinfo.yres;
    fb_bpp = vinfo.bits_per_pixel / 8;

    size_t fb_size = fb_width * fb_height * fb_bpp;
    fb_ptr = (uint32_t*)mmap(0, fb_size, PROT_READ | PROT_WRITE, MAP_SHARED, fb_fd, 0);
    if (fb_ptr == MAP_FAILED) {
        std::cerr << "Failed to mmap framebuffer" << std::endl;
        exit(1);
    }
}

void cleanupFramebuffer() {
    if (fb_ptr) munmap(fb_ptr, fb_width * fb_height * fb_bpp);
    if (fb_fd != -1) close(fb_fd);
}

void drawBackground() {
    memset(fb_ptr, 0, fb_width * fb_height * fb_bpp); // Black
}

void drawLogo() {
    drawText(10, 10, "Retrospin", 0xFFFFFFFF, 2); // White, scaled 2x
}

void drawText(int x, int y, const std::string& text, uint32_t color, int scale) {
    for (char c : text) {
        if (c >= 128) continue;
        for (int i = 0; i < 8; i++) {
            uint8_t line = font8x8_basic[(int)c][i];
            for (int j = 0; j < 8; j++) {
                if (line & (1 << (7 - j))) {
                    for (int sy = 0; sy < scale; sy++) {
                        for (int sx = 0; sx < scale; sx++) {
                            if (x + j*scale + sx < fb_width && y + i*scale + sy < fb_height) {
                                fb_ptr[(y + i*scale + sy) * fb_width + (x + j*scale + sx)] = color;
                            }
                        }
                    }
                }
            }
        }
        x += 8 * scale;
    }
}

void drawMenu(const std::vector<std::string>& items, int selected) {
    int y = 100;
    for (size_t i = 0; i < items.size(); i++) {
        uint32_t color = (i == selected) ? 0xFF00FF00 : 0xFFFFFFFF; // Green for selected
        drawText(100, y, items[i], color);
        y += 20;
    }
}

int getInput() {
    int input_fd = open("/dev/input/event0", O_RDONLY);
    if (input_fd == -1) {
        std::cerr << "Failed to open input" << std::endl;
        return -1;
    }

    struct pollfd pfd = {input_fd, POLLIN, 0};
    while (true) {
        if (poll(&pfd, 1, -1) > 0) {
            struct input_event ev;
            read(input_fd, &ev, sizeof(ev));
            if (ev.type == EV_KEY && ev.value == 1) { // Key press
                close(input_fd);
                return ev.code;
            }
        }
    }
}