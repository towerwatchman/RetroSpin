#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <ctime>
#include <dirent.h>
#include <sqlite3.h>
#include <linux/cdrom.h>
#include <mntent.h>
#include <signal.h>
#include <termios.h>
#include <sys/select.h>

using namespace std;

// Constants
const string DATA_DIR = "/media/fat/data";
const string DAT_DIR = DATA_DIR + "/dat";
const string DB_PATH = DATA_DIR + "/games.db";
const string CD_DEVICE = "/dev/sr0";
const string MNT_CDROM = "/mnt/cdrom";
const string GAMES_DIR = "/media/fat/Games";
const string PSX_DIR = GAMES_DIR + "/PSX";
const string MISTER_INI = "/media/fat/MiSTer.ini";
const string TMP_MGL = "/tmp/autolaunch.mgl";
const string CORE_PATH = "_Console/PSX";
const string RBF_NAME = "PSX.rbf";

// Systems (focus on PSX for now)
vector<string> SYSTEMS = {"psx"}; // Limited to PSX as per "testing PlayStation"
vector<string> SYSTEM_NAMES = {"Sony Playstation"};
map<string, string> REGION_MAP = {
    {"USA", "NTSC-U"}, {"Europe", "PAL"}, {"Japan", "NTSC-J"}, {"Asia", "NTSC-J"},
    {"Australia", "PAL"}, {"Brazil", "NTSC-U"}, {"Canada", "NTSC-U"}, {"China", "NTSC-J"},
    {"France", "PAL"}, {"Germany", "PAL"}, {"Italy", "PAL"}, {"Korea", "NTSC-J"},
    {"Netherlands", "PAL"}, {"Spain", "PAL"}, {"Sweden", "PAL"}, {"Taiwan", "NTSC-J"},
    {"UK", "PAL"}, {"Russia", "PAL"}, {"Scandinavia", "PAL"}, {"Greece", "PAL"},
    {"Finland", "PAL"}, {"Norway", "PAL"}, {"Ireland", "PAL"}, {"Portugal", "PAL"},
    {"Austria", "PAL"}, {"Israel", "PAL"}, {"Poland", "PAL"}, {"Denmark", "PAL"},
    {"Belgium", "PAL"}, {"India", "PAL"}, {"Latin America", "PAL"}, {"Croatia", "PAL"},
    {"World", "NTSC-U"}, {"Switzerland", "PAL"}, {"South Africa", "PAL"}
};
map<string, string> LANGUAGE_MAP = {
    {"En", "English"}, {"Ja", "Japanese"}, {"Fr", "French"}, {"De", "German"},
    {"Es", "Spanish"}, {"It", "Italian"}, {"Nl", "Dutch"}, {"Pt", "Portuguese"},
    {"Sv", "Swedish"}, {"No", "Norwegian"}, {"Da", "Danish"}, {"Fi", "Finnish"},
    {"Zh", "Chinese"}, {"Ko", "Korean"}, {"Pl", "Polish"}, {"Ru", "Russian"},
    {"El", "Greek"}, {"He", "Hebrew"}
};
map<string, string> REGION_LANGUAGE_MAP = {
    {"USA", "English"}, {"Europe", "English"}, {"Japan", "Japanese"}, {"Asia", "English"},
    {"Australia", "English"}, {"Brazil", "Portuguese"}, {"Canada", "English"}, {"China", "Chinese"},
    {"France", "French"}, {"Germany", "German"}, {"Italy", "Italian"}, {"Korea", "Korean"},
    {"Netherlands", "Dutch"}, {"Spain", "Spanish"}, {"Sweden", "Swedish"}, {"Taiwan", "Chinese"},
    {"UK", "English"}, {"Russia", "Russian"}, {"Scandinavia", "English"}, {"Greece", "Greek"},
    {"Finland", "Finnish"}, {"Norway", "Norwegian"}, {"Ireland", "English"}, {"Portugal", "Portuguese"},
    {"Austria", "German"}, {"Israel", "Hebrew"}, {"Poland", "Polish"}, {"Denmark", "Danish"},
    {"Belgium", "Dutch"}, {"India", "English"}, {"Latin America", "Spanish"}, {"Croatia", "Croatian"},
    {"World", "English"}, {"Switzerland", "German"}, {"South Africa", "English"}
};

// ANSI color codes
const string ANSI_CLEAR = "\033[2J\033[H";
const string ANSI_BLACK_BG = "\033[40m";
const string ANSI_WHITE = "\033[37m";
const string ANSI_YELLOW = "\033[33m";
const string ANSI_RESET = "\033[0m";
const string ANSI_CURSOR_OFF = "\033[?25l";
const string ANSI_CURSOR_ON = "\033[?25h";

// Function declarations
void ensure_data_dir();
pair<string, string> extract_region_and_language(const string& game_name);
string download_and_extract_dat(int i, const string& system, const string& system_name, double base_percent, double system_share);
vector<map<string, string>> parse_redump_xml(const string& file_path, const string& system, const string& system_name, double base_percent, double system_share);
void update_gauge(const string& message, int percent = -1);
void populate_database();
void create_table_schema(sqlite3* db);
string get_psx_serial_from_disc();
map<string, string> query_game(const string& serial, const string& system);
void test_disc();
void save_disc();
bool is_service_running();
void install_service();
void remove_service();
void run_as_service();
string find_usb_drive();
bool disc_inserted(int& fd);
void umount_cdrom();
bool mount_cdrom();
string normalize_serial(const string& raw_id);
string get_game_file(const string& title);
void launch_game(const string& game_path);
int get_menu_choice();
void show_message(const string& msg);
void draw_ui(const vector<string>& options, int selected, const string& status = "");
bool get_keypress(char& key, int timeout_ms = -1);

// Retrospin logo
const vector<string> LOGO = {
    "  ____      _            ",
    " |  _ \\ ___| |_ ___  ___ ",
    " | |_) / __| __/ __|/ __|",
    " |  _ < (__| || (__| (__ ",
    " |_| \\_\\___|\\__\\___|\\___|"
};

int main(int argc, char* argv[]) {
    // Set terminal to non-canonical mode for keypress detection
    termios oldt, newt;
    tcgetattr(STDIN_FILENO, &oldt);
    newt = oldt;
    newt.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(STDIN_FILENO, TCSANOW, &newt);

    if (argc > 1 && string(argv[1]) == "service") {
        run_as_service();
        tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
        return 0;
    } else if (argc > 1 && string(argv[1]) == "save") {
        save_disc();
        tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
        return 0;
    }

    // Ensure dirs
    ensure_data_dir();
    mkdir(MNT_CDROM.c_str(), 0755);

    // Main menu
    int choice = get_menu_choice();
    switch (choice) {
        case 1:
            if (is_service_running()) {
                remove_service();
            } else {
                install_service();
            }
            break;
        case 2:
            test_disc();
            break;
        case 3:
            save_disc();
            break;
        case 4:
            populate_database();
            break;
        default:
            break;
    }

    tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
    cout << ANSI_CURSOR_ON << ANSI_RESET << endl;
    return 0;
}

void ensure_data_dir() {
    mkdir(DATA_DIR.c_str(), 0755);
    mkdir(DAT_DIR.c_str(), 0755);
}

pair<string, string> extract_region_and_language(const string& game_name) {
    string region = "Unknown";
    string language = "Unknown";
    size_t paren_pos = game_name.find('(');
    if (paren_pos != string::npos) {
        size_t end_paren = game_name.find(')', paren_pos);
        string inside = game_name.substr(paren_pos + 1, end_paren - paren_pos - 1);
        vector<string> parts;
        size_t pos = 0;
        while ((pos = inside.find(',')) != string::npos) {
            string part = inside.substr(0, pos);
            part.erase(remove(part.begin(), part.end(), ' '), part.end());
            parts.push_back(part);
            inside.erase(0, pos + 1);
        }
        parts.push_back(inside);
        for (const auto& p : parts) {
            for (const auto& [key, value] : REGION_MAP) {
                if (p.find(key) != string::npos) {
                    region = value;
                    if (REGION_LANGUAGE_MAP.count(key)) {
                        language = REGION_LANGUAGE_MAP[key];
                    }
                    break;
                }
            }
            for (const auto& [key, value] : LANGUAGE_MAP) {
                if (p == key) {
                    language = value;
                    break;
                }
            }
        }
    }
    return {region, language};
}

string download_and_extract_dat(int i, const string& system, const string& system_name, double base_percent, double system_share) {
    string url = "http://redump.org/datfile/" + system + "/serial,version";
    string zip_path = DATA_DIR + "/" + system + ".zip";
    string curl_cmd = "curl -L -o " + zip_path + " \"" + url + "\" "
        "-H \"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36\" "
        "-H \"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7\" "
        "-H \"Referer: http://redump.org/downloads/\" ";
    update_gauge("Downloading " + system_name + "...");
    if (system(curl_cmd.c_str()) != 0) {
        update_gauge("Download failed for " + system_name);
        return "";
    }
    update_gauge("Downloaded " + system_name, (int)(base_percent + system_share / 2));

    string unzip_cmd = "unzip -o " + zip_path + " -d " + DAT_DIR;
    update_gauge("Extracting " + system_name + "...");
    if (system(unzip_cmd.c_str()) != 0) {
        update_gauge("Unzip failed for " + system_name);
        return "";
    }
    remove(zip_path.c_str());

    DIR* dir = opendir(DAT_DIR.c_str());
    struct dirent* ent;
    string dat_path;
    while ((ent = readdir(dir)) != NULL) {
        if (strstr(ent->d_name, ".dat")) {
            dat_path = DAT_DIR + "/" + string(ent->d_name);
            break;
        }
    }
    closedir(dir);
    update_gauge("Extracted DAT for " + system_name, (int)(base_percent + system_share * 0.6));
    return dat_path;
}

vector<map<string, string>> parse_redump_xml(const string& file_path, const string& system, const string& system_name, double base_percent, double system_share) {
    vector<map<string, string>> games;
    vector<map<string, string>> unknown_games;
    ifstream file(file_path);
    string xml((istreambuf_iterator<char>(file)), istreambuf_iterator<char>());
    file.close();

    update_gauge("Parsing XML for " + system_name + "...", (int)(base_percent + system_share * 0.6));
    size_t pos = 0;
    while ((pos = xml.find("<game name=\"", pos)) != string::npos) {
        pos += 12;
        size_t end = xml.find("\">", pos);
        string title = xml.substr(pos, end - pos);
        pos = end + 2;

        pos = xml.find("<category>", pos);
        string category = "Unknown";
        if (pos != string::npos) {
            pos += 10;
            end = xml.find("</category>", pos);
            category = xml.substr(pos, end - pos);
            pos = end;
        }

        pos = xml.find("<serial>", pos);
        string serial = "";
        if (pos != string::npos) {
            pos += 8;
            end = xml.find("</serial>", pos);
            serial = xml.substr(pos, end - pos);
            pos = end;
        }

        auto [region, language] = extract_region_and_language(title);
        if (serial.empty()) {
            map<string, string> game;
            game["title"] = title;
            game["category"] = category;
            game["serial"] = "Unknown";
            game["region"] = region;
            game["system"] = system;
            game["language"] = language;
            game["timestamp"] = to_string(time(nullptr));
            unknown_games.push_back(game);
        } else {
            vector<string> serials;
            size_t s_pos = 0;
            while ((s_pos = serial.find(',')) != string::npos) {
                serials.push_back(serial.substr(0, s_pos));
                serial.erase(0, s_pos + 1);
            }
            serials.push_back(serial);
            for (auto& s : serials) {
                map<string, string> game;
                game["title"] = title;
                game["category"] = category;
                game["serial"] = s;
                game["region"] = region;
                game["system"] = system;
                game["language"] = language;
                games.push_back(game);
            }
        }
    }
    update_gauge("Parsed " + to_string(games.size()) + " games, " + to_string(unknown_games.size()) + " unknown for " + system_name, (int)(base_percent + system_share * 0.8));
    return games; // Note: unknown_games not inserted for brevity, add if needed
}

void update_gauge(const string& message, int percent) {
    cout << ANSI_CLEAR << ANSI_BLACK_BG << ANSI_WHITE;
    for (const auto& line : LOGO) {
        cout << line << endl;
    }
    cout << "\nStatus: " << message << endl;
    if (percent >= 0) {
        int bar_width = 50;
        int filled = bar_width * percent / 100;
        cout << "[";
        for (int i = 0; i < bar_width; ++i) {
            cout << (i < filled ? "=" : " ");
        }
        cout << "] " << percent << "%" << endl;
    }
    cout << ANSI_RESET << flush;
}

void populate_database() {
    sqlite3* db;
    sqlite3_open(DB_PATH.c_str(), &db);
    create_table_schema(db);

    int num_systems = SYSTEMS.size();
    double system_share = 100.0 / num_systems;
    vector<string> failed;

    for (int i = 0; i < num_systems; ++i) {
        double base_percent = i * system_share;
        string system = SYSTEMS[i];
        string system_name = SYSTEM_NAMES[i];

        string dat_path = download_and_extract_dat(i, system, system_name, base_percent, system_share);
        if (dat_path.empty()) {
            failed.push_back(system_name);
            update_gauge("Failed to process " + system_name, (int)(base_percent + system_share));
            continue;
        }

        auto games = parse_redump_xml(dat_path, system, system_name, base_percent, system_share);
        update_gauge("Inserting data for " + system_name + "...", (int)(base_percent + system_share * 0.8));
        for (auto& game : games) {
            string sql = "INSERT OR REPLACE INTO games (serial, title, category, region, system, language) VALUES ('" +
                         game["serial"] + "', '" + game["title"] + "', '" + game["category"] + "', '" +
                         game["region"] + "', '" + game["system"] + "', '" + game["language"] + "')";
            sqlite3_exec(db, sql.c_str(), NULL, NULL, NULL);
        }
    }

    int game_count = 0;
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(db, "SELECT COUNT(*) FROM games", -1, &stmt, NULL);
    if (sqlite3_step(stmt) == SQLITE_ROW) game_count = sqlite3_column_int(stmt, 0);
    sqlite3_finalize(stmt);
    sqlite3_close(db);

    string msg = "Database update complete.\nTotal games: " + to_string(game_count);
    if (!failed.empty()) msg += "\nFailed: " + string(); // Join failed systems
    show_message(msg);
}

void create_table_schema(sqlite3* db) {
    string sql_games = "CREATE TABLE IF NOT EXISTS games (serial TEXT, title TEXT, category TEXT, region TEXT, system TEXT, language TEXT, PRIMARY KEY (serial, system))";
    string sql_unknown = "CREATE TABLE IF NOT EXISTS unknown (serial TEXT, title TEXT, category TEXT, region TEXT, system TEXT, language TEXT, timestamp TEXT, PRIMARY KEY (title, system))";
    string sql_systems = "CREATE TABLE IF NOT EXISTS systems (system TEXT, core TEXT, name TEXT, PRIMARY KEY (system))";
    sqlite3_exec(db, sql_games.c_str(), NULL, NULL, NULL);
    sqlite3_exec(db, sql_unknown.c_str(), NULL, NULL, NULL);
    sqlite3_exec(db, sql_systems.c_str(), NULL, NULL, NULL);
}

string get_psx_serial_from_disc() {
    umount_cdrom();
    if (!mount_cdrom()) {
        system("dd if=/dev/sr0 of=/tmp/disc.iso bs=2352 skip=0 count=10000 conv=sync,noerror status=progress");
        system(("mount -o loop -t iso9660 /tmp/disc.iso " + MNT_CDROM).c_str());
        if (access((MNT_CDROM + "/SYSTEM.CNF").c_str(), R_OK) != 0) {
            umount_cdrom();
            remove("/tmp/disc.iso");
            return "";
        }
    }

    ifstream cnf(MNT_CDROM + "/SYSTEM.CNF");
    string line;
    while (getline(cnf, line)) {
        if (line.find("BOOT") != string::npos) {
            size_t eq_pos = line.find('=');
            if (eq_pos != string::npos) {
                string boot = line.substr(eq_pos + 1);
                size_t col_pos = boot.find(';');
                if (col_pos != string::npos) boot = boot.substr(0, col_pos);
                size_t slash_pos = boot.rfind('\\');
                if (slash_pos == string::npos) slash_pos = boot.rfind('/');
                if (slash_pos != string::npos) boot = boot.substr(slash_pos + 1);
                cnf.close();
                umount_cdrom();
                return normalize_serial(boot);
            }
        }
    }
    cnf.close();
    umount_cdrom();
    return "";
}

string normalize_serial(const string& raw_id) {
    string id = raw_id;
    replace(id.begin(), id.end(), '_', '-');
    id.erase(remove(id.begin(), id.end(), '.'), id.end());
    transform(id.begin(), id.end(), id.begin(), ::toupper);
    return id;
}

map<string, string> query_game(const string& serial, const string& system) {
    map<string, string> game;
    sqlite3* db;
    sqlite3_open(DB_PATH.c_str(), &db);
    string sql = "SELECT serial, title, category, region, system, language FROM games WHERE serial = '" + serial + "' AND system = '" + system + "'";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt, NULL);
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        game["serial"] = (const char*)sqlite3_column_text(stmt, 0);
        game["title"] = (const char*)sqlite3_column_text(stmt, 1);
        game["category"] = (const char*)sqlite3_column_text(stmt, 2);
        game["region"] = (const char*)sqlite3_column_text(stmt, 3);
        game["system"] = (const char*)sqlite3_column_text(stmt, 4);
        game["language"] = (const char*)sqlite3_column_text(stmt, 5);
    }
    sqlite3_finalize(stmt);
    sqlite3_close(db);
    return game;
}

void test_disc() {
    int fd = open(CD_DEVICE.c_str(), O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        show_message("No disc drive available.");
        return;
    }
    close(fd);

    show_message("Trying to read disc...");
    time_t start = time(nullptr);
    while (time(nullptr) - start < 10) {
        int disc_fd;
        if (disc_inserted(disc_fd)) {
            string serial = get_psx_serial_from_disc();
            if (!serial.empty()) {
                auto game = query_game(serial, "PSX");
                if (!game.empty()) {
                    string output = "Serial: " + game["serial"] + "\nTitle: " + game["title"] + "\nCategory: " + game["category"] +
                                    "\nRegion: " + game["region"] + "\nSystem: " + game["system"] + "\nLanguage: " + game["language"];
                    show_message(output);
                    return;
                } else {
                    show_message("No match found in database.");
                    return;
                }
            }
            close(disc_fd);
        }
        sleep(1);
    }
    show_message("No disc detected after 10 seconds.");
}

void save_disc() {
    string serial = get_psx_serial_from_disc();
    if (serial.empty()) {
        show_message("Failed to read disc ID.");
        return;
    }
    auto game = query_game(serial, "PSX");
    if (game.empty()) {
        show_message("No match in database.");
        return;
    }
    string output = "Found game:\n" + game["title"] + "\n\nSave disc? (y/n)";
    draw_ui({"Yes", "No"}, 0, output);
    char key;
    while (get_keypress(key)) {
        if (tolower(key) == 'y') break;
        if (tolower(key) == 'n') return;
    }
    if (tolower(key) != 'y') return;

    string usb = find_usb_drive();
    if (usb.empty()) {
        show_message("No USB drive found.");
        return;
    }
    string save_dir = usb + "/Games/PSX";
    mkdir(save_dir.c_str(), 0755);
    string bin_path = save_dir + "/" + game["title"] + ".bin";
    string toc_path = "/tmp/disc.toc";
    string cue_path = save_dir + "/" + game["title"] + ".cue";

    update_gauge("Reading TOC...");
    string cdrdao_toc = "cdrdao read-toc --device " + CD_DEVICE + " " + toc_path;
    if (system(cdrdao_toc.c_str()) != 0) {
        show_message("Failed to read TOC.");
        return;
    }

    // Estimate time (simplified, assume 700MB disc, ~20 min at 2x speed)
    update_gauge("Ripping disc, estimated time: ~20 min");
    string cdrdao_rip = "cdrdao read-cd --read-raw --datafile " + bin_path + " --device " + CD_DEVICE + " --driver generic-mmc-raw " + toc_path;
    if (system(cdrdao_rip.c_str()) != 0) {
        show_message("Rip failed.");
        return;
    }

    update_gauge("Converting TOC to CUE...");
    string toc2cue_cmd = "toc2cue " + toc_path + " " + cue_path;
    if (system(toc2cue_cmd.c_str()) != 0) {
        show_message("Failed to create cue.");
        return;
    }

    remove(toc_path.c_str());
    show_message("Disc saved to " + cue_path);
}

bool is_service_running() {
    FILE* pipe = popen("ps | grep Retrospin | grep service", "r");
    char buf[1024];
    bool running = fgets(buf, 1024, pipe) != NULL;
    pclose(pipe);
    return running;
}

void install_service() {
    ofstream startup("/media/fat/linux/user-startup.sh", ios::app);
    startup << "/media/fat/linux/Retrospin service &\n";
    startup.close();
    show_message("Installed as service.");
}

void remove_service() {
    ifstream in("/media/fat/linux/user-startup.sh");
    ofstream out("/tmp/user-startup.tmp");
    string line;
    while (getline(in, line)) {
        if (line.find("Retrospin service") == string::npos) out << line << endl;
    }
    in.close();
    out.close();
    rename("/tmp/user-startup.tmp", "/media/fat/linux/user-startup.sh");
    system("killall Retrospin");
    show_message("Removed service.");
}

void run_as_service() {
    if (fork() != 0) exit(0);
    setsid();

    string last_serial;
    while (true) {
        int fd;
        if (disc_inserted(fd)) {
            string serial = get_psx_serial_from_disc();
            if (!serial.empty() && serial != last_serial) {
                last_serial = serial;
                auto game = query_game(serial, "PSX");
                if (!game.empty()) {
                    string game_path = get_game_file(game["title"]);
                    if (!game_path.empty()) {
                        launch_game(game_path);
                    } else {
                        system("/media/fat/linux/Retrospin save");
                    }
                }
            }
            close(fd);
        }
        sleep(5);
    }
}

string find_usb_drive() {
    FILE* mtab = setmntent("/etc/mtab", "r");
    struct mntent* ent;
    while ((ent = getmntent(mtab))) {
        if (strstr(ent->mnt_dir, "/media/usb")) return ent->mnt_dir;
    }
    endmntent(mtab);
    return "";
}

bool disc_inserted(int& fd) {
    fd = open(CD_DEVICE.c_str(), O_RDONLY | O_NONBLOCK);
    if (fd < 0) return false;
    int status = ioctl(fd, CDROM_DISC_STATUS);
    if (status == CDS_DISC_OK) return true;
    close(fd);
    return false;
}

void umount_cdrom() {
    system(("umount " + MNT_CDROM).c_str());
}

bool mount_cdrom() {
    return system(("mount -t iso9660 " + CD_DEVICE + " " + MNT_CDROM).c_str()) == 0;
}

string get_game_file(const string& title) {
    string cue = PSX_DIR + "/" + title + ".cue";
    if (access(cue.c_str(), R_OK) == 0) return cue;
    string chd = PSX_DIR + "/" + title + ".chd";
    if (access(chd.c_str(), R_OK) == 0) return chd;
    return "";
}

void launch_game(const string& game_path) {
    ofstream mgl(TMP_MGL);
    mgl << "<mgl><rbf>" << CORE_PATH << "</rbf><file delay=\"2\" type=\"f\" index=\"0\" path=\"" << game_path << "\"/></mgl>";
    mgl.close();

    ifstream ini_in(MISTER_INI);
    ofstream ini_out("/tmp/MiSTer.tmp");
    string line;
    bool set = false;
    while (getline(ini_in, line)) {
        if (line.find("bootcore") != string::npos) {
            ini_out << "bootcore=" << TMP_MGL << endl;
            set = true;
        } else {
            ini_out << line << endl;
        }
    }
    if (!set) ini_out << "bootcore=" << TMP_MGL << endl;
    ini_in.close();
    ini_out.close();
    rename("/tmp/MiSTer.tmp", MISTER_INI.c_str());

    system("killall MiSTer");
}

int get_menu_choice() {
    vector<string> options = {
        is_service_running() ? "Remove service" : "Install as service",
        "Test Disc",
        "Save Disc",
        "Update database"
    };
    int selected = 0;
    char key;

    while (true) {
        draw_ui(options, selected);
        if (get_keypress(key)) {
            if (key == 27) { // ESC
                return 0;
            } else if (key == '\n') {
                return selected + 1;
            } else if (key == 'A' || key == 'w') { // Up
                selected = (selected == 0) ? options.size() - 1 : selected - 1;
            } else if (key == 'B' || key == 's') { // Down
                selected = (selected == options.size() - 1) ? 0 : selected + 1;
            }
        }
    }
}

void show_message(const string& msg) {
    draw_ui({}, -1, msg);
    char key;
    while (!get_keypress(key)) {}
}

void draw_ui(const vector<string>& options, int selected, const string& status) {
    cout << ANSI_CLEAR << ANSI_BLACK_BG << ANSI_WHITE;
    for (size_t i = 0; i < LOGO.size(); ++i) {
        cout << "\033[" << (i + 1) << ";1H" << LOGO[i];
    }
    int menu_start_y = LOGO.size() + 2;
    if (!options.empty()) {
        cout << "\033[" << menu_start_y << ";1HMain Menu:";
        for (size_t i = 0; i < options.size(); ++i) {
            cout << "\033[" << (menu_start_y + i + 1) << ";3H";
            if ((int)i == selected) {
                cout << ANSI_YELLOW << "> " << options[i] << ANSI_WHITE;
            } else {
                cout << "  " << options[i];
            }
        }
    }
    if (!status.empty()) {
        cout << "\033[" << (menu_start_y + options.size() + 2) << ";1H" << status;
    }
    cout << ANSI_RESET << flush;
}

bool get_keypress(char& key, int timeout_ms) {
    fd_set set;
    struct timeval timeout;
    FD_ZERO(&set);
    FD_SET(STDIN_FILENO, &set);
    if (timeout_ms >= 0) {
        timeout.tv_sec = timeout_ms / 1000;
        timeout.tv_usec = (timeout_ms % 1000) * 1000;
    }
    int rv = select(STDIN_FILENO + 1, &set, NULL, NULL, timeout_ms >= 0 ? &timeout : NULL);
    if (rv <= 0) return false;
    char buf[3];
    int n = read(STDIN_FILENO, buf, 3);
    if (n == 1) {
        key = buf[0];
        return true;
    } else if (n == 3 && buf[0] == 27 && buf[1] == '[') {
        key = buf[2]; // Arrow keys (A=up, B=down)
        return true;
    }
    return false;
}