#include <iostream>
#include <string>
#include <vector>
#include <unistd.h>
#include "ui.h"
#include "disc.h"
#include "db.h"
#include "rip.h"
#include "service.h"
#include "update_db.h"

int main(int argc, char* argv[]) {
    if (argc > 1 && std::string(argv[1]) == "--service") {
        runAsService();
        return 0;
    }

    // UI mode
    initFramebuffer();
    drawBackground();
    drawLogo();

    std::vector<std::string> menuItems = {"Install/Remove as a service", "Test Disc", "Save Disc", "Update database"};
    if (isServiceRunning()) {
        menuItems[0] = "Remove service (running)";
    } else {
        menuItems[0] = "Install as service";
    }

    int selected = 0;
    while (true) {
        drawMenu(menuItems, selected);
        int key = getInput();
        if (key == KEY_UP) selected = (selected > 0) ? selected - 1 : menuItems.size() - 1;
        if (key == KEY_DOWN) selected = (selected < menuItems.size() - 1) ? selected + 1 : 0;
        if (key == KEY_ENTER) {
            if (selected == 0) {
                if (isServiceRunning()) removeService(); else installService();
                // Update menu text
                if (isServiceRunning()) menuItems[0] = "Remove service (running)";
                else menuItems[0] = "Install as service";
            } else if (selected == 1) testDisc();
            else if (selected == 2) saveDisc();
            else if (selected == 3) updateDatabase();
        }
        if (key == KEY_ESC) break;
    }

    cleanupFramebuffer();
    return 0;
}