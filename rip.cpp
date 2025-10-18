#include "rip.h"
#include "disc.h"
#include "ui.h"
#include "db.h"
#include <fstream>
#include <iostream>
#include <dirent.h>
#include <sys/stat.h>

std::string findUSB() {
    DIR* dir = opendir("/media");
    struct dirent* entry;
    while ((entry = readdir(dir))) {
        if (strstr(entry->d_name, "usb")) {
            closedir(dir);
            return std::string("/media/") + entry->d_name;
        }
    }
    closedir(dir);
    return "/media/fat";
}

void launchGame(const std::string& path) {
    // Load core; user selects file manually
    system("echo 'load_core /media/fat/_Console/PSX/PSX.rbf' > /dev/MiSTer_cmd");
}

bool fileExists(const std::string& path) {
    struct stat buffer;
    return (stat(path.c_str(), &buffer) == 0);
}

long parseTOCLength(const std::string& tocFile) {
    std::ifstream toc(tocFile);
    std::string line;
    long totalSectors = 0;
    std::regex r("TRACK .* \\( (\\d+):(\\d+):(\\d+) \\)");
    while (std::getline(toc, line)) {
        std::smatch m;
        if (std::regex_search(line, m, r)) {
            int min = std::stoi(m[1]);
            int sec = std::stoi(m[2]);
            int frame = std::stoi(m[3]);
            totalSectors += (min * 60 + sec) * 75 + frame;
        }
    }
    return totalSectors;
}

long estimateRipTime(const std::string& tocFile) {
    long sectors = parseTOCLength(tocFile);
    int speed = 8; // Assume 8x
    return sectors / (75 * speed); // Seconds
}

void saveDisc() {
    std::string serial = getPS1Serial();
    if (serial.empty()) {
        drawText(100, 200, "No valid disc", 0xFFFF0000);
        sleep(3);
        return;
    }

    auto gameData = getGameData(serial);
    if (gameData.empty()) {
        drawText(100, 200, "No match; can't save", 0xFFFF0000);
        sleep(3);
        return;
    }

    std::string title = gameData["title"];
    int y = 200;
    for (const auto& pair : gameData) {
        drawText(100, y, pair.first + ": " + pair.second, 0xFFFFFFFF);
        y += 20;
    }
    drawText(100, y, "Save disc? (Enter=Yes, Esc=No)", 0xFFFFFFFF);

    int key = getInput();
    if (key != KEY_ENTER) return;

    system(("cdrdao read-toc --device " + DRIVE + " /tmp/disc.toc").c_str());
    long estTime = estimateRipTime("/tmp/disc.toc");
    drawText(100, y + 20, "Est time: " + std::to_string(estTime / 60) + " min", 0xFFFFFFFF);

    system("toc2cue /tmp/disc.toc /tmp/disc.cue");
    system(("cdrdao read-cd --device " + DRIVE + " --datafile /tmp/disc.bin /tmp/disc.toc").c_str());

    std::string usb = findUSB();
    std::string dir = usb + "/games/PSX/" + title;
    mkdir(dir.c_str(), 0755);
    system(("mv /tmp/disc.cue " + dir + "/" + title + ".cue").c_str());
    system(("mv /tmp/disc.bin " + dir + "/" + title + ".bin").c_str());

    drawText(100, y + 40, "Saved to " + dir, 0xFFFFFFFF);
    sleep(5);
}