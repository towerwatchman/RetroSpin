#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/fb.h>

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

        // Poll for disc presence using cdrdao
        int disc_present = system("/media/fat/_Utility/cdrdao disk-info > /dev/null 2>&1");

        if (disc_present == 0) {
            // Check if mounted
            int mounted = system("mountpoint /mnt/cdrom > /dev/null 2>&1");

            if (mounted != 0) {
                // Try to mount
                if (system("mount -t iso9660 /dev/sr0 /mnt/cdrom 2>/dev/null") != 0) {
                    fprintf(stderr, "Error mounting disc\n");
                    sleep(1);  // Reduced to 1 second
                    continue;
                }
                mounted = system("mountpoint /mnt/cdrom > /dev/null 2>&1");
            }

            if (mounted == 0) {
                // Disc found and mounted - switch to terminal to hide OSD
                int send_f9 = system("echo \"k 0x01\" > /dev/MiSTer_cmd");
                if (send_f9 != 0) {
                    fprintf(stderr, "Warning: Failed to send F9 (scancode 0x01) to MiSTer_cmd\n");
                } else {
                    fprintf(stderr, "Success: Sent F9 to switch to terminal\n");
                }
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

                // Sync changes
                if (msync(fbp, screensize, MS_SYNC) != 0) {
                    perror("Warning: msync failed");
                } else {
                    fprintf(stderr, "Success: Framebuffer synced\n");
                }

                // Break to stay on the screen
                break;
            }
        }

        sleep(1);  // Reduced to 1 second
    }

    // Cleanup
    munmap(fbp, screensize);
    close(fb_fd);

    return 0;
}