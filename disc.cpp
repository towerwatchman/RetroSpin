#include "disc.h"
#include "ui.h"
#include "db.h"
#include <sys/mount.h>
#include <unistd.h>
#include <fstream>
#include <iostream>
#include <regex>

const std::string MOUNT_POINT = "/mnt/cdrom";
const std::string DRIVE = "/dev/sr0";

bool isDriveAvailable() {
    return access(DRIVE.c_str(), F_OK) == 0;
}

bool isDiscInserted() {
    if (mount(DRIVE.c_str(), MOUNT_POINT.c_str(), "iso9660", MS_RDONLY, NULL) == 0) {
        umount(MOUNT_POINT.c_str());
        return true;
    }
    return false;
}

std::string getPS1Serial() {
    if (mount(DRIVE.c_str(), MOUNT_POINT.c_str(), "iso9660", MS_RDONLY, NULL) != 0) {
        return "";
    }

    std::ifstream cnf(MOUNT_POINT + "/SYSTEM.CNF");
    std::string line;
    std::string serial = "";
    while (std::getline(cnf, line)) {
        if (line.find("BOOT") != std::string::npos) {
            std::regex r("cdrom:\\\\(.*?)_(.*?)\\.(.*?);1");
            std::smatch m;
            if (std::regex_search(line, m, r)) {
                serial = m[1].str() + "-" + m[2].str() + m[3].str(); // e.g., SLUS-00707
            }
            break;
        }
    }
    umount(MOUNT_POINT.c_str());
    return serial;
}

void testDisc() {
    if (!isDriveAvailable()) {
        drawText(100, 200, "No drive available", 0xFFFF0000);
        sleep(3);
        return;
    }

    drawText(100, 200, "Trying to read disc...", 0xFFFFFFFF);
    for (int i = 0; i < 10; i++) {
        if (isDiscInserted()) break;
        sleep(1);
    }

    std::string serial = getPS1Serial();
    if (serial.empty()) {
        drawText(100, 220, "No disc or invalid", 0xFFFF0000);
        sleep(3);
        return;
    }

    auto gameData = getGameData(serial);
    if (gameData.empty()) {
        drawText(100, 220, "No match in DB", 0xFFFF0000);
    } else {
        int y = 220;
        for (const auto& pair : gameData) {
            drawText(100, y, pair.first + ": " + pair.second, 0xFFFFFFFF);
            y += 20;
        }
    }
    sleep(5);
}