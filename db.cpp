#include "db.h"
#include <sqlite3.h>
#include <iostream>

const std::string DB_PATH = "/media/fat/retrospin.db";

static int callback(void* data, int argc, char** argv, char** azColName) {
    auto* map = static_cast<std::map<std::string, std::string>*>(data);
    for (int i = 0; i < argc; i++) {
        (*map)[azColName[i]] = argv[i] ? argv[i] : "";
    }
    return 0;
}

std::map<std::string, std::string> getGameData(const std::string& serial) {
    sqlite3* db;
    if (sqlite3_open(DB_PATH.c_str(), &db) != SQLITE_OK) {
        std::cerr << "Can't open DB" << std::endl;
        return {};
    }

    std::map<std::string, std::string> data;
    std::string sql = "SELECT * FROM games WHERE serial = '" + serial + "';";
    char* errMsg;
    sqlite3_exec(db, sql.c_str(), callback, &data, &errMsg);

    sqlite3_close(db);
    return data;
}

std::string getGameTitle(const std::string& serial) {
    auto data = getGameData(serial);
    return data["title"];
}