#include "service.h"
#include "disc.h"
#include "db.h"
#include "rip.h"
#include <iostream>
#include <unistd.h>

bool isServiceRunning() {
    return system("ps aux | grep '[r]etrospin --service' > /dev/null") == 0;
}

void installService() {
    system("cp /mnt/retrospin /usr/local/bin/retrospin");
    std::ofstream init("/etc/init.d/retrospin");
    init << "#!/bin/sh\n/usr/local/bin/retrospin --service &\n";
    init.close();
    system("chmod +x /etc/init.d/retrospin");
    system("update-rc.d retrospin defaults");
}

void removeService() {
    system("update-rc.d retrospin remove");
    system("rm /etc/init.d/retrospin");
    system("killall retrospin");
}

void runAsService() {
    while (true) {
        if (isDiscInserted()) {
            std::string serial = getPS1Serial();
            if (!serial.empty()) {
                std::string title = getGameTitle(serial);
                std::string cuePath = "/media/fat/games/PSX/" + title + ".cue"; // Check default first
                if (fileExists(cuePath)) {
                    launchGame(cuePath);
                } else {
                    std::string chdPath = "/media/fat/games/PSX/" + title + ".chd";
                    if (fileExists(chdPath)) {
                        launchGame(chdPath);
                    } else {
                        // Rip and show UI over
                        initFramebuffer();
                        drawBackground();
                        drawLogo();
                        saveDisc();
                        cleanupFramebuffer();
                    }
                }
            }
        }
        sleep(5); // Poll every 5s
    }
}