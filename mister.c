#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <sqlite3.h>
#include <SDL2/SDL.h>
#include <SDL2/SDL_image.h>
#include <SDL2/SDL_ttf.h>
#include <math.h>

#define SLEEP_TIME 40000 // 40 ms in us

// --- uinput Keyboard Emulation ---
struct Keyboard {
    int fd;
};

int NewKeyboard(struct Keyboard *kb) {
    kb->fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
    if (kb->fd < 0) {
        perror("open /dev/uinput");
        return -1;
    }

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
    for (size_t i = 0; i < sizeof(keys)/sizeof(keys[0]); i++) {
        ioctl(kb->fd, UI_SET_KEYBIT, keys[i]);
    }

    struct uinput_setup usetup;
    memset(&usetup, 0, sizeof(usetup));
    strncpy(usetup.name, "mrext", UINPUT_MAX_NAME_SIZE - 1);
    usetup.id.bustype = BUS_USB;
    usetup.id.vendor = 0x1234;
    usetup.id.product = 0x5678;

    if (ioctl(kb->fd, UI_DEV_SETUP, &usetup) < 0 ||
        ioctl(kb->fd, UI_DEV_CREATE) < 0) {
        perror("ioctl SETUP/CREATE");
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
    }
}

void KeyEvent(struct Keyboard *kb, int type, int code, int value) {
    struct input_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.type = type;
    ev.code = code;
    ev.value = value;
    write(kb->fd, &ev, sizeof(ev));
}

void KeyPress(struct Keyboard *kb, int key) {
    KeyEvent(kb, EV_KEY, key, 1);
    KeyEvent(kb, EV_SYN, SYN_REPORT, 0);
    usleep(SLEEP_TIME);
    KeyEvent(kb, EV_KEY, key, 0);
    KeyEvent(kb, EV_SYN, SYN_REPORT, 0);
}

void KeyCombo(struct Keyboard *kb, int *keys, int count) {
    for (int i = 0; i < count; i++) KeyEvent(kb, EV_KEY, keys[i], 1);
    KeyEvent(kb, EV_SYN, SYN_REPORT, 0);
    usleep(SLEEP_TIME);
    for (int i = 0; i < count; i++) KeyEvent(kb, EV_KEY, keys[i], 0);
    KeyEvent(kb, EV_SYN, SYN_REPORT, 0);
}

// F-key functions (matching Go)
void VolumeUp(struct Keyboard *kb) { KeyPress(kb, KEY_VOLUMEUP); }
void VolumeDown(struct Keyboard *kb) { KeyPress(kb, KEY_VOLUMEDOWN); }
void VolumeMute(struct Keyboard *kb) { KeyPress(kb, KEY_MUTE); }
void Menu(struct Keyboard *kb) { KeyPress(kb, KEY_ESC); }
void Back(struct Keyboard *kb) { KeyPress(kb, KEY_BACKSPACE); }
void Confirm(struct Keyboard *kb) { KeyPress(kb, KEY_ENTER); }
void Cancel(struct Keyboard *kb) { Menu(kb); }
void Up(struct Keyboard *kb) { KeyPress(kb, KEY_UP); }
void Down(struct Keyboard *kb) { KeyPress(kb, KEY_DOWN); }
void Left(struct Keyboard *kb) { KeyPress(kb, KEY_LEFT); }
void Right(struct Keyboard *kb) { KeyPress(kb, KEY_RIGHT); }
void Osd(struct Keyboard *kb) { KeyPress(kb, KEY_F12); }
void CoreSelect(struct Keyboard *kb) {
    int keys[] = {KEY_LEFTALT, KEY_F12};
    KeyCombo(kb, keys, 2);
}
void Screenshot(struct Keyboard *kb) {
    int keys[] = {KEY_LEFTALT, KEY_SCROLLLOCK};
    KeyCombo(kb, keys, 2);
}
void RawScreenshot(struct Keyboard *kb) {
    int keys[] = {KEY_LEFTALT, KEY_LEFTSHIFT, KEY_SCROLLLOCK};
    KeyCombo(kb, keys, 3);
}
void User(struct Keyboard *kb) {
    int keys[] = {KEY_LEFTCTRL, KEY_LEFTALT, KEY_RIGHTALT};
    KeyCombo(kb, keys, 3);
}
void Reset(struct Keyboard *kb) {
    int keys[] = {KEY_LEFTSHIFT, KEY_LEFTCTRL, KEY_LEFTALT, KEY_RIGHTALT};
    KeyCombo(kb, keys, 4);
}
void PairBluetooth(struct Keyboard *kb) { KeyPress(kb, KEY_F11); }
void ChangeBackground(struct Keyboard *kb) { KeyPress(kb, KEY_F1); }
void ToggleCoreDates(struct Keyboard *kb) { KeyPress(kb, KEY_F2); }
void Console(struct Keyboard *kb) { KeyPress(kb, KEY_F9); }
void ExitConsole(struct Keyboard *kb) { KeyPress(kb, KEY_F12); }
void ComputerOsd(struct Keyboard *kb) {
    int keys[] = {KEY_LEFTMETA, KEY_F12};
    KeyCombo(kb, keys, 2);
}

// --- Helper: Draw Circle (fallback) ---
void SDL_DrawCircle(SDL_Surface *surface, int cx, int cy, int radius, Uint32 color) {
    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            if (x*x + y*y <= radius*radius) {
                int px = cx + x, py = cy + y;
                if (px >= 0 && px < surface->w && py >= 0 && py < surface->h) {
                    ((Uint32*)surface->pixels)[py * surface->pitch/4 + px] = color;
                }
            }
        }
    }
}

// --- Draw Menu ---
void draw_menu(SDL_Renderer *ren, SDL_Texture *logo, TTF_Font *font, int selected) {
    SDL_SetRenderDrawColor(ren, 0, 0, 0, 255);
    SDL_RenderClear(ren);

    // Logo
    if (logo) {
        int w, h;
        SDL_QueryTexture(logo, NULL, NULL, &w, &h);
        SDL_Rect dst = {(640 - w) / 2, 30, w, h};
        SDL_RenderCopy(ren, logo, NULL, &dst);
    }

    // Menu items
    const char *items[] = {"Update database", "Test disc", "Save disc"};
    SDL_Color white = {255, 255, 255, 255};
    SDL_Color yellow = {255, 255, 0, 255};
    int y = 180;
    for (int i = 0; i < 3; i++) {
        SDL_Surface *surf = TTF_RenderText_Solid(font, items[i], i == selected ? yellow : white);
        if (surf) {
            SDL_Texture *tex = SDL_CreateTextureFromSurface(ren, surf);
            int w, h;
            SDL_QueryTexture(tex, NULL, NULL, &w, &h);
            SDL_Rect dst = {(640 - w) / 2, y, w, h};
            SDL_RenderCopy(ren, tex, NULL, &dst);
            SDL_DestroyTexture(tex);
            SDL_FreeSurface(surf);
        }
        y += 50;
    }

    SDL_RenderPresent(ren);
}

// --- Test Disc Animation ---
void test_disc(SDL_Renderer *ren, TTF_Font *font) {
    SDL_Surface *disc_surf = IMG_Load("disc.png");
    if (!disc_surf) {
        printf("Warning: disc.png not found. Using fallback.\n");
        disc_surf = SDL_CreateRGBSurface(0, 120, 120, 32, 0, 0, 0, 0);
        SDL_FillRect(disc_surf, NULL, SDL_MapRGB(disc_surf->format, 80, 80, 80));
        SDL_DrawCircle(disc_surf, 60, 60, 50, SDL_MapRGB(disc_surf->format, 40, 40, 40));
        SDL_DrawCircle(disc_surf, 60, 60, 20, SDL_MapRGB(disc_surf->format, 20, 20, 20));
    }
    SDL_Texture *disc_tex = SDL_CreateTextureFromSurface(ren, disc_surf);
    SDL_FreeSurface(disc_surf);

    int dw, dh;
    SDL_QueryTexture(disc_tex, NULL, NULL, &dw, &dh);
    SDL_Rect disc_rect = {(640 - dw)/2, (480 - dh)/2 - 40, dw, dh};

    SDL_Color white = {255, 255, 255, 255};
    SDL_Surface *text_surf = TTF_RenderText_Solid(font, "Reading disc...", white);
    SDL_Texture *text_tex = SDL_CreateTextureFromSurface(ren, text_surf);
    int tw, th;
    SDL_QueryTexture(text_tex, NULL, NULL, &tw, &th);
    SDL_Rect text_rect = {(640 - tw)/2, disc_rect.y + dh + 10, tw, th};
    SDL_FreeSurface(text_surf);

    double angle = 0.0;
    for (int i = 0; i < 48; i++) {
        SDL_SetRenderDrawColor(ren, 0, 0, 0, 255);
        SDL_RenderClear(ren);
        SDL_RenderCopyEx(ren, disc_tex, NULL, &disc_rect, angle, NULL, SDL_FLIP_NONE);
        SDL_RenderCopy(ren, text_tex, NULL, &text_rect);
        SDL_RenderPresent(ren);
        angle += 7.5;
        SDL_Delay(60);
    }

    SDL_DestroyTexture(disc_tex);
    SDL_DestroyTexture(text_tex);
}

// --- Main ---
int main(int argc, char *argv[]) {
    // Create database
    sqlite3 *db;
    if (sqlite3_open("games.db", &db) == SQLITE_OK) {
        printf("games.db created/opened successfully.\n");
        sqlite3_close(db);
    } else {
        fprintf(stderr, "Failed to create database.\n");
    }

    // Init SDL
    if (SDL_Init(SDL_INIT_VIDEO) < 0 || IMG_Init(IMG_INIT_PNG) != IMG_INIT_PNG || TTF_Init() < 0) {
        fprintf(stderr, "SDL init failed: %s\n", SDL_GetError());
        return 1;
    }

    SDL_Window *win = SDL_CreateWindow("RetroSpin", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, 640, 480, 0);
    if (!win) goto cleanup;

    SDL_Renderer *ren = SDL_CreateRenderer(win, -1, SDL_RENDERER_ACCELERATED);
    if (!ren) goto cleanup_win;

    // Load logo
    SDL_Texture *logo = NULL;
    SDL_Surface *logo_surf = IMG_Load("retrospin.png");
    if (logo_surf) {
        logo = SDL_CreateTextureFromSurface(ren, logo_surf);
        SDL_FreeSurface(logo_surf);
    } else {
        printf("Warning: retrospin.png not found.\n");
    }

    // Load font
    TTF_Font *font = TTF_OpenFont("font.ttf", 28);
    if (!font) {
        fprintf(stderr, "Font load failed: %s\n", TTF_GetError());
        goto cleanup_ren;
    }

    // Init keyboard
    struct Keyboard kb = {.fd = -1};
    if (NewKeyboard(&kb) == 0) {
        printf("Virtual keyboard ready (uinput).\n");
        // Example: ChangeBackground(&kb); // Uncomment to test F1
    }

    // Menu loop
    int selected = 0;
    int running = 1;
    draw_menu(ren, logo, font, selected);

    while (running) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_QUIT) {
                running = 0;
            } else if (e.type == SDL_KEYDOWN) {
                switch (e.key.keysym.sym) {
                    case SDLK_UP:    selected = (selected - 1 + 3) % 3; break;
                    case SDLK_DOWN:  selected = (selected + 1) % 3; break;
                    case SDLK_RETURN:
                    case SDLK_KP_ENTER:
                        if (selected == 0) {
                            printf("Update database selected\n");
                        } else if (selected == 1) {
                            test_disc(ren, font);
                        } else if (selected == 2) {
                            printf("Save disc selected\n");
                        }
                        draw_menu(ren, logo, font, selected);
                        break;
                }
                draw_menu(ren, logo, font, selected);
            }
        }
    }

    CloseKeyboard(&kb);
    TTF_CloseFont(font);
cleanup_ren:
    if (logo) SDL_DestroyTexture(logo);
    SDL_DestroyRenderer(ren);
cleanup_win:
    SDL_DestroyWindow(win);
cleanup:
    TTF_Quit();
    IMG_Quit();
    SDL_Quit();
    return 0;
}