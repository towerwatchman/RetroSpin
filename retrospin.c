/* retrospin.c – Entry point with debug output */
#include <stdio.h>
#include <unistd.h>
#include <sys/time.h>

#include "input.c"
#include "ui.c"

int main(void)
{
    printf("retrospin: Starting...\n");
    fflush(stdout);

    Keyboard kb;

    printf("retrospin: Creating virtual keyboard...\n");
    if (keyboard_init(&kb) < 0) {
        fprintf(stderr, "retrospin: FAILED to create keyboard\n");
        return 1;
    }
    printf("retrospin: Virtual keyboard 'mrext' created\n");

    printf("retrospin: Sending F9 (open console)...\n");
    keyboard_console(&kb);
    usleep(500000);  /* 500ms for console to open */

    printf("retrospin: Initializing UI...\n");
    if (ui_init() < 0) {
        fprintf(stderr, "retrospin: UI init failed (no input device?)\n");
        keyboard_exit_console(&kb);
        keyboard_close(&kb);
        return 1;
    }
    printf("retrospin: UI initialized\n");

    printf("retrospin: Showing menu...\n");
    ui_show_menu(0);

    printf("retrospin: Waiting for user input...\n");
    int sel = ui_wait_for_selection();

    if (sel == -1) {
        printf("retrospin: User cancelled (ESC/B)\n");
    } else {
        printf("retrospin: Selected option %d: %s\n", sel, menu_items[sel]);
    }

    ui_close();
    printf("retrospin: Sending F12 (close console)...\n");
    keyboard_exit_console(&kb);
    keyboard_close(&kb);

    /* Handle selection */
    switch (sel) {
        case 0: printf("retrospin: Running update_db.sh\n"); system("update_db.sh"); break;
        case 1: printf("retrospin: Running cdrdao read-toc\n"); system("cdrdao read-toc disc.toc"); break;
        case 2: printf("retrospin: Running load_disc.sh\n"); system("load_disc.sh"); break;
        case 3: printf("retrospin: Close selected\n"); break;
    }

    printf("retrospin: Done.\n");
    return 0;
}