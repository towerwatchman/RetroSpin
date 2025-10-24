// retrospin.c
// RetroSpin - MiSTer FPGA Disc Manager GUI
// Compile instructions at the end of this file.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <fcntl.h>
#include <time.h>
#include <errno.h>
#include <regex.h>  // For basic regex; assume installed or manual string matching
#include <dirent.h>

#include "sqlite3.h"  // Include from amalgamation
#include "input.h"    // Our input header

#define DATA_DIR "data"
#define DAT_DIR "data/dat"
#define DB_PATH "data/games.db"
#define TEMP_DIR "/tmp/retrospin_temp"
#define ZIP_PATH "/tmp/redump_zip.zip"
#define GAUGE_MSG_FILE "/tmp/gauge_msg"
#define CHOICE_FILE "/tmp/retrospin_choice"

// Systems and mappings (ported from Python)
const char *SYSTEMS[] = {"psx", "ajcd", "acd", "cd32", "cdtv", "pce", "ngcd", "3do", "cdi", "mcd", "ss"};
const char *SYSTEM_NAMES[] = {"Sony Playstation", "Atari Jaguar CD", "Amiga CD", "Amiga CD32", "Amiga CDTV", "NEC PC Engine", "Neo Geo CD", "Panasonic 3DO", "Philips CDI", "Sega CD", "Sega Saturn"};
int NUM_SYSTEMS = 11;

// Region map (simplified; full map in code)
struct RegionMap {
    const char *from;
    const char *to;
};
struct RegionMap REGION_MAP[] = {
    {"USA", "NTSC-U"}, {"Europe", "PAL"}, {"Japan", "NTSC-J"}, {"Asia", "NTSC-J"},
    {"Australia", "PAL"}, {"Brazil", "NTSC-U"}, {"Canada", "NTSC-U"}, {"China", "NTSC-J"},
    {"France", "PAL"}, {"Germany", "PAL"}, {"Italy", "PAL"}, {"Korea", "NTSC-J"},
    {"Netherlands", "PAL"}, {"Spain", "PAL"}, {"Sweden", "PAL"}, {"Taiwan", "NTSC-J"},
    {"UK", "PAL"}, {"Russia", "PAL"}, {"Scandinavia", "PAL"}, {"Greece", "PAL"},
    {"Finland", "PAL"}, {"Norway", "PAL"}, {"Ireland", "PAL"}, {"Portugal", "PAL"},
    {"Austria", "PAL"}, {"Israel", "PAL"}, {"Poland", "PAL"}, {"Denmark", "PAL"},
    {"Belgium", "PAL"}, {"India", "PAL"}, {"Latin America", "PAL"}, {"Croatia", "PAL"},
    {"World", "NTSC-U"}, {"Switzerland", "PAL"}, {"South Africa", "PAL"},
    {NULL, NULL}
};

// Language maps similar (omitted for brevity; implement as arrays)

void ensure_data_dir() {
    mkdir(DATA_DIR, 0755);
    mkdir(DAT_DIR, 0755);
}

void run_dialog_menu(const char *title, const char *prompt, const char **items, int num_items, int height, int width) {
    char cmd[1024] = "dialog --clear --backtitle \"";
    strcat(cmd, title);
    strcat(cmd, "\" --title \"");
    strcat(cmd, prompt);
    strcat(cmd, "\" --menu \"Choose an option:\" ");
    char hws[32];
    sprintf(hws, "%d %d %d", height, width, num_items);
    strcat(cmd, hws);
    for (int i = 0; i < num_items; i++) {
        char item[256];
        sprintf(item, " %s %d %s", items[i*2], i+1, items[i*2+1]);
        strcat(cmd, item);
    }
    strcat(cmd, " 2> ");
    strcat(cmd, CHOICE_FILE);
    system(cmd);
}

int get_choice() {
    FILE *f = fopen(CHOICE_FILE, "r");
    if (!f) return -1;
    int choice;
    fscanf(f, "%d", &choice);
    fclose(f);
    unlink(CHOICE_FILE);
    return choice;
}

void run_dialog_msgbox(const char *title, const char *msg, int height, int width) {
    char cmd[1024] = "dialog --backtitle \"RetroSpin\" --title \"";
    strcat(cmd, title);
    strcat(cmd, "\" --msgbox \"";
    strcat(cmd, msg);
    strcat(cmd, "\" ");
    char hws[32];
    sprintf(hws, "%d %d", height, width);
    strcat(cmd, hws);
    system(cmd);
}

void run_dialog_gauge_start(const char *title) {
    char cmd[512] = "dialog --backtitle \"RetroSpin\" --title \"";
    strcat(cmd, title);
    strcat(cmd, "\" --gauge \"Starting...\" 10 50 0";
    system(cmd);
    // To update, we need to kill and restart or use pipes; for simplicity, use multiple msgbox or separate gauges
    // Advanced: fork and write to stdin
}

void update_gauge(int percent, const char *msg) {
    // Simple implementation: use echo to update, but dialog gauge doesn't support dynamic easily without pipe
    // For now, stub with msgbox; improve with pipe
    char fullmsg[256];
    sprintf(fullmsg, "%d%%: %s", percent, msg);
    run_dialog_msgbox("Progress", fullmsg, 8, 50);
}

// Stub for pipe-based gauge (like Python)
pid_t start_gauge_process(const char *title) {
    pid_t pid = fork();
    if (pid == 0) {
        execlp("dialog", "dialog", "--backtitle", "RetroSpin", "--title", title, "--gauge", "0", "10", "50", NULL);
    }
    return pid;
}

void update_gauge_pipe(pid_t pid, int percent, const char *msg) {
    // Send to stdin of pid
    char input[256];
    sprintf(input, "XXX\n%d\n%s\nXXX\n", percent, msg);
    int fd = pid + 3; // Approximate; better use pipe
    // Full impl needs pipe setup; stub for now
    run_dialog_msgbox("Update", msg, 8, 50);  // Fallback
}

void end_gauge(pid_t pid) {
    kill(pid, SIGTERM);
    waitpid(pid, NULL, 0);
}

// Ported extract_region_and_language (simplified, manual string match instead of full re)
void extract_region_and_language(const char *game_name, char *region, char *language) {
    strcpy(region, "Unknown");
    strcpy(language, "Unknown");

    // Find (regions)
    char *paren = strstr(game_name, "(");
    if (paren) {
        char *close = strchr(paren, ')');
        if (close) {
            char regbuf[256];
            strncpy(regbuf, paren + 1, close - paren - 1);
            regbuf[close - paren - 1] = '\0';
            // Split by comma, check map
            char *part = strtok(regbuf, ",");
            while (part) {
                char p[64];
                strcpy(p, part);
                // Trim
                char *end = p + strlen(p) - 1;
                while (end > p && (*end == ' ' || *end == '\t')) end--;
                end[1] = '\0';
                for (int m = 0; REGION_MAP[m].from; m++) {
                    if (strcasestr(p, REGION_MAP[m].from)) {  // Need strcasestr impl or tolower
                        strcpy(region, REGION_MAP[m].to);
                        break;
                    }
                }
                part = strtok(NULL, ",");
            }
        }
    }

    // Language (En, etc.) similar manual match
    if (strstr(game_name, "(En)")) strcpy(language, "English");
    // Add more...

    // Fallback region lang
    if (strcmp(region, "Unknown") == 0 && strcmp(language, "Unknown") == 0) {
        if (strstr(game_name, "USA")) strcpy(language, "English");
        // etc.
    }
}

// Simple XML parser for Redump DAT
int parse_redump_xml(const char *file_path, const char *system, int *games_count, int *unknown_count) {
    FILE *fp = fopen(file_path, "r");
    if (!fp) return -1;

    char line[1024];
    char title[512] = "";
    char category[128] = "Unknown";
    char serial[128] = "";
    char region[64], language[64];
    int gc = 0, uc = 0;

    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "<game name=")) {
            // Extract name
            char *quote = strchr(line, '"');
            if (quote) {
                quote++;
                char *endquote = strchr(quote, '"');
                if (endquote) {
                    strncpy(title, quote, endquote - quote);
                    title[endquote - quote] = '\0';
                }
            }
            // Assume category and serial in next lines
            fgets(line, sizeof(line), fp);  // category
            if (strstr(line, "<category>")) {
                // extract
                strcpy(category, "Game");  // Stub
            }
            serial[0] = '\0';
            fgets(line, sizeof(line), fp);  // serial
            if (strstr(line, "<serial>")) {
                // extract serial
                char *start = strstr(line, ">") + 1;
                char *end = strstr(line, "</serial>");
                if (end) strncpy(serial, start, end - start - 1);
            }
            extract_region_and_language(title, region, language);

            if (strlen(serial) == 0) {
                uc++;
                // Insert unknown to DB stub
            } else {
                // Split serials by ,, insert each
                char *s = strtok(serial, ",");
                while (s) {
                    // sqlite insert
                    gc++;
                    s = strtok(NULL, ",");
                }
            }
        }
    }
    fclose(fp);
    *games_count = gc;
    *unknown_count = uc;
    return 0;
}

// Download and extract (using system calls)
int download_and_extract_dat(const char *system, const char *system_name, int base_percent, double system_share, pid_t gauge_pid) {
    char url[256];
    sprintf(url, "http://redump.org/datfile/%s/serial,version", system);
    char wget_cmd[512];
    sprintf(wget_cmd, "wget -O %s %s", ZIP_PATH, url);
    if (system(wget_cmd) != 0) {
        update_gauge_pipe(gauge_pid, base_percent + (system_share / 2), "Download failed");
        return -1;
    }
    update_gauge_pipe(gauge_pid, base_percent + (system_share / 2), "Downloaded");

    // Extract
    mkdir(TEMP_DIR, 0755);
    char unzip_cmd[512];
    sprintf(unzip_cmd, "unzip -o %s -d %s", ZIP_PATH, TEMP_DIR);
    if (system(unzip_cmd) != 0) {
        update_gauge_pipe(gauge_pid, base_percent + (system_share * 0.6), "Extract failed");
        return -1;
    }

    // Find .dat
    DIR *dir = opendir(TEMP_DIR);
    struct dirent *entry;
    char dat_path[256] = "";
    while ((entry = readdir(dir)) != NULL) {
        if (strstr(entry->d_name, ".dat")) {
            sprintf(dat_path, "%s/%s", TEMP_DIR, entry->d_name);
            break;
        }
    }
    closedir(dir);

    if (strlen(dat_path) == 0) return -1;

    // Copy to DAT_DIR
    char cp_cmd[512];
    sprintf(cp_cmd, "cp %s %s", dat_path, DAT_DIR);
    system(cp_cmd);

    // Cleanup
    sprintf(unzip_cmd, "rm -rf %s", TEMP_DIR);
    system(unzip_cmd);
    unlink(ZIP_PATH);

    update_gauge_pipe(gauge_pid, base_percent + (system_share * 0.6), "Extracted");
    return 0;
}

void create_table_schema(sqlite3 *db) {
    const char *create_games = "CREATE TABLE IF NOT EXISTS games ("
        "serial TEXT PRIMARY KEY, title TEXT, category TEXT, region TEXT, system TEXT, language TEXT);";
    const char *create_unknown = "CREATE TABLE IF NOT EXISTS unknown ("
        "serial TEXT PRIMARY KEY, title TEXT, category TEXT, region TEXT, system TEXT, language TEXT, timestamp TEXT);";
    char *err;
    sqlite3_exec(db, create_games, NULL, NULL, &err);
    sqlite3_exec(db, create_unknown, NULL, NULL, &err);
}

void update_database() {
    ensure_data_dir();
    sqlite3 *db;
    if (sqlite3_open(DB_PATH, &db) != SQLITE_OK) {
        run_dialog_msgbox("Error", "Failed to open DB", 8, 50);
        return;
    }
    create_table_schema(db);

    double system_share = 100.0 / NUM_SYSTEMS;
    pid_t gauge_pid = start_gauge_process("Updating Database");

    int total_games = 0, total_unknown = 0;
    int failed = 0;

    for (int i = 0; i < NUM_SYSTEMS; i++) {
        int base_p = i * system_share;
        const char *sys = SYSTEMS[i];
        const char *sysname = SYSTEM_NAMES[i];

        update_gauge_pipe(gauge_pid, base_p, "Fetching DAT for system");

        if (download_and_extract_dat(sys, sysname, base_p, system_share, gauge_pid) != 0) {
            failed++;
            continue;
        }

        char dat_path[256];
        sprintf(dat_path, "%s/%s.dat", DAT_DIR, sys);  // Assume filename
        int gc = 0, uc = 0;
        parse_redump_xml(dat_path, sys, &gc, &uc);

        // Insert stub; in full, loop over parsed games and sqlite3_exec INSERT OR REPLACE

        total_games += gc;
        total_unknown += uc;

        update_gauge_pipe(gauge_pid, base_p + system_share, "Done");
    }

    end_gauge(gauge_pid);

    char msg[256];
    sprintf(msg, "Update complete.\nGames: %d\nUnknown: %d", total_games, total_unknown);
    if (failed > 0) {
        sprintf(msg + strlen(msg), "\nFailed: %d systems", failed);
    }
    run_dialog_msgbox("Complete", msg, 10, 50);

    sqlite3_close(db);
}

void test_disc() {
    system("mkdir -p /mnt/cdrom");
    system("mount /dev/sr0 /mnt/cdrom 2>/dev/null || umount /mnt/cdrom 2>/dev/null");
    if (system("mount /dev/sr0 /mnt/cdrom") != 0) {
        run_dialog_msgbox("Error", "Failed to mount disc", 8, 50);
        return;
    }

    system("cdrdao read-toc --device /dev/sr0 > /tmp/disc.toc 2>/dev/null");

    char cmd[256] = "dialog --backtitle \"RetroSpin\" --title \"Disc Info\" --textbox /tmp/disc.toc 20 80";
    system(cmd);

    unlink("/tmp/disc.toc");
    system("umount /mnt/cdrom 2>/dev/null");
}

void load_disc() {
    // Stub: Use toc2cue to generate CUE/BIN for MiSTer loading
    // Assume disc mounted; eject or prepare
    run_dialog_msgbox("Load Disc", "TODO: Implement load (e.g., toc2cue and copy to MiSTer folder)", 10, 50);
    // Example: system("toc2cue /tmp/disc.toc /tmp/disc.cue");
    // Then copy to /media/fat/Menu or similar
}

void show_input_menu(Keyboard *kb) {
    const char *items[8] = {"Volume Up", "1", "Volume Down", "2", "Menu", "3", "Close", "4"};
    run_dialog_menu("Input Commands", "Select command:", items, 4, 12, 40);
    int ch = get_choice();
    if (ch == 1) kb_volume_up(kb);
    else if (ch == 2) kb_volume_down(kb);
    else if (ch == 3) kb_menu(kb);
    // Add more
}

int main() {
    Keyboard kb;
    if (init_keyboard(&kb) < 0) {
        // Non-fatal
    }

    while (1) {
        const char *menu_items[8] = {
            "Update Database", "1",
            "Test Disc", "2",
            "Load Disc", "3",
            "Send Command", "4",  // For input
            "Close", "5"
        };
        run_dialog_menu("RetroSpin", "Main Menu", menu_items, 5, 15, 50);
        int choice = get_choice();
        if (choice == 1) update_database();
        else if (choice == 2) test_disc();
        else if (choice == 3) load_disc();
        else if (choice == 4) show_input_menu(&kb);
        else if (choice == 5 || choice < 0) break;
    }

    close_keyboard(&kb);
    return 0;
}