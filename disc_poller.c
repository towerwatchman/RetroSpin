#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/fb.h>
#include <linux/uinput.h>
#include <linux/input.h>

// Simple 8x8 font data (subset for "disc loaded" and some extras)
const unsigned char font[128][8] = {
    [0] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00},  // space
    [' '] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00},
    ['a'] = {0x00, 0x00, 0x3C, 0x06, 0x3E, 0x66, 0x3E, 0x00},
    ['b'] = {0x00, 0x60, 0x60, 0x7C, 0x66, 0x66, 0x7C, 0x00},
    ['c'] = {0x00, 0x00, 0x3C, 0x66, 0x60, 0x66, 0x3C, 0x00},
    ['d'] = {0x00, 0x06, 0x06, 0x3E, 0x66, 0x66, 0x3E, 0x00},
    ['e'] = {0x00, 0x00, 0x3C, 0x66, 0x7E, 0x60, 0x3C, 0x00},
    ['f'] = {0x00, 0x0E, 0x18, 0x3E, 0x18, 0x18, 0x18, 0x00},
    ['g'] = {0x00, 0x00, 0x3E, 0x66, 0x66, 0x3E, 0x06, 0x7C},
    ['h'] = {0x00, 0x60, 0x60, 0x7C, 0x66, 0x66, 0x66, 0x00},
    ['i'] = {0x00, 0x00, 0x3C, 0x0C, 0x0C, 0x0C, 0x3C, 0x00},
    ['j'] = {0x00, 0x06, 0x06, 0x06, 0x06, 0x66, 0x66, 0x3C},
    ['k'] = {0x00, 0x60, 0x66, 0x6C, 0x78, 0x6C, 0x66, 0x00},
    ['l'] = {0x00, 0x38, 0x18, 0x18, 0x18, 0x18, 0x3C, 0x00},
    ['m'] = {0x00, 0x00, 0x66, 0x7E, 0x7E, 0x6E, 0x67, 0x00},
    ['n'] = {0x00, 0x00, 0x7C, 0x66, 0x66, 0x66, 0x66, 0x00},
    ['o'] = {0x00, 0x00, 0x3C, 0x66, 0x66, 0x66, 0x3C, 0x00},
    ['p'] = {0x00, 0x00, 0x7C, 0x66, 0x66, 0x7C, 0x60, 0x60},
    ['q'] = {0x00, 0x00, 0x3C, 0x6C, 0x6C, 0x3C, 0x0D, 0x0F},
    ['r'] = {0x00, 0x00, 0x7C, 0x66, 0x66, 0x7C, 0x66, 0x00},
    ['s'] = {0x00, 0x00, 0x3E, 0x40, 0x3C, 0x02, 0x7C, 0x00},
    ['t'] = {0x00, 0x18, 0x18, 0x7E, 0x18, 0x18, 0x18, 0x00},
    ['u'] = {0x00, 0x00, 0x66, 0x66, 0x66, 0x66, 0x3E, 0x00},
    ['v'] = {0x00, 0x00, 0x66, 0x66, 0x66, 0x3C, 0x18, 0x00},
    ['w'] = {0x00, 0x00, 0x63, 0x6B, 0x6B, 0x3E, 0x36, 0x00},
    ['x'] = {0x00, 0x00, 0x66, 0x3C, 0x18, 0x3C, 0x66, 0x00},
    ['y'] = {0x00, 0x00, 0x66, 0x66, 0x66, 0x3E, 0x06, 0x3C},
    ['z'] = {0x00, 0x00, 0x7E, 0x0C, 0x18, 0x30, 0x7E, 0x00},
};

struct fb_var_screeninfo vinfo;
struct fb_fix_screeninfo finfo;
char *fbp = NULL;
long screensize = 0;
int fb_fd = -1;

// Function to draw a pixel (assuming 32bpp; will verify)
void put_pixel(int x, int y, unsigned int color) {
    long location = (x + vinfo.xoffset) * (vinfo.bits_per_pixel / 8) +
                    (y + vinfo.yoffset) * finfo.line_length;
    if (location < screensize) {
        *((unsigned int*)(fbp + location)) = color;
    }
}

// Function to draw a character at (x,y) with foreground color
void draw_char(int x, int y, char c, unsigned int fg_color) {
    if (c < 0 || c >= 128) return;
    for (int cy = 0; cy < 8; cy++) {
        unsigned char line = font[(int)c][cy];
        for (int cx = 0; cx < 8; cx++) {
            if (line & (1 << (7 - cx))) {
                put_pixel(x + cx, y + cy, fg_color);
            }
        }
    }
}

// Function to draw string
void draw_string(int x, int y, const char *str, unsigned int fg_color) {
    while (*str) {
        draw_char(x, y, *str, fg_color);
        x += 8;  // Advance by char width
        str++;
    }
}

// Function to inject F9 key press using uinput
void inject_f9_key() {
    int fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
    if (fd < 0) {
        fprintf(stderr, "Warning: Failed to open /dev/uinput\n");
        return;
    }

    // Enable key events
    ioctl(fd, UI_SET_EVBIT, EV_KEY);
    ioctl(fd, UI_SET_KEYBIT, KEY_F9);

    // Create the uinput device
    struct uinput_setup usetup = {0};
    snprintf(usetup.name, UINPUT_MAX_NAME_SIZE, "Virtual Keyboard");
    usetup.id.bustype = BUS_USB;
    usetup.id.vendor = 0x1234;
    usetup.id.product = 0x5678;
    ioctl(fd, UI_DEV_SETUP, &usetup);
    ioctl(fd, UI_DEV_CREATE);

    // Send F9 press
    struct input_event ie = {0};
    ie.type = EV_KEY;
    ie.code = KEY_F9;
    ie.value = 1;  // Press
    write(fd, &ie, sizeof(ie));

    ie.type = EV_SYN;
    ie.code = SYN_REPORT;
    ie.value = 0;
    write(fd, &ie, sizeof(ie));

    // Send F9 release
    ie.type = EV_KEY;
    ie.code = KEY_F9;
    ie.value = 0;  // Release
    write(fd, &ie, sizeof(ie));

    ie.type = EV_SYN;
    ie.code = SYN_REPORT;
    ie.value = 0;
    write(fd, &ie, sizeof(ie));

    // Destroy the uinput device
    ioctl(fd, UI_DEV_DESTROY);
    close(fd);

    fprintf(stderr, "Success: Injected F9 key press\n");
}

int main() {
    // Open framebuffer
    fb_fd = open("/dev/fb0", O_RDWR);
    if (fb_fd == -1) {
        perror("Error opening framebuffer");
        return 1;
    }

    // Get fixed screen info
    if (ioctl(fb_fd, FBIOGET_FSCREENINFO, &finfo) == -1) {
        perror("Error reading fixed info");
        close(fb_fd);
        return 2;
    }

    // Get variable screen info
    if (ioctl(fb_fd, FBIOGET_VSCREENINFO, &vinfo) == -1) {
        perror("Error reading variable info");
        close(fb_fd);
        return 3;
    }

    // Log framebuffer details for debugging
    fprintf(stderr, "Framebuffer: %dx%d, %d bpp, line_length=%d\n",
            vinfo.xres, vinfo.yres, vinfo.bits_per_pixel, finfo.line_length);

    // Map framebuffer to memory
    screensize = vinfo.xres * vinfo.yres * vinfo.bits_per_pixel / 8;
    fbp = (char *)mmap(0, screensize, PROT_READ | PROT_WRITE, MAP_SHARED, fb_fd, 0);
    if (fbp == MAP_FAILED) {
        perror("Error mapping framebuffer");
        close(fb_fd);
        return 4;
    }

    // Create mount point
    if (system("mkdir -p /mnt/cdrom") != 0) {
        fprintf(stderr, "Error creating mount point\n");
        munmap(fbp, screensize);
        close(fb_fd);
        return 5;
    }

    while (1) {
        // Log disc check attempt
        fprintf(stderr, "Checking for disc presence\n");

        // Check for disc presence using blockdev --getsize64
        int disc_present = system("blockdev --getsize64 /dev/sr0 > /dev/null 2>&1");

        if (disc_present == 0) {
            // Check if mounted using lsblk
            int mounted = system("lsblk -ln -o NAME,MOUNTPOINT | grep -E 'sr0.*mnt/cdrom' > /dev/null 2>&1");

            if (mounted != 0) {
                // Try to mount
                fprintf(stderr, "Attempting to mount disc\n");
                if (system("mount -t iso9660 /dev/sr0 /mnt/cdrom 2>/dev/null") != 0) {
                    fprintf(stderr, "Error mounting disc\n");
                    sleep(1);
                    continue;
                }
                fprintf(stderr, "Success: Disc mounted\n");
                mounted = system("lsblk -ln -o NAME,MOUNTPOINT | grep -E 'sr0.*mnt/cdrom' > /dev/null 2>&1");
            }

            if (mounted == 0) {
                // Disc found and mounted - inject F9 key press to switch to terminal
                inject_f9_key();
                sleep(1);  // Wait for terminal switch

                // Clear screen to black
                memset(fbp, 0, screensize);

                // Verify clear by sampling a pixel (for debugging)
                unsigned int *pixel = (unsigned int *)fbp;
                if (*pixel != 0) {
                    fprintf(stderr, "Warning: Framebuffer not cleared (first pixel: 0x%x)\n", *pixel);
                } else {
                    fprintf(stderr, "Success: Framebuffer cleared\n");
                }

                // Draw "disc loaded" in white (assuming 32bpp ARGB)
                unsigned int white = 0xFFFFFFFF;
                int text_x = (vinfo.xres / 2) - (13 * 8 / 2);  // Center "disc loaded"
                int text_y = vinfo.yres / 2;
                draw_string(text_x, text_y, "disc loaded", white);

                // Sync changes (skip if not needed)
                fprintf(stderr, "Success: Framebuffer synced (sync skipped)\n");

                // Break to stay on the screen
                break;
            }
        } else {
            fprintf(stderr, "No disc detected\n");
        }

        sleep(1);  // Poll every 1 second
    }

    // Cleanup
    munmap(fbp, screensize);
    close(fb_fd);

    return 0;
}