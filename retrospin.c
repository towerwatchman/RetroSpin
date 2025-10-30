#include <stdio.h>
#include <unistd.h>

#include "input.c"
#include "ui.c"

int main(void)
{
    printf("retrospin: init\n");
    Keyboard kb;
    if (keyboard_init(&kb) < 0) return 1;

    printf("retrospin: UI init\n");
    if (ui_init() < 0) {
        keyboard_close(&kb);
        return 1;
    }

    printf("retrospin: sending F9\n");
    keyboard_console(&kb);
    usleep(100000);

    int sel = ui_wait_for_selection();
    ui_close();

    printf("retrospin: sending F12\n");
    keyboard_exit_console(&kb);
    keyboard_close(&kb);

    switch (sel) {
        case 0: system("update_db.sh"); break;
        case 1: system("cdrdao read-toc disc.toc"); break;
        case 2: system("load_disc.sh"); break;
    }

    return 0;
}